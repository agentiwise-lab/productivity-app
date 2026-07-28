"""Auth persistence contract plus an in-memory implementation.

Three concerns behind one contract: the user and their password hash, the live
OTP challenge, and the refresh-token family. ``InMemoryCredentialsRepository`` is
the test and local implementation; ``SupabaseCredentialsRepository`` implements
the same Protocol against Postgres with no change to callers.

Isolation is the repository's job, as everywhere else in this codebase: a
refresh token is only ever returned for the user it belongs to, and a lookup
crossing users returns nothing. The database enforces the same shape again
through the ``(email, purpose) where consumed_at is null`` unique index, which is
what "one live OTP per email and purpose" means here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol
import uuid

from backend.models.auth import OtpPurpose, OtpRecord, RefreshRecord, UserRecord


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CredentialsRepository(Protocol):
    # --- users ---------------------------------------------------------
    def get_user_by_email(self, email: str) -> UserRecord | None:
        ...

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        """The profile read for an authenticated request, keyed on the token's
        subject rather than the email the client typed."""
        ...

    def create_user(self, email: str, password_hash: str) -> UserRecord:
        """Insert the ``public.users`` row (and its uuid). This is the row every
        other table's ``user_id`` FK points at, so it must exist before any feed
        or connection row for the user."""
        ...

    def set_password(self, user_id: str, password_hash: str) -> None:
        ...

    def set_name(self, user_id: str, name: str | None) -> None:
        """The one profile write. ``None`` clears the name back to no-name."""
        ...

    def set_notify_level(self, user_id: str, level: str) -> None:
        """The other profile write. Validated by the caller and again by the
        column's check constraint; this only stores it."""
        ...

    # --- otp -----------------------------------------------------------
    def upsert_otp(
        self,
        email: str,
        purpose: OtpPurpose,
        code_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        """Replace any live challenge for this (email, purpose) with a fresh one:
        new code, attempts back to zero, ``last_sent_at`` now. A resend is this
        call, so the cooldown lives above it, in the service."""
        ...

    def get_active_otp(self, email: str, purpose: OtpPurpose) -> OtpRecord | None:
        """The one unconsumed challenge, if any. Expiry is the service's to
        judge; this returns it so the service can say *why* it failed."""
        ...

    def increment_otp_attempts(self, otp_id: str) -> int:
        """Returns the new attempt count, so the caller can lock out on it."""
        ...

    def consume_otp(self, otp_id: str, now: datetime) -> None:
        ...

    # --- refresh tokens ------------------------------------------------
    def store_refresh(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        rotated_from: str | None = None,
    ) -> str:
        """Persist a hashed refresh token; returns its row id."""
        ...

    def get_refresh(self, token_hash: str) -> RefreshRecord | None:
        ...

    def revoke_refresh(self, token_id: str, now: datetime) -> None:
        ...

    def revoke_all_for_user(self, user_id: str, now: datetime) -> None:
        """Kill every live token for a user. Used on logout-everywhere and, more
        importantly, when a revoked token is presented again (reuse = theft)."""
        ...


class InMemoryCredentialsRepository:
    def __init__(self) -> None:
        self._users: dict[str, UserRecord] = {}
        self._otps: dict[str, OtpRecord] = {}
        self._refresh: dict[str, RefreshRecord] = {}

    # --- users ---------------------------------------------------------
    def get_user_by_email(self, email: str) -> UserRecord | None:
        for user in self._users.values():
            if user.email == email:
                return user.model_copy()
        return None

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        user = self._users.get(user_id)
        return user.model_copy() if user is not None else None

    def create_user(self, email: str, password_hash: str) -> UserRecord:
        user = UserRecord(
            id=str(uuid.uuid4()),
            email=email,
            password_hash=password_hash,
            created_at=_utcnow(),
        )
        self._users[user.id] = user
        return user.model_copy()

    def set_password(self, user_id: str, password_hash: str) -> None:
        user = self._users.get(user_id)
        if user is not None:
            self._users[user_id] = user.model_copy(update={"password_hash": password_hash})

    def set_name(self, user_id: str, name: str | None) -> None:
        user = self._users.get(user_id)
        if user is not None:
            self._users[user_id] = user.model_copy(update={"name": name})

    def set_notify_level(self, user_id: str, level: str) -> None:
        user = self._users.get(user_id)
        if user is not None:
            self._users[user_id] = user.model_copy(update={"notify_level": level})

    # --- otp -----------------------------------------------------------
    def upsert_otp(
        self,
        email: str,
        purpose: OtpPurpose,
        code_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        existing = self._active_otp(email, purpose)
        if existing is not None:
            self._otps[existing.id] = existing.model_copy(
                update={
                    "code_hash": code_hash,
                    "expires_at": expires_at,
                    "attempts": 0,
                    "last_sent_at": now,
                }
            )
            return
        otp = OtpRecord(
            id=str(uuid.uuid4()),
            email=email,
            purpose=purpose,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
            consumed_at=None,
            last_sent_at=now,
        )
        self._otps[otp.id] = otp

    def get_active_otp(self, email: str, purpose: OtpPurpose) -> OtpRecord | None:
        found = self._active_otp(email, purpose)
        return found.model_copy() if found is not None else None

    def increment_otp_attempts(self, otp_id: str) -> int:
        otp = self._otps.get(otp_id)
        if otp is None:
            return 0
        updated = otp.model_copy(update={"attempts": otp.attempts + 1})
        self._otps[otp_id] = updated
        return updated.attempts

    def consume_otp(self, otp_id: str, now: datetime) -> None:
        otp = self._otps.get(otp_id)
        if otp is not None:
            self._otps[otp_id] = otp.model_copy(update={"consumed_at": now})

    def _active_otp(self, email: str, purpose: OtpPurpose) -> OtpRecord | None:
        for otp in self._otps.values():
            if otp.email == email and otp.purpose == purpose and otp.consumed_at is None:
                return otp
        return None

    # --- refresh tokens ------------------------------------------------
    def store_refresh(
        self,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        rotated_from: str | None = None,
    ) -> str:
        record = RefreshRecord(
            id=str(uuid.uuid4()),
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            rotated_from=rotated_from,
        )
        self._refresh[record.id] = record
        return record.id

    def get_refresh(self, token_hash: str) -> RefreshRecord | None:
        for record in self._refresh.values():
            if record.token_hash == token_hash:
                return record.model_copy()
        return None

    def revoke_refresh(self, token_id: str, now: datetime) -> None:
        record = self._refresh.get(token_id)
        if record is not None and record.revoked_at is None:
            self._refresh[token_id] = record.model_copy(update={"revoked_at": now})

    def revoke_all_for_user(self, user_id: str, now: datetime) -> None:
        for token_id, record in list(self._refresh.items()):
            if record.user_id == user_id and record.revoked_at is None:
                self._refresh[token_id] = record.model_copy(update={"revoked_at": now})
