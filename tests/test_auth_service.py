"""AuthService contract.

Exercised against the in-memory repo, the fake hasher, the fake mailer, and a
real token codec, with an injected clock so cooldown and expiry are tested by
moving time rather than sleeping. The refusals are the point: a wrong code, a
locked-out challenge, a reused refresh token each have to fail in their own
distinguishable way.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.integrations.loops import FakeEmailService
from backend.models.auth import OtpPurpose
from backend.repositories.credentials_repository import InMemoryCredentialsRepository
from backend.services.auth_service import (
    DefaultAuthService,
    EmailAlreadyRegistered,
    InvalidCredentials,
    OtpExpired,
    OtpLockedOut,
    OtpMismatch,
    RefreshInvalid,
    RefreshReused,
    ResendTooSoon,
)
from backend.services.passwords import FakePasswordHasher
from backend.tokens import TokenCodec

START = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at

    def advance(self, delta):
        self.at = self.at + delta


@pytest.fixture
def ctx():
    repo = InMemoryCredentialsRepository()
    mail = FakeEmailService()
    clock = Clock(START)
    codec = TokenCodec(
        secret="test-secret-at-least-thirty-two-bytes-long!!",
        issuer="productivity-app",
        audience="app",
        access_ttl=timedelta(minutes=15),
    )
    service = DefaultAuthService(
        repo=repo,
        passwords=FakePasswordHasher(),
        codec=codec,
        send_email=mail.send_otp,
        refresh_ttl=timedelta(days=30),
        otp_ttl=timedelta(minutes=10),
        resend_cooldown=timedelta(seconds=60),
        max_attempts=5,
        clock=clock,
    )
    return service, repo, mail, clock, codec


# --- send / verify -----------------------------------------------------
def test_send_otp_emits_a_six_digit_code(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    code = mail.last_code("a@example.com")
    assert code is not None and len(code) == 6 and code.isdigit()


def test_send_otp_signup_rejects_a_registered_email(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    service.register("a@example.com", mail.last_code("a@example.com"), "pw-123456")
    with pytest.raises(EmailAlreadyRegistered):
        service.send_otp("a@example.com", OtpPurpose.SIGNUP)


def test_resend_within_cooldown_is_refused_then_allowed(ctx):
    service, _, _, clock, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    with pytest.raises(ResendTooSoon):
        service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    clock.advance(timedelta(seconds=61))
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)  # no raise


def test_verify_correct_code(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    assert service.verify_otp("a@example.com", OtpPurpose.SIGNUP, mail.last_code("a@example.com"))


def test_verify_wrong_code_reports_remaining(ctx):
    service, _, _, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    with pytest.raises(OtpMismatch) as exc:
        service.verify_otp("a@example.com", OtpPurpose.SIGNUP, "000000")
    assert exc.value.remaining == 4


def test_lockout_after_five_wrong_attempts(ctx):
    service, _, _, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    for _ in range(5):
        with pytest.raises(OtpMismatch):
            service.verify_otp("a@example.com", OtpPurpose.SIGNUP, "000000")
    with pytest.raises(OtpLockedOut):
        service.verify_otp("a@example.com", OtpPurpose.SIGNUP, "000000")


def test_expired_code_is_rejected(ctx):
    service, _, mail, clock, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    code = mail.last_code("a@example.com")
    clock.advance(timedelta(minutes=11))
    with pytest.raises(OtpExpired):
        service.verify_otp("a@example.com", OtpPurpose.SIGNUP, code)


# --- register / authenticate ------------------------------------------
def test_register_creates_user_and_token_subject_is_the_new_id(ctx):
    service, repo, mail, _, codec = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    tokens = service.register("a@example.com", mail.last_code("a@example.com"), "pw-123456")
    user = repo.get_user_by_email("a@example.com")
    assert codec.verify_access(tokens.access_token) == user.id


def test_register_consumes_the_otp(ctx):
    service, repo, mail, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    service.register("a@example.com", mail.last_code("a@example.com"), "pw-123456")
    assert repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP) is None


def test_register_rejects_a_wrong_code(ctx):
    service, _, _, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    with pytest.raises(OtpMismatch):
        service.register("a@example.com", "000000", "pw-123456")


def test_email_is_normalised(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("A@Example.com ", OtpPurpose.SIGNUP)
    service.register("a@example.com", mail.last_code("a@example.com"), "pw-123456")
    tokens = service.authenticate("  A@EXAMPLE.COM", "pw-123456")
    assert tokens.access_token


def test_authenticate_success_and_failures(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    service.register("a@example.com", mail.last_code("a@example.com"), "pw-123456")
    assert service.authenticate("a@example.com", "pw-123456").access_token
    with pytest.raises(InvalidCredentials):
        service.authenticate("a@example.com", "wrong")
    with pytest.raises(InvalidCredentials):
        service.authenticate("nobody@example.com", "pw-123456")


# --- refresh / logout --------------------------------------------------
def test_refresh_rotates_and_old_token_dies(ctx):
    service, _, mail, _, codec = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    first = service.register("a@example.com", mail.last_code("a@example.com"), "pw-123456")
    second = service.refresh(first.refresh_token)
    assert second.refresh_token != first.refresh_token
    assert codec.verify_access(second.access_token)
    # Reusing the rotated-away token is theft: it fails and burns the family.
    with pytest.raises(RefreshReused):
        service.refresh(first.refresh_token)
    with pytest.raises((RefreshReused, RefreshInvalid)):
        service.refresh(second.refresh_token)


def test_unknown_refresh_token_is_invalid(ctx):
    service, _, _, _, _ = ctx
    with pytest.raises(RefreshInvalid):
        service.refresh("never-issued")


def test_logout_kills_the_refresh_token(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    tokens = service.register("a@example.com", mail.last_code("a@example.com"), "pw-123456")
    service.revoke(tokens.refresh_token)
    with pytest.raises((RefreshReused, RefreshInvalid)):
        service.refresh(tokens.refresh_token)


# --- reset -------------------------------------------------------------
def test_reset_password_lets_the_new_password_sign_in(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("a@example.com", OtpPurpose.SIGNUP)
    service.register("a@example.com", mail.last_code("a@example.com"), "old-password")
    service.send_otp("a@example.com", OtpPurpose.RESET)
    service.reset_password("a@example.com", mail.last_code("a@example.com"), "new-password")
    assert service.authenticate("a@example.com", "new-password").access_token
    with pytest.raises(InvalidCredentials):
        service.authenticate("a@example.com", "old-password")


def test_reset_for_unknown_email_sends_nothing(ctx):
    service, _, mail, _, _ = ctx
    service.send_otp("ghost@example.com", OtpPurpose.RESET)
    assert mail.last_code("ghost@example.com") is None
