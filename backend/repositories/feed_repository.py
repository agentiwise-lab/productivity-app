"""Feed persistence contract plus an in-memory implementation.

The contract is what services depend on. ``InMemoryFeedRepository`` is the test
and local implementation; ``SupabaseFeedRepository`` implements the same
Protocol with no change to callers.

Isolation is enforced here rather than trusted to callers: every method takes a
``user_id`` and nothing crosses it, which is the same rule the database enforces
again through RLS. Two layers, because a leak between users is the one bug this
product cannot survive.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from backend.models.feed import FeedItem, FeedStatus, TierSource
from backend.models.tiers import Tier, TypeTag

RETENTION = timedelta(days=30)

# Items in these states have been dealt with and leave the feed at once (3.11).
_CLOSED = {FeedStatus.ACTED, FeedStatus.DISMISSED}


class FeedRepository(Protocol):
    def upsert(self, item: FeedItem) -> FeedItem:
        """Insert or refresh from the source, by (user_id, source_ref).

        This is the ingest path and it owns the source's content only. It never
        writes the user's own state: a refetch of a notification must not undo a
        reply the user already sent. Use ``mark_handled`` for that.
        """
        ...

    def mark_handled(
        self, user_id: str, item_id: str, *, status: FeedStatus, at: datetime
    ) -> FeedItem | None:
        """Record that the user dealt with an item. Returns None if it is not
        this user's."""
        ...

    def snooze(self, user_id: str, item_id: str, until: datetime) -> FeedItem | None:
        """Hide an item until a time. Distinct from ``mark_handled``: nothing
        was done about it, so it has to come back."""
        ...

    def get(self, user_id: str, item_id: str) -> FeedItem | None:
        ...

    def list_by_user(
        self, user_id: str, now: datetime | None = None
    ) -> list[FeedItem]:
        """Live items only: unhandled, and inside the 30-day window."""
        ...

    def list_pending_classification(
        self, user_id: str, limit: int = 20
    ) -> list[FeedItem]:
        """Items the rules deferred and the model has not yet judged."""
        ...

    def apply_classification(
        self,
        user_id: str,
        item_id: str,
        *,
        tier: Tier,
        summary: str,
        reason: str,
        at: datetime,
    ) -> FeedItem | None:
        """Record the model's verdict. Returns None when the item is not this
        user's, so a misrouted event cannot write across accounts. ``at`` also
        stamps ``llm_attempted_at`` so a re-run does not re-judge it."""
        ...

    def mark_attempted(
        self, user_id: str, item_ids: list[str], *, at: datetime
    ) -> None:
        """Record that the model tried these items and produced no verdict (a
        failed batch, or an id it silently dropped). They stop being *held* and
        surface at their band ceiling; a later pass may still succeed. Only rows
        still lacking an ``llm_tier`` are touched, so this never clobbers a
        verdict that landed in between."""
        ...


class InMemoryFeedRepository:
    """Dict-backed store keyed by (user_id, source_ref) for dedupe."""

    def __init__(self) -> None:
        self._by_key: dict[tuple[str, str], FeedItem] = {}

    def upsert(self, item: FeedItem) -> FeedItem:
        key = (item.user_id, item.source_ref)
        existing = self._by_key.get(key)
        if existing is not None:
            item = item.model_copy(
                update={
                    # Keep the identity and the user's own actions on the row
                    # that is already there; only the source's content refreshes.
                    "id": existing.id,
                    "created_at": existing.created_at,
                    "status": existing.status,
                    "handled_at": existing.handled_at,
                    "snoozed_until": existing.snoozed_until,
                    **self._carried_classification(existing, item),
                }
            )
        self._by_key[key] = item
        return item

    @staticmethod
    def _carried_classification(existing: FeedItem, incoming: FeedItem) -> dict:
        """Carry the model's verdict across a refetch, but only while it still
        describes the item. A thread that gained replies is a different thing,
        so its old summary is worse than none at all.

        The attempt marker is carried in every case except a never-attempted
        item: a classified card whose content moved on must keep its marker so
        it stays visible at the ceiling and gets re-judged, rather than dropping
        back into the held state and vanishing mid-session (H1)."""
        if existing.llm_tier is None:
            # Held or failed: carry only a real attempt marker, so a failed item
            # stays visible; a truly-held one stays held.
            if existing.llm_attempted_at is not None:
                return {"llm_attempted_at": existing.llm_attempted_at}
            return {}
        if existing.content_hash != incoming.content_hash:
            # Stale verdict: re-queue (llm_tier drops to None via the fresh row)
            # but keep the marker so the card does not disappear until re-judged.
            return {"llm_attempted_at": existing.llm_attempted_at}
        return {
            "llm_tier": existing.llm_tier,
            "tier_source": existing.tier_source,
            "summary": existing.summary,
            "reason": existing.reason,
            "llm_attempted_at": existing.llm_attempted_at,
        }

    def mark_handled(
        self, user_id: str, item_id: str, *, status: FeedStatus, at: datetime
    ) -> FeedItem | None:
        item = self.get(user_id, item_id)
        if item is None:
            return None
        updated = item.model_copy(update={"status": status, "handled_at": at})
        self._by_key[(item.user_id, item.source_ref)] = updated
        return updated

    def snooze(self, user_id: str, item_id: str, until: datetime) -> FeedItem | None:
        item = self.get(user_id, item_id)
        if item is None:
            return None
        updated = item.model_copy(
            update={"status": FeedStatus.SNOOZED, "snoozed_until": until}
        )
        self._by_key[(item.user_id, item.source_ref)] = updated
        return updated

    def get(self, user_id: str, item_id: str) -> FeedItem | None:
        for item in self._by_key.values():
            if item.user_id == user_id and item.id == item_id:
                return item
        return None

    def list_by_user(
        self, user_id: str, now: datetime | None = None
    ) -> list[FeedItem]:
        now = now or datetime.now(timezone.utc)
        cutoff = now - RETENTION
        return [
            item
            for item in self._by_key.values()
            if item.user_id == user_id
            and item.status not in _CLOSED
            and (
                (item.occurred_at or item.created_at or now) >= cutoff
                # Two things are obligations rather than events, and neither
                # ages out. An item with a deadline: Linear issues last touched
                # in June were months overdue and invisible at the same time.
                # And anything assigned to this user: a task does not stop being
                # yours because nobody edited it for a month. That one silently
                # hid an Urgent issue and emptied the Later tab.
                or item.deadline is not None
                or item.type_tag is TypeTag.ASSIGNED
            )
        ]

    def list_pending_classification(
        self, user_id: str, limit: int = 20
    ) -> list[FeedItem]:
        pending = [
            item
            for item in self._by_key.values()
            if item.user_id == user_id and item.needs_llm and item.llm_tier is None
        ]
        return pending[:limit]

    def apply_classification(
        self,
        user_id: str,
        item_id: str,
        *,
        tier: Tier,
        summary: str,
        reason: str,
        at: datetime,
    ) -> FeedItem | None:
        item = self.get(user_id, item_id)
        if item is None:
            return None
        updated = item.model_copy(
            update={
                "llm_tier": tier,
                "tier_source": TierSource.LLM,
                "summary": summary,
                "reason": reason,
                "llm_attempted_at": at,
            }
        )
        self._by_key[(item.user_id, item.source_ref)] = updated
        return updated

    def mark_attempted(
        self, user_id: str, item_ids: list[str], *, at: datetime
    ) -> None:
        wanted = set(item_ids)
        for key, item in list(self._by_key.items()):
            if (
                item.user_id == user_id
                and item.id in wanted
                and item.llm_tier is None
            ):
                self._by_key[key] = item.model_copy(
                    update={"llm_attempted_at": at}
                )
