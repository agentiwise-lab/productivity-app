"""Supabase-backed feed persistence.

Satisfies the same ``FeedRepository`` Protocol as the in-memory store, so
nothing above it changes. The contract tests in ``tests/test_repository.py`` are
the specification this must answer to.

It reaches Postgres with the service role, which bypasses RLS, so every query
here scopes on ``user_id`` explicitly. That is not belt and braces: with the
service role, a missing ``user_id`` filter is a cross-account leak, and RLS will
not catch it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from supabase import Client

from backend.models.feed import FeedItem, FeedStatus, TierSource
from backend.models.tiers import Tier
from backend.repositories.feed_repository import RETENTION

_TABLE = "feed_items"

# Columns the ingest path owns. Everything absent from this list belongs to the
# user (status, handled_at, snoozed_until) or to the model (llm_tier, summary,
# reason, tier_source), and a refetch from the source must not touch it.
_SOURCE_COLUMNS = (
    "user_id",
    "source",
    "source_ref",
    "rule_tier",
    "type_tag",
    "needs_llm",
    "title",
    "url",
    "repo",
    "context_chip",
    "sender_name",
    "sender_handle",
    "actors",
    "deadline",
    "occurred_at",
    "is_blocking",
    "content_hash",
    "raw",
)


class SupabaseFeedRepository:
    def __init__(self, client: Client) -> None:
        self._db = client

    # ------------------------------------------------------------- ingest

    def upsert(self, item: FeedItem) -> FeedItem:
        payload = {
            key: value
            for key, value in _serialize(item).items()
            if key in _SOURCE_COLUMNS
        }
        existing = self._find_by_source_ref(item.user_id, item.source_ref)

        if existing is None:
            rows = self._db.table(_TABLE).insert(payload).execute().data
            return _deserialize(rows[0])

        # A refetch whose content changed invalidates the model's verdict: the
        # old summary no longer describes the thing it summarised.
        if existing.get("content_hash") != item.content_hash:
            payload |= {
                "llm_tier": None,
                "summary": None,
                "reason": None,
                "tier_source": TierSource.RULE.value,
            }

        rows = (
            self._db.table(_TABLE)
            .update(payload)
            .eq("id", existing["id"])
            .eq("user_id", item.user_id)
            .execute()
            .data
        )
        return _deserialize(rows[0])

    # -------------------------------------------------------------- reads

    def get(self, user_id: str, item_id: str) -> FeedItem | None:
        rows = (
            self._db.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("id", item_id)
            .limit(1)
            .execute()
            .data
        )
        return _deserialize(rows[0]) if rows else None

    def list_by_user(
        self, user_id: str, now: datetime | None = None
    ) -> list[FeedItem]:
        now = now or datetime.now(timezone.utc)
        cutoff = (now - RETENTION).isoformat()
        rows = (
            self._db.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .in_("status", [FeedStatus.UNREAD.value, FeedStatus.SNOOZED.value])
            .gte("occurred_at", cutoff)
            .order("occurred_at", desc=True)
            .execute()
            .data
        )
        return [_deserialize(row) for row in rows]

    def list_pending_classification(
        self, user_id: str, limit: int = 20
    ) -> list[FeedItem]:
        rows = (
            self._db.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("needs_llm", True)
            .is_("llm_tier", "null")
            .order("occurred_at", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        return [_deserialize(row) for row in rows]

    # ------------------------------------------------------------- writes

    def mark_handled(
        self, user_id: str, item_id: str, *, status: FeedStatus, at: datetime
    ) -> FeedItem | None:
        rows = (
            self._db.table(_TABLE)
            .update({"status": status.value, "handled_at": at.isoformat()})
            .eq("user_id", user_id)
            .eq("id", item_id)
            .execute()
            .data
        )
        return _deserialize(rows[0]) if rows else None

    def snooze(self, user_id: str, item_id: str, until: datetime) -> FeedItem | None:
        rows = (
            self._db.table(_TABLE)
            .update(
                {
                    "status": FeedStatus.SNOOZED.value,
                    "snoozed_until": until.isoformat(),
                }
            )
            .eq("user_id", user_id)
            .eq("id", item_id)
            .execute()
            .data
        )
        return _deserialize(rows[0]) if rows else None

    def apply_classification(
        self, user_id: str, item_id: str, *, tier: Tier, summary: str, reason: str
    ) -> FeedItem | None:
        rows = (
            self._db.table(_TABLE)
            .update(
                {
                    "llm_tier": tier.value,
                    "tier_source": TierSource.LLM.value,
                    "summary": summary,
                    "reason": reason,
                }
            )
            .eq("user_id", user_id)
            .eq("id", item_id)
            .execute()
            .data
        )
        return _deserialize(rows[0]) if rows else None

    # ---------------------------------------------------------- retention

    def purge_expired(self, now: datetime | None = None) -> int:
        """Delete past the 30-day window. Later *holds* 30 days; it does not
        merely hide older rows (plan 3.11)."""
        now = now or datetime.now(timezone.utc)
        rows = (
            self._db.table(_TABLE)
            .delete()
            .lt("occurred_at", (now - RETENTION).isoformat())
            .execute()
            .data
        )
        return len(rows or [])

    # ----------------------------------------------------------- internal

    def _find_by_source_ref(self, user_id: str, source_ref: str) -> dict | None:
        rows = (
            self._db.table(_TABLE)
            .select("id, content_hash")
            .eq("user_id", user_id)
            .eq("source_ref", source_ref)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None


def _serialize(item: FeedItem) -> dict[str, Any]:
    return item.model_dump(mode="json")


def _deserialize(row: dict[str, Any]) -> FeedItem:
    return FeedItem.model_validate(row)


def retention_days() -> int:
    return int(RETENTION / timedelta(days=1))
