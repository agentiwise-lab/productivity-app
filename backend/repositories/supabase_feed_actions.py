"""Supabase-backed action ledger (``public.feed_actions``).

The one durable trace of what the user did to a feed item, keyed on
``(user_id, source_ref)`` so it survives the Redis row being evicted or
re-ingested. Same ``FeedActionsRepository`` Protocol as the in-memory store.

Service role, RLS bypassed, so every query scopes on ``user_id``.
"""

from __future__ import annotations

from datetime import datetime

from backend.models.feed import FeedStatus
from backend.repositories.feed_actions import FeedAction
from backend.repositories.supabase_client import SupabaseClientProvider

_TABLE = "feed_actions"


class SupabaseFeedActionsRepository:
    def __init__(self, provider: SupabaseClientProvider) -> None:
        self._provider = provider

    @property
    def _db(self):
        return self._provider.get()

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
        self._db.table(_TABLE).upsert(
            {
                "user_id": user_id,
                "source_ref": source_ref,
                "status": status.value,
                "snoozed_until": snoozed_until.isoformat() if snoozed_until else None,
                "handled_at": handled_at.isoformat() if handled_at else None,
                "updated_at": at.isoformat(),
            },
            on_conflict="user_id,source_ref",
        ).execute()

    def statuses_for(self, user_id: str) -> dict[str, FeedAction]:
        rows = (
            self._db.table(_TABLE)
            .select("source_ref, status, snoozed_until, handled_at")
            .eq("user_id", user_id)
            .execute()
            .data
        ) or []
        out: dict[str, FeedAction] = {}
        for row in rows:
            try:
                out[row["source_ref"]] = FeedAction(
                    status=FeedStatus(row["status"]),
                    snoozed_until=_parse(row.get("snoozed_until")),
                    handled_at=_parse(row.get("handled_at")),
                )
            except (KeyError, ValueError):
                continue
        return out

    def delete_by_source(self, user_id: str, source: str) -> None:
        # source_ref values start with "<source>:" (e.g. "gmail:...").
        (
            self._db.table(_TABLE)
            .delete()
            .eq("user_id", user_id)
            .like("source_ref", f"{source}:%")
            .execute()
        )


def _parse(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
