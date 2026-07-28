"""Supabase-backed auth persistence.

Answers the same ``CredentialsRepository`` Protocol as the in-memory store, so
nothing above it changes. Like the feed repository it reaches Postgres with the
service role (RLS bypassed), so every query scopes on the key it is about:
``email`` for users and OTPs, ``user_id`` for tokens. A missing filter here is a
cross-account leak the database will not catch.

"One live OTP per (email, purpose)" is a database invariant (the partial unique
index in migration 0004). ``upsert_otp`` clears the previous live challenge
before inserting a fresh one, which is what keeps that insert from colliding with
the index and what makes a resend a real reset rather than a second live code.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.models.auth import OtpPurpose, OtpRecord, RefreshRecord, UserRecord
from backend.repositories.supabase_client import SupabaseClientProvider

_USERS = "users"
_OTPS = "email_otps"
_REFRESH = "refresh_tokens"


class SupabaseCredentialsRepository:
    def __init__(self, provider: SupabaseClientProvider) -> None:
        self._provider = provider

    @property
    def _db(self):
        return self._provider.get()

    # --- users ---------------------------------------------------------
    def get_user_by_email(self, email: str) -> UserRecord | None:
        rows = (
            self._db.table(_USERS)
            .select("id, email, password_hash, name, notify_level, created_at")
            .eq("email", email)
            .limit(1)
            .execute()
            .data
        )
        return UserRecord.model_validate(rows[0]) if rows else None

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        rows = (
            self._db.table(_USERS)
            .select("id, email, password_hash, name, notify_level, created_at")
            .eq("id", user_id)
            .limit(1)
            .execute()
            .data
        )
        return UserRecord.model_validate(rows[0]) if rows else None

    def create_user(self, email: str, password_hash: str) -> UserRecord:
        rows = (
            self._db.table(_USERS)
            .insert({"email": email, "password_hash": password_hash})
            .execute()
            .data
        )
        return UserRecord.model_validate(rows[0])

    def set_password(self, user_id: str, password_hash: str) -> None:
        self._db.table(_USERS).update({"password_hash": password_hash}).eq(
            "id", user_id
        ).execute()

    def set_name(self, user_id: str, name: str | None) -> None:
        self._db.table(_USERS).update({"name": name}).eq("id", user_id).execute()

    def set_notify_level(self, user_id: str, level: str) -> None:
        self._db.table(_USERS).update({"notify_level": level}).eq(
            "id", user_id
        ).execute()

    # --- otp -----------------------------------------------------------
    def upsert_otp(
        self,
        email: str,
        purpose: OtpPurpose,
        code_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        # Clear any live challenge first, so the fresh insert cannot collide with
        # the (email, purpose) where consumed_at is null unique index.
        self._db.table(_OTPS).delete().eq("email", email).eq(
            "purpose", purpose.value
        ).is_("consumed_at", "null").execute()
        self._db.table(_OTPS).insert(
            {
                "email": email,
                "purpose": purpose.value,
                "code_hash": code_hash,
                "expires_at": expires_at.isoformat(),
                "attempts": 0,
                "last_sent_at": now.isoformat(),
            }
        ).execute()

    def get_active_otp(self, email: str, purpose: OtpPurpose) -> OtpRecord | None:
        rows = (
            self._db.table(_OTPS)
            .select("*")
            .eq("email", email)
            .eq("purpose", purpose.value)
            .is_("consumed_at", "null")
            .order("last_sent_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return OtpRecord.model_validate(rows[0]) if rows else None

    def increment_otp_attempts(self, otp_id: str) -> int:
        rows = (
            self._db.table(_OTPS)
            .select("attempts")
            .eq("id", otp_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            return 0
        new_count = int(rows[0]["attempts"]) + 1
        self._db.table(_OTPS).update({"attempts": new_count}).eq(
            "id", otp_id
        ).execute()
        return new_count

    def consume_otp(self, otp_id: str, now: datetime) -> None:
        self._db.table(_OTPS).update({"consumed_at": now.isoformat()}).eq(
            "id", otp_id
        ).execute()

    # --- refresh tokens ------------------------------------------------
    def store_refresh(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        rotated_from: str | None = None,
    ) -> str:
        rows = (
            self._db.table(_REFRESH)
            .insert(
                {
                    "user_id": user_id,
                    "token_hash": token_hash,
                    "expires_at": expires_at.isoformat(),
                    "rotated_from": rotated_from,
                }
            )
            .execute()
            .data
        )
        return rows[0]["id"]

    def get_refresh(self, token_hash: str) -> RefreshRecord | None:
        rows = (
            self._db.table(_REFRESH)
            .select("*")
            .eq("token_hash", token_hash)
            .limit(1)
            .execute()
            .data
        )
        return RefreshRecord.model_validate(rows[0]) if rows else None

    def revoke_refresh(self, token_id: str, now: datetime) -> None:
        self._db.table(_REFRESH).update({"revoked_at": now.isoformat()}).eq(
            "id", token_id
        ).execute()

    def revoke_all_for_user(self, user_id: str, now: datetime) -> None:
        self._db.table(_REFRESH).update({"revoked_at": now.isoformat()}).eq(
            "user_id", user_id
        ).is_("revoked_at", "null").execute()
