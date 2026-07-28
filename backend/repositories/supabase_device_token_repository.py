"""Supabase-backed device tokens.

Answers the same ``DeviceTokenRepository`` Protocol as the in-memory store, so
nothing above it changes. Reaches Postgres with the service role (RLS bypassed),
which is why ``tokens_for`` scopes on ``user_id`` explicitly: a missing filter
here would send one person's notifications to everybody's phones.
"""

from __future__ import annotations

from backend.repositories.supabase_client import SupabaseClientProvider

_TOKENS = "device_tokens"


class SupabaseDeviceTokenRepository:
    def __init__(self, provider: SupabaseClientProvider) -> None:
        self._provider = provider

    @property
    def _db(self):
        return self._provider.get()

    def upsert(self, user_id: str, token: str, platform: str) -> None:
        """Insert, or hand the device to this user.

        ``upsert`` on the token primary key rather than insert-then-catch: the
        conflicting row must have its ``user_id`` **overwritten**, because the
        conflict is exactly the case where a phone changed hands. Leaving the
        old owner in place would keep delivering their work to whoever is
        holding the device now.
        """
        self._db.table(_TOKENS).upsert(
            {
                "token": token,
                "user_id": user_id,
                "platform": platform,
                "last_seen_at": "now()",
            },
            on_conflict="token",
        ).execute()

    def delete(self, token: str) -> None:
        self._db.table(_TOKENS).delete().eq("token", token).execute()

    def tokens_for(self, user_id: str) -> list[str]:
        rows = (
            self._db.table(_TOKENS)
            .select("token")
            .eq("user_id", user_id)
            .execute()
            .data
        ) or []
        return [row["token"] for row in rows]
