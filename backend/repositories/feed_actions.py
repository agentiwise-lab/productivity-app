"""The durable action ledger (``feed_actions``).

The feed content lives in Redis (ephemeral, 24h TTL). The one thing that must
survive an eviction or a Redis restart is what the *user* did to an item:
snoozed, dismissed, handled. That is this ledger, keyed on ``(user_id,
source_ref)`` so it stays valid across a re-ingest that mints a fresh Redis row.

The read path overlays this onto the Redis rows (drop dismissed, hide snoozed).
Writes go here first (durable), then the Redis row is updated: a crash in between
self-heals because the overlay hides the item anyway.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from backend.models.feed import FeedStatus


class FeedAction(BaseModel):
    status: FeedStatus
    snoozed_until: datetime | None = None
    handled_at: datetime | None = None


class FeedActionsRepository(Protocol):
    def record(
        self,
        user_id: str,
        source_ref: str,
        *,
        status: FeedStatus,
        at: datetime,
        snoozed_until: datetime | None = None,
        handled_at: datetime | None = None,
    ) -> None:
        ...

    def statuses_for(self, user_id: str) -> dict[str, FeedAction]:
        """Every acted/snoozed/dismissed source_ref for this user, for the
        read-time overlay. Absent source_refs are unread by default."""
        ...

    def delete_by_source(self, user_id: str, source: str) -> None:
        """Drop a whole source's actions (on disconnect)."""
        ...


class InMemoryFeedActionsRepository:
    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], FeedAction] = {}

    def record(
        self,
        user_id: str,
        source_ref: str,
        *,
        status: FeedStatus,
        at: datetime,
        snoozed_until: datetime | None = None,
        handled_at: datetime | None = None,
    ) -> None:
        self._by_key[(user_id, source_ref)] = FeedAction(
            status=status, snoozed_until=snoozed_until, handled_at=handled_at
        )

    def statuses_for(self, user_id: str) -> dict[str, FeedAction]:
        return {
            source_ref: action
            for (uid, source_ref), action in self._by_key.items()
            if uid == user_id
        }

    def delete_by_source(self, user_id: str, source: str) -> None:
        prefix = f"{source}:"
        for key in list(self._by_key):
            uid, source_ref = key
            if uid == user_id and source_ref.startswith(prefix):
                del self._by_key[key]
