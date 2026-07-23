"""What the user has connected, and what each source is currently asking.

Sources is a menu, not a report. Every supported source is returned on every
call, in a fixed order, and only its status and counts change. The alternative,
building the list from whatever appears in the feed, cannot distinguish a source
with nothing to say from one that was never connected, and cannot show the user
what they are missing.

Connecting an account is a separate concern (``link_url``) and is deliberately
thin: today the demo runs on accounts already connected in the Composio
dashboard, and a sign-up flow later only has to call this one method.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from backend.models.feed import FeedItem
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
_BROKEN = {"EXPIRED", "REVOKED", "FAILED"}


class ConnectionService(Protocol):
    def list_sources(self, user_id: str, items: list[FeedItem]) -> list[SourceInfo]:
        ...

    def link_url(self, user_id: str, source: Source) -> str:
        ...


class DefaultConnectionService:
    def __init__(self, composio: Any, composio_user_id: str) -> None:
        self._composio = composio
        self._composio_user_id = composio_user_id

    def list_sources(self, user_id: str, items: list[FeedItem]) -> list[SourceInfo]:
        statuses = self._statuses()
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
        toolkit = SOURCE_TO_TOOLKIT[source]
        result = self._composio.connected_accounts.link(
            user_id=self._composio_user_id, auth_config_id=None, toolkit=toolkit
        )
        return getattr(result, "redirect_url", "") or ""

    # ----------------------------------------------------------- internals

    def _statuses(self) -> dict[Source, tuple[ConnectionStatus, str | None]]:
        try:
            response = self._composio.connected_accounts.list(
                user_ids=[self._composio_user_id]
            )
        except Exception:
            # The catalogue still renders. An empty list would tell the user
            # they have connected nothing, which is worse than "unknown".
            log.warning("could not read connected accounts", exc_info=True)
            return {source: (ConnectionStatus.ERROR, None) for source, _, _ in CATALOGUE}

        found: dict[Source, tuple[ConnectionStatus, str | None]] = {}
        for row in getattr(response, "items", response) or []:
            data = row if isinstance(row, dict) else row.__dict__
            toolkit = data.get("toolkit")
            slug = (
                toolkit.get("slug")
                if isinstance(toolkit, dict)
                else getattr(toolkit, "slug", None)
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
