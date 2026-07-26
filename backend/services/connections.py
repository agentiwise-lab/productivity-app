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
from typing import Any, Callable, Protocol

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
#: Half-finished sign-ins. Once a live account exists they are abandoned junk,
#: and left alone they pile up one per retry (BUG-11), so finalize deletes them.
_PENDING = {"INITIATED", "INITIALIZING"}

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

    def list(self, user_id: str) -> list[ConnectionRow]:
        ...

    def delete(self, user_id: str, provider: str) -> None:
        ...


class TriggerProvisionerLike(Protocol):
    def provision(
        self, user_id: str, source: Source, connected_account_id: str
    ) -> None:
        ...


class ConnectionService(Protocol):
    def list_sources(self, user_id: str, items: list[FeedItem]) -> list[SourceInfo]:
        ...

    def link_url(self, user_id: str, source: Source) -> str:
        ...

    def finalize(self, user_id: str, source: Source) -> SourceInfo:
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
        provisioner: TriggerProvisionerLike,
        callback_url: str = "",
        background: Callable[[Callable[[], None]], None] | None = None,
    ) -> None:
        self._composio = composio
        self._auth_config_ids = auth_config_ids
        self._repo = repo
        self._provisioner = provisioner
        self._callback_url = callback_url
        # Where the slow half of a finalize runs. Production passes an executor so
        # trigger provisioning and stale-account cleanup happen off the connect
        # poll's critical path (they are several serial Composio calls, and the
        # poll is what flips the UI to "connected"). Tests leave it None, which
        # runs the work inline so behaviour is identical and assertable.
        self._background = background

    def list_sources(self, user_id: str, items: list[FeedItem]) -> list[SourceInfo]:
        statuses = self._statuses(user_id)
        self._heal(user_id, statuses)
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

    def finalize(self, user_id: str, source: Source) -> SourceInfo:
        """The one idempotent reconcile that makes a source usable.

        Reads the live accounts for the source's toolkit and, when one is active,
        records the connection row, provisions the source's triggers (the step
        that was missing, and the reason the feed never filled), and clears away
        any half-finished attempts. Safe to call on every poll and every source
        list: repeated calls converge on the same row and the same trigger set.

        The order matters. The row is written before triggers are provisioned so
        that ingest can resolve identity the instant events start arriving; and
        stale attempts are deleted only after a live account is confirmed, so we
        never delete the sole attempt mid-connect.
        """
        toolkit = SOURCE_TO_TOOLKIT[source]
        try:
            accounts = self._raw_accounts(user_id, toolkit)
        except Exception:
            log.warning("could not reconcile %s", source.value, exc_info=True)
            return SourceInfo(
                source=source, label=LABELS[source], status=ConnectionStatus.ERROR
            )

        live_id: str | None = None
        stale_ids: list[str] = []
        expired = False
        for data in accounts:
            status = str(data.get("status") or "").upper()
            account_id = data.get("id")
            if status in _LIVE:
                live_id = account_id
            elif status in _PENDING:
                if account_id:
                    stale_ids.append(account_id)
            elif status in _BROKEN:
                expired = True

        if live_id:
            identity = self._resolve_identity(user_id, source)
            self._repo.mark_active(
                user_id,
                source.value,
                composio_connected_account_id=live_id,
                provider_login=identity.github_login,
                provider_user_id=identity.slack_user_id,
            )
            # The row is written; the app can read "connected" now. Trigger
            # provisioning and stale-attempt cleanup are several more serial
            # Composio calls, so they run in the background rather than holding up
            # the poll. Both are idempotent and `_heal` re-runs them if this drops,
            # so deferring them is safe.
            self._defer(
                lambda: self._provision_and_prune(user_id, source, live_id, stale_ids)
            )
            return SourceInfo(
                source=source,
                label=LABELS[source],
                status=ConnectionStatus.CONNECTED,
                connected_account_id=live_id,
            )

        if expired:
            self._repo.mark_status(user_id, source.value, "expired")
            return SourceInfo(
                source=source, label=LABELS[source], status=ConnectionStatus.EXPIRED
            )

        return SourceInfo(
            source=source, label=LABELS[source], status=ConnectionStatus.DISCONNECTED
        )

    def status(self, user_id: str, source: Source) -> SourceInfo:
        """The connect poll. It is exactly the reconcile: the app polls this
        after the user returns from consent, and each poll converges the row and
        the triggers, so a connection finishes even when web OAuth has no
        deep-link return to tell us the moment it went active."""
        return self.finalize(user_id, source)

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

    def _heal(
        self,
        user_id: str,
        statuses: dict[Source, tuple[ConnectionStatus, str | None]],
    ) -> None:
        """Reconcile any source Composio reports connected but that has no active
        row yet. This covers the case the connect poll missed entirely (RC-2):
        without it, ``list_sources`` would show a source as connected off the live
        status while ingest still had no row to resolve identity from. Once a row
        exists it is skipped, so a steady state costs one row read, not a reconcile
        per feed load.
        """
        connected = {
            source
            for source, (status, _) in statuses.items()
            if status is ConnectionStatus.CONNECTED
        }
        if not connected:
            return
        try:
            active = {
                row.provider for row in self._repo.list(user_id) if row.status == "active"
            }
        except Exception:
            log.warning("could not read connection rows to heal", exc_info=True)
            return
        for source in connected:
            if source.value not in active:
                self.finalize(user_id, source)

    def _raw_accounts(self, user_id: str, toolkit: str) -> list[dict]:
        response = self._composio.connected_accounts.list(
            user_ids=[user_id], toolkit_slugs=[toolkit]
        )
        return [
            row if isinstance(row, dict) else row.__dict__
            for row in getattr(response, "items", response) or []
        ]

    def _discard(self, account_ids: list[str]) -> None:
        for account_id in account_ids:
            try:
                self._composio.connected_accounts.delete(account_id)
            except Exception:
                log.warning(
                    "could not delete stale account %s", account_id, exc_info=True
                )

    def _provision_and_prune(
        self, user_id: str, source: Source, live_id: str, stale_ids: list[str]
    ) -> None:
        """The slow half of a finalize: create the source's triggers and delete
        the abandoned attempts. Runs on the background runner in production."""
        self._provisioner.provision(user_id, source, live_id)
        self._discard(stale_ids)

    def _defer(self, work: Callable[[], None]) -> None:
        if self._background is not None:
            self._background(work)
        else:
            work()

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
