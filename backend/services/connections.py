"""What the user has connected, and what each source is currently asking.

Sources is a menu, not a report. Every supported source is returned on every
call, in a fixed order, and only its status and counts change. The alternative,
building the list from whatever appears in the feed, cannot distinguish a source
with nothing to say from one that was never connected, and cannot show the user
what they are missing.

Everything here is scoped to the app user's id, which is also the Composio
``user_id``: `link_url` starts an OAuth for *this* user, `status` confirms it
became active for *this* user and records the account, and `disconnect` removes
it. There is no shared account any more; the id is the boundary, and it comes
from the verified token, never from the client.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from backend.models.connections import ConnectionRow
from backend.models.feed import FeedItem
from backend.models.identity import Identity
from backend.models.sources import (
    CATALOGUE,
    LABELS,
    SOURCE_TO_TOOLKIT,
    TOOLKIT_TO_SOURCE,
    ConnectionStatus,
    Source,
    SourceInfo,
)
from backend.models.tiers import Tier

log = logging.getLogger(__name__)

#: Composio reports a row per authorisation attempt. Only these mean "usable".
_LIVE = {"ACTIVE"}
_BROKEN = {"EXPIRED", "REVOKED", "FAILED", "INACTIVE"}

_GITHUB_VERSION = "20260721_00"
_SLACK_VERSION = "20260721_00"


class MissingAuthConfig(Exception):
    """A source was asked to connect but has no Composio auth config id. The
    route turns this into a 503: it is a deployment gap, not a user error."""


class ConnectionRepositoryLike(Protocol):
    def mark_active(
        self,
        user_id: str,
        provider: str,
        *,
        composio_connected_account_id: str,
        provider_login: str | None = None,
        provider_user_id: str | None = None,
    ) -> None:
        ...

    def mark_status(self, user_id: str, provider: str, status: str) -> None:
        ...

    def get(self, user_id: str, provider: str) -> ConnectionRow | None:
        ...

    def delete(self, user_id: str, provider: str) -> None:
        ...


class ConnectionService(Protocol):
    def list_sources(self, user_id: str, items: list[FeedItem]) -> list[SourceInfo]:
        ...

    def link_url(self, user_id: str, source: Source) -> str:
        ...

    def status(self, user_id: str, source: Source) -> SourceInfo:
        ...

    def disconnect(self, user_id: str, source: Source) -> None:
        ...


class DefaultConnectionService:
    def __init__(
        self,
        composio: Any,
        auth_config_ids: dict[Source, str],
        repo: ConnectionRepositoryLike,
        callback_url: str = "",
    ) -> None:
        self._composio = composio
        self._auth_config_ids = auth_config_ids
        self._repo = repo
        self._callback_url = callback_url

    def list_sources(self, user_id: str, items: list[FeedItem]) -> list[SourceInfo]:
        statuses = self._statuses(user_id)
        counts = self._counts(items)

        return [
            SourceInfo(
                source=source,
                label=LABELS[source],
                status=statuses.get(source, (ConnectionStatus.DISCONNECTED, None))[0],
                connected_account_id=statuses.get(source, (None, None))[1],
                count=counts.get(source, (0, 0))[0],
                urgent=counts.get(source, (0, 0))[1],
            )
            for source, _, _ in CATALOGUE
        ]

    def link_url(self, user_id: str, source: Source) -> str:
        auth_config_id = self._auth_config_ids.get(source)
        if not auth_config_id:
            raise MissingAuthConfig(source.value)
        result = self._composio.connected_accounts.link(
            user_id=user_id,
            auth_config_id=auth_config_id,
            callback_url=self._callback_url or None,
        )
        return getattr(result, "redirect_url", "") or ""

    def status(self, user_id: str, source: Source) -> SourceInfo:
        """Reconcile one source against Composio and record the result.

        Called by the poll after the user returns from consent. On the first
        ACTIVE it resolves the provider identity and writes the connection row;
        Composio stays the source of truth for status, the row is what ingest and
        disconnect read.
        """
        entry = self._statuses(user_id, toolkit=SOURCE_TO_TOOLKIT[source]).get(source)
        status = entry[0] if entry else ConnectionStatus.DISCONNECTED
        account_id = entry[1] if entry else None

        if status is ConnectionStatus.CONNECTED and account_id:
            identity = self._resolve_identity(user_id, source)
            self._repo.mark_active(
                user_id,
                source.value,
                composio_connected_account_id=account_id,
                provider_login=identity.github_login,
                provider_user_id=identity.slack_user_id,
            )
        elif status is ConnectionStatus.EXPIRED:
            self._repo.mark_status(user_id, source.value, "expired")

        return SourceInfo(
            source=source,
            label=LABELS[source],
            status=status,
            connected_account_id=account_id,
        )

    def disconnect(self, user_id: str, source: Source) -> None:
        row = self._repo.get(user_id, source.value)
        account_id = row.composio_connected_account_id if row else None
        if account_id:
            try:
                self._composio.connected_accounts.delete(account_id)
            except Exception:
                # The local row is cleared regardless: leaving it would show a
                # connection the user just asked us to drop.
                log.warning("could not delete connected account %s", account_id, exc_info=True)
        self._repo.delete(user_id, source.value)

    # ----------------------------------------------------------- internals

    def _statuses(
        self, user_id: str, toolkit: str | None = None
    ) -> dict[Source, tuple[ConnectionStatus, str | None]]:
        kwargs: dict[str, Any] = {"user_ids": [user_id]}
        if toolkit is not None:
            kwargs["toolkit_slugs"] = [toolkit]
        try:
            response = self._composio.connected_accounts.list(**kwargs)
        except Exception:
            # The catalogue still renders. An empty list would tell the user
            # they have connected nothing, which is worse than "unknown".
            log.warning("could not read connected accounts", exc_info=True)
            return {source: (ConnectionStatus.ERROR, None) for source, _, _ in CATALOGUE}

        found: dict[Source, tuple[ConnectionStatus, str | None]] = {}
        for row in getattr(response, "items", response) or []:
            data = row if isinstance(row, dict) else row.__dict__
            raw_toolkit = data.get("toolkit")
            slug = (
                raw_toolkit.get("slug")
                if isinstance(raw_toolkit, dict)
                else getattr(raw_toolkit, "slug", None)
            )
            source = TOOLKIT_TO_SOURCE.get(slug or "")
            if source is None:
                continue

            status = str(data.get("status") or "").upper()
            account_id = data.get("id")

            if status in _LIVE:
                # A live record always wins. One toolkit can carry both an
                # abandoned attempt and a working connection, and reporting the
                # dead one says Calendar is broken while it quietly works.
                found[source] = (ConnectionStatus.CONNECTED, account_id)
            elif status in _BROKEN:
                if found.get(source, (None,))[0] is not ConnectionStatus.CONNECTED:
                    found[source] = (ConnectionStatus.EXPIRED, account_id)
            # INITIATED and INITIALIZING are half-finished sign-ins, not
            # connections, and stay absent so the row reads "Connect".

        return found

    def _resolve_identity(self, user_id: str, source: Source) -> Identity:
        """Who the user is on the provider, resolved once at connect. Only the
        two sources whose rules need it are handled; the rest keep an empty
        identity, which is all `mark_active` stores for them."""
        try:
            if source is Source.GITHUB:
                data = self._execute(
                    "GITHUB_GET_THE_AUTHENTICATED_USER", {}, user_id, _GITHUB_VERSION
                )
                return Identity(github_login=data.get("login"))
            if source is Source.SLACK:
                data = self._execute("SLACK_TEST_AUTH", {}, user_id, _SLACK_VERSION)
                return Identity(
                    slack_user_id=data.get("user_id") or data.get("user_id_str")
                )
        except Exception:
            log.warning("could not resolve %s identity", source.value, exc_info=True)
        return Identity()

    def _execute(
        self, slug: str, arguments: dict, user_id: str, version: str
    ) -> dict:
        result = self._composio.tools.execute(
            slug, user_id=user_id, arguments=arguments, version=version
        )
        if isinstance(result, dict):
            return result.get("data") or {}
        return getattr(result, "data", {}) or {}

    @staticmethod
    def _counts(items: list[FeedItem]) -> dict[Source, tuple[int, int]]:
        counts: dict[Source, tuple[int, int]] = {}
        for item in items:
            try:
                source = Source(item.source)
            except ValueError:
                continue
            if (item.llm_tier or item.rule_tier) is Tier.NOISE:
                continue
            total, urgent = counts.get(source, (0, 0))
            counts[source] = (
                total + 1,
                urgent + (1 if (item.llm_tier or item.rule_tier) is Tier.URGENT else 0),
            )
        return counts
