"""Credentials repository contract.

Written against the Protocol so the in-memory and (later) Supabase stores answer
to one specification. The isolation cases are the ones that matter most: a
refresh token belongs to exactly one user, and nothing about one user's OTP or
tokens may surface for another.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.models.auth import OtpPurpose
from backend.repositories.credentials_repository import InMemoryCredentialsRepository

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def repo():
    return InMemoryCredentialsRepository()


# --- users -------------------------------------------------------------
def test_create_then_get_user_by_email(repo):
    created = repo.create_user("a@example.com", "hash-1")
    found = repo.get_user_by_email("a@example.com")
    assert found is not None
    assert found.id == created.id
    assert found.password_hash == "hash-1"


def test_unknown_email_is_none(repo):
    assert repo.get_user_by_email("nobody@example.com") is None


def test_set_password_updates_the_user(repo):
    user = repo.create_user("a@example.com", "old")
    repo.set_password(user.id, "new")
    assert repo.get_user_by_email("a@example.com").password_hash == "new"


def test_get_user_by_id(repo):
    created = repo.create_user("a@example.com", "hash")
    found = repo.get_user_by_id(created.id)
    assert found is not None and found.email == "a@example.com"
    assert found.name is None


def test_get_user_by_id_unknown_is_none(repo):
    assert repo.get_user_by_id("00000000-0000-0000-0000-000000000000") is None


def test_set_name_updates_the_user(repo):
    user = repo.create_user("a@example.com", "hash")
    repo.set_name(user.id, "Vicky")
    assert repo.get_user_by_id(user.id).name == "Vicky"
    repo.set_name(user.id, None)
    assert repo.get_user_by_id(user.id).name is None


# --- otp ---------------------------------------------------------------
def test_upsert_then_get_active_otp(repo):
    repo.upsert_otp("a@example.com", OtpPurpose.SIGNUP, "codehash", NOW + timedelta(minutes=10), NOW)
    otp = repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP)
    assert otp is not None
    assert otp.code_hash == "codehash"
    assert otp.attempts == 0


def test_resend_replaces_the_active_challenge_and_resets_attempts(repo):
    repo.upsert_otp("a@example.com", OtpPurpose.SIGNUP, "first", NOW + timedelta(minutes=10), NOW)
    otp = repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP)
    repo.increment_otp_attempts(otp.id)
    repo.upsert_otp("a@example.com", OtpPurpose.SIGNUP, "second", NOW + timedelta(minutes=10), NOW + timedelta(minutes=1))
    refreshed = repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP)
    assert refreshed.code_hash == "second"
    assert refreshed.attempts == 0


def test_increment_returns_new_count(repo):
    repo.upsert_otp("a@example.com", OtpPurpose.SIGNUP, "c", NOW + timedelta(minutes=10), NOW)
    otp = repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP)
    assert repo.increment_otp_attempts(otp.id) == 1
    assert repo.increment_otp_attempts(otp.id) == 2


def test_consumed_otp_is_no_longer_active(repo):
    repo.upsert_otp("a@example.com", OtpPurpose.SIGNUP, "c", NOW + timedelta(minutes=10), NOW)
    otp = repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP)
    repo.consume_otp(otp.id, NOW)
    assert repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP) is None


def test_signup_and_reset_are_separate_challenges(repo):
    repo.upsert_otp("a@example.com", OtpPurpose.SIGNUP, "s", NOW + timedelta(minutes=10), NOW)
    repo.upsert_otp("a@example.com", OtpPurpose.RESET, "r", NOW + timedelta(minutes=10), NOW)
    assert repo.get_active_otp("a@example.com", OtpPurpose.SIGNUP).code_hash == "s"
    assert repo.get_active_otp("a@example.com", OtpPurpose.RESET).code_hash == "r"


# --- refresh tokens ----------------------------------------------------
def test_store_then_get_refresh(repo):
    user = repo.create_user("a@example.com", "h")
    repo.store_refresh(user.id, "tok-hash", NOW + timedelta(days=30))
    record = repo.get_refresh("tok-hash")
    assert record is not None
    assert record.user_id == user.id
    assert record.revoked_at is None


def test_revoke_refresh_marks_it(repo):
    user = repo.create_user("a@example.com", "h")
    token_id = repo.store_refresh(user.id, "tok-hash", NOW + timedelta(days=30))
    repo.revoke_refresh(token_id, NOW)
    assert repo.get_refresh("tok-hash").revoked_at == NOW


def test_revoke_all_kills_every_live_token_for_the_user(repo):
    user = repo.create_user("a@example.com", "h")
    repo.store_refresh(user.id, "t1", NOW + timedelta(days=30))
    repo.store_refresh(user.id, "t2", NOW + timedelta(days=30))
    repo.revoke_all_for_user(user.id, NOW)
    assert repo.get_refresh("t1").revoked_at == NOW
    assert repo.get_refresh("t2").revoked_at == NOW


def test_one_users_tokens_are_untouched_by_anothers_revoke_all(repo):
    a = repo.create_user("a@example.com", "h")
    b = repo.create_user("b@example.com", "h")
    repo.store_refresh(a.id, "a-tok", NOW + timedelta(days=30))
    repo.store_refresh(b.id, "b-tok", NOW + timedelta(days=30))
    repo.revoke_all_for_user(a.id, NOW)
    assert repo.get_refresh("a-tok").revoked_at == NOW
    assert repo.get_refresh("b-tok").revoked_at is None
