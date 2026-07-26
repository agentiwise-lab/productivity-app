"""Supabase-backed connection storage (``public.connections``).

Same ``ConnectionRepository`` contract as the in-memory store. Like the other
Supabase repositories it uses the service role, so every query scopes on
``user_id``; the ``unique(user_id, provider)`` on the table is what makes "one
connection per provider per user" a database fact, and mark_active honours it by
updating an existing row rather than inserting a second.

There are no tokens here. A row is a pointer to a Composio account plus the
status and identity we resolved at connect time.
"""

from __future__ import annotations

import logging

from backend.models.connections import ConnectionRow
from backend.models.identity import Identity
from backend.repositories.supabase_client import SupabaseClientProvider

log = logging.getLogger(__name__)

_TABLE = "connections"


class SupabaseConnectionRepository:
    def __init__(self, provider: SupabaseClientProvider) -> None:
        self._provider = provider

    @property
    def _db(self):
        return self._provider.get()

    def mark_active(
        self,
        user_id: str,
        provider: str,
        *,
        composio_connected_account_id: str,
        provider_login: str | None = None,
        provider_user_id: str | None = None,
    ) -> None:
        payload = {
            "composio_user_id": user_id,
            "composio_connected_account_id": composio_connected_account_id,
            "status": "active",
            "provider_login": provider_login,
            "provider_user_id": provider_user_id,
        }
        if self._raw(user_id, provider) is not None:
            self._db.table(_TABLE).update(payload).eq("user_id", user_id).eq(
                "provider", provider
            ).execute()
        else:
            self._db.table(_TABLE).insert(
                {"user_id": user_id, "provider": provider, **payload}
            ).execute()

    def mark_status(self, user_id: str, provider: str, status: str) -> None:
        self._db.table(_TABLE).update({"status": status}).eq("user_id", user_id).eq(
            "provider", provider
        ).execute()

    def get(self, user_id: str, provider: str) -> ConnectionRow | None:
        row = self._raw(user_id, provider)
        return ConnectionRow.model_validate(row) if row is not None else None

    def list(self, user_id: str) -> list[ConnectionRow]:
        rows = (
            self._db.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .execute()
            .data
        )
        return [ConnectionRow.model_validate(row) for row in rows]

    def delete(self, user_id: str, provider: str) -> None:
        self._db.table(_TABLE).delete().eq("user_id", user_id).eq(
            "provider", provider
        ).execute()

    def identity_for(self, user_id: str, provider: str) -> Identity:
        # Read from the ingest path, where the user_id came off a webhook. A
        # malformed one (not a valid uuid) makes Postgres raise 22P02; degrade to
        # an empty identity so the event still processes rather than 500-ing and
        # being redelivered forever (BUG-3).
        try:
            row = self.get(user_id, provider)
        except Exception:
            log.warning(
                "could not read identity for %s/%s", user_id, provider, exc_info=True
            )
            return Identity()
        return row.identity() if row is not None else Identity()

    def _raw(self, user_id: str, provider: str) -> dict | None:
        rows = (
            self._db.table(_TABLE)
            .select("*")
            .eq("user_id", user_id)
            .eq("provider", provider)
            .limit(1)
            .execute()
            .data
        )
        return rows[0] if rows else None
