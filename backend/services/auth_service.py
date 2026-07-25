"""The auth flow, owned end to end.

One service holds the whole thing: send an OTP, verify it, register a password
against it, sign in, rotate refresh tokens, and reset a password. OTP lives here
rather than in its own module because it is not independently useful; it exists
only to gate registration and reset, and splitting it would be a shallow module
for its own sake.

Every failure is a typed exception, so the router maps it to a status code and
the client can say which of "wrong code", "too many tries" and "expired" it was.
The service never reads configuration or the wall clock directly: the clock is
injected, which is what makes cooldowns and expiry testable without sleeping.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from backend.models.auth import OtpPurpose, OtpRecord, TokenPair, UserRecord
from backend.repositories.credentials_repository import CredentialsRepository
from backend.services.passwords import PasswordHasher
from backend.tokens import TokenCodec, hash_token, new_refresh_token


class AuthError(Exception):
    """Base for everything the auth flow refuses."""


class EmailAlreadyRegistered(AuthError):
    ...


class OtpNotFound(AuthError):
    ...


class OtpExpired(AuthError):
    ...


class OtpMismatch(AuthError):
    def __init__(self, remaining: int) -> None:
        super().__init__("incorrect code")
        self.remaining = remaining


class OtpLockedOut(AuthError):
    ...


class ResendTooSoon(AuthError):
    def __init__(self, retry_after: int) -> None:
        super().__init__("resend requested too soon")
        self.retry_after = retry_after


class InvalidCredentials(AuthError):
    ...


class RefreshInvalid(AuthError):
    ...


class RefreshReused(AuthError):
    ...


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _norm(email: str) -> str:
    return email.strip().lower()


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class AuthService(Protocol):
    def send_otp(self, email: str, purpose: OtpPurpose) -> None:
        ...

    def verify_otp(self, email: str, purpose: OtpPurpose, code: str) -> bool:
        ...

    def register(self, email: str, code: str, password: str) -> TokenPair:
        ...

    def authenticate(self, email: str, password: str) -> TokenPair:
        ...

    def refresh(self, refresh_token: str) -> TokenPair:
        ...

    def revoke(self, refresh_token: str) -> None:
        ...

    def reset_password(self, email: str, code: str, new_password: str) -> None:
        ...


class DefaultAuthService:
    def __init__(
        self,
        repo: CredentialsRepository,
        passwords: PasswordHasher,
        codec: TokenCodec,
        send_email: Callable[[str, str], None],
        *,
        refresh_ttl: timedelta,
        otp_ttl: timedelta,
        resend_cooldown: timedelta,
        max_attempts: int,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._repo = repo
        self._passwords = passwords
        self._codec = codec
        self._send_email = send_email
        self._refresh_ttl = refresh_ttl
        self._otp_ttl = otp_ttl
        self._resend_cooldown = resend_cooldown
        self._max_attempts = max_attempts
        self._now = clock

    # --- OTP -----------------------------------------------------------
    def send_otp(self, email: str, purpose: OtpPurpose) -> None:
        email = _norm(email)
        now = self._now()
        exists = self._repo.get_user_by_email(email) is not None

        if purpose is OtpPurpose.SIGNUP and exists:
            # Signup deliberately tells the user to sign in instead; the product
            # needs that message, and it is the one place existence leaks.
            raise EmailAlreadyRegistered()
        if purpose is OtpPurpose.RESET and not exists:
            # Reset must not leak existence: the route answers 200 either way,
            # so we simply do not send for an unknown address.
            return

        active = self._repo.get_active_otp(email, purpose)
        if active is not None:
            ready_at = active.last_sent_at + self._resend_cooldown
            if now < ready_at:
                raise ResendTooSoon(int((ready_at - now).total_seconds()))

        code = f"{secrets.randbelow(1_000_000):06d}"
        self._repo.upsert_otp(
            email, purpose, _hash_code(code), now + self._otp_ttl, now
        )
        self._send_email(email, code)

    def verify_otp(self, email: str, purpose: OtpPurpose, code: str) -> bool:
        self._check_otp(_norm(email), purpose, code)
        return True

    def _check_otp(self, email: str, purpose: OtpPurpose, code: str) -> OtpRecord:
        otp = self._repo.get_active_otp(email, purpose)
        if otp is None:
            raise OtpNotFound()
        if self._now() > otp.expires_at:
            raise OtpExpired()

        attempts = self._repo.increment_otp_attempts(otp.id)
        if attempts > self._max_attempts:
            self._repo.consume_otp(otp.id, self._now())
            raise OtpLockedOut()

        if not secrets.compare_digest(otp.code_hash, _hash_code(code.strip())):
            raise OtpMismatch(remaining=self._max_attempts - attempts)
        return otp

    # --- registration & sign-in ---------------------------------------
    def register(self, email: str, code: str, password: str) -> TokenPair:
        email = _norm(email)
        if self._repo.get_user_by_email(email) is not None:
            raise EmailAlreadyRegistered()

        otp = self._check_otp(email, OtpPurpose.SIGNUP, code)
        user = self._repo.create_user(email, self._passwords.hash(password))
        self._repo.consume_otp(otp.id, self._now())
        return self._issue(user.id)

    def authenticate(self, email: str, password: str) -> TokenPair:
        user = self._repo.get_user_by_email(_norm(email))
        if (
            user is None
            or user.password_hash is None
            or not self._passwords.verify(password, user.password_hash)
        ):
            # One error for unknown-email and wrong-password alike, so neither
            # can be told from the other.
            raise InvalidCredentials()
        return self._issue(user.id)

    # --- refresh & logout ---------------------------------------------
    def refresh(self, refresh_token: str) -> TokenPair:
        now = self._now()
        record = self._repo.get_refresh(hash_token(refresh_token))
        if record is None:
            raise RefreshInvalid()
        if record.revoked_at is not None:
            # A revoked token presented again is a token that was rotated away
            # and then reused: treat it as theft and drop the whole family.
            self._repo.revoke_all_for_user(record.user_id, now)
            raise RefreshReused()
        if now > record.expires_at:
            raise RefreshInvalid()

        self._repo.revoke_refresh(record.id, now)
        return self._issue(record.user_id, rotated_from=record.id)

    def revoke(self, refresh_token: str) -> None:
        record = self._repo.get_refresh(hash_token(refresh_token))
        if record is not None and record.revoked_at is None:
            self._repo.revoke_refresh(record.id, self._now())

    # --- reset ---------------------------------------------------------
    def reset_password(self, email: str, code: str, new_password: str) -> None:
        email = _norm(email)
        otp = self._check_otp(email, OtpPurpose.RESET, code)
        user = self._repo.get_user_by_email(email)
        if user is None:
            raise InvalidCredentials()
        self._repo.set_password(user.id, self._passwords.hash(new_password))
        self._repo.consume_otp(otp.id, self._now())
        # A password reset ends every existing session: a reset is what you do
        # when you think someone else has your account.
        self._repo.revoke_all_for_user(user.id, self._now())

    # --- internals -----------------------------------------------------
    def _issue(self, user_id: str, rotated_from: str | None = None) -> TokenPair:
        now = self._now()
        access = self._codec.sign_access(user_id, now)
        refresh = new_refresh_token()
        self._repo.store_refresh(
            user_id, hash_token(refresh), now + self._refresh_ttl, rotated_from
        )
        return TokenPair(access_token=access, refresh_token=refresh)
