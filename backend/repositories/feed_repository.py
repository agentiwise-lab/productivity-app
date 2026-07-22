"""Feed persistence contract + an in-memory implementation.

The contract is what services depend on. ``InMemoryFeedRepository`` is the tracer
/ test implementation; a Supabase-backed repository will implement the same
Protocol later with no change to callers. Isolation is enforced here: every read
is scoped to ``user_id``.
"""

from __future__ import annotations

from typing import Protocol

from backend.models.feed import FeedItem


class FeedRepository(Protocol):
    def upsert(self, item: FeedItem) -> FeedItem:
        """Insert or update by (user_id, source_ref). Returns the stored item."""
        ...

    def get(self, user_id: str, item_id: str) -> FeedItem | None:
        ...

    def list_by_user(self, user_id: str) -> list[FeedItem]:
        ...


class InMemoryFeedRepository:
    """Dict-backed store keyed by (user_id, source_ref) for dedupe."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], FeedItem] = {}

    def upsert(self, item: FeedItem) -> FeedItem:
        key = (item.user_id, item.source_ref)
        existing = self._by_key.get(key)
        if existing is not None:
            # Preserve the identity of the existing row; update its content.
            item = item.model_copy(
                update={"id": existing.id, "created_at": existing.created_at}
            )
        self._by_key[key] = item
        return item

    def get(self, user_id: str, item_id: str) -> FeedItem | None:
        for item in self._by_key.values():
            if item.user_id == user_id and item.id == item_id:
                return item
        return None

    def list_by_user(self, user_id: str) -> list[FeedItem]:
        return [item for item in self._by_key.values() if item.user_id == user_id]
