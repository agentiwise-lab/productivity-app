"""Redis-backed feed store (Phase 0).

The feed content and the model's verdict live in Redis with a 24h TTL, reset on
every write; the durable store keeps only the action ledger. Same
``FeedRepository`` Protocol as the in-memory and Supabase stores, so nothing above
it changes.

Layout: one hash per user, ``feed:{user_id}``, field = ``source_ref``, value =
the JSON of the row minus the three ledger-owned fields (status / snoozed_until /
handled_at). Reads overlay the ledger back on.

The item id is deterministic — ``uuid5(user_id + ":" + source_ref)`` — so a card
keeps the same id across an eviction and a re-ingest, and the action routes
(which key on the id) resolve to the same row.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.models.feed import FeedItem, FeedStatus, TierSource
from backend.models.tiers import Tier, TypeTag
from backend.repositories.feed_actions import FeedActionsRepository
from backend.repositories.feed_repository import RETENTION, InMemoryFeedRepository

# A fixed namespace so the id is stable across processes and restarts.
_NAMESPACE = uuid.UUID("6f2a1c9e-1b3d-4f7a-9c2e-8d5b0a4e7c11")

# Ledger-owned fields, never serialized into the Redis row.
_LEDGER_FIELDS = ("status", "snoozed_until", "handled_at")

_CLOSED = {FeedStatus.ACTED, FeedStatus.DISMISSED}

TTL_SECONDS = 86_400  # 24h, reset on every write


def item_id(user_id: str, source_ref: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, f"{user_id}:{source_ref}"))


class RedisFeedRepository:
    def __init__(
        self,
        redis: Any,
        ledger: FeedActionsRepository,
        clock: Any | None = None,
    ) -> None:
        self._r = redis
        self._ledger = ledger
        self._now = clock or (lambda: datetime.now(timezone.utc))

    # ------------------------------------------------------------ helpers

    def _key(self, user_id: str) -> str:
        return f"feed:{user_id}"

    @staticmethod
    def _serialize(item: FeedItem) -> str:
        data = item.model_dump(mode="json")
        for field in _LEDGER_FIELDS:
            data.pop(field, None)
        return json.dumps(data)

    @staticmethod
    def _deserialize(raw: Any) -> FeedItem:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return FeedItem.model_validate(json.loads(raw))

    def _rows(self, user_id: str) -> dict[str, FeedItem]:
        """Every stored row for the user, source_ref -> FeedItem (no overlay)."""
        stored = self._r.hgetall(self._key(user_id)) or {}
        out: dict[str, FeedItem] = {}
        for field, raw in stored.items():
            source_ref = field.decode("utf-8") if isinstance(field, bytes) else field
            try:
                out[source_ref] = self._deserialize(raw)
            except Exception:
                continue  # a malformed row is dropped, not fatal
        return out

    def _overlay(self, item: FeedItem, user_id: str, actions: dict) -> FeedItem:
        action = actions.get(item.source_ref)
        if action is None:
            return item
        return item.model_copy(
            update={
                "status": action.status,
                "snoozed_until": action.snoozed_until,
                "handled_at": action.handled_at,
            }
        )

    def _find_by_id(self, user_id: str, item_id_: str) -> tuple[str, FeedItem] | None:
        for source_ref, item in self._rows(user_id).items():
            if item.id == item_id_:
                return source_ref, item
        return None

    def _store(self, item: FeedItem) -> None:
        key = self._key(item.user_id)
        self._r.hset(key, item.source_ref, self._serialize(item))
        self._r.expire(key, TTL_SECONDS)

    # ------------------------------------------------------------- ingest

    def upsert(self, item: FeedItem) -> FeedItem:
        # The id is derived from (user_id, source_ref), not minted per row, so it
        # survives eviction and re-ingest.
        item = item.model_copy(
            update={"id": item_id(item.user_id, item.source_ref)}
        )
        existing = self._rows(item.user_id).get(item.source_ref)
        if existing is not None:
            item = item.model_copy(
                update={
                    "created_at": existing.created_at,
                    **InMemoryFeedRepository._carried_classification(existing, item),
                }
            )
        self._store(item)
        return item

    # -------------------------------------------------------------- reads

    def get(self, user_id: str, item_id_: str) -> FeedItem | None:
        found = self._find_by_id(user_id, item_id_)
        if found is None:
            return None
        _, item = found
        return self._overlay(item, user_id, self._ledger.statuses_for(user_id))

    def list_by_user(
        self, user_id: str, now: datetime | None = None
    ) -> list[FeedItem]:
        now = now or self._now()
        cutoff = now - RETENTION
        actions = self._ledger.statuses_for(user_id)
        out: list[FeedItem] = []
        for item in self._rows(user_id).values():
            item = self._overlay(item, user_id, actions)
            if item.status in _CLOSED:
                continue
            if (
                (item.occurred_at or item.created_at or now) >= cutoff
                or item.deadline is not None
                or item.type_tag is TypeTag.ASSIGNED
            ):
                out.append(item)
        return out

    def list_pending_classification(
        self, user_id: str, limit: int = 20
    ) -> list[FeedItem]:
        pending = [
            item
            for item in self._rows(user_id).values()
            if item.needs_llm and item.llm_tier is None
        ]
        return pending[:limit]

    # ------------------------------------------------------------- writes

    def apply_classification(
        self,
        user_id: str,
        item_id_: str,
        *,
        tier: Tier,
        summary: str,
        reason: str,
        at: datetime,
    ) -> FeedItem | None:
        found = self._find_by_id(user_id, item_id_)
        if found is None:
            return None
        _, item = found
        updated = item.model_copy(
            update={
                "llm_tier": tier,
                "tier_source": TierSource.LLM,
                "summary": summary,
                "reason": reason,
                "llm_attempted_at": at,
            }
        )
        self._store(updated)
        return updated

    def mark_attempted(
        self, user_id: str, item_ids: list[str], *, at: datetime
    ) -> None:
        wanted = set(item_ids)
        for item in self._rows(user_id).values():
            if item.id in wanted and item.llm_tier is None:
                self._store(item.model_copy(update={"llm_attempted_at": at}))

    def mark_handled(
        self, user_id: str, item_id_: str, *, status: FeedStatus, at: datetime
    ) -> FeedItem | None:
        found = self._find_by_id(user_id, item_id_)
        if found is None:
            return None
        source_ref, item = found
        # Durable ledger first: a crash before the Redis update self-heals because
        # the overlay hides it anyway; the reverse order would lose the action.
        self._ledger.record(user_id, source_ref, status=status, at=at, handled_at=at)
        if status in _CLOSED:
            # Terminal: free the Redis field. A re-ingest re-appends it, but the
            # ledger keeps hiding it via the overlay.
            self._r.hdel(self._key(user_id), source_ref)
        return item.model_copy(update={"status": status, "handled_at": at})

    def snooze(
        self, user_id: str, item_id_: str, until: datetime
    ) -> FeedItem | None:
        found = self._find_by_id(user_id, item_id_)
        if found is None:
            return None
        source_ref, item = found
        self._ledger.record(
            user_id,
            source_ref,
            status=FeedStatus.SNOOZED,
            at=self._now(),
            snoozed_until=until,
        )
        return item.model_copy(
            update={"status": FeedStatus.SNOOZED, "snoozed_until": until}
        )
