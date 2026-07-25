"""Access-token codec contract.

Tested through ``TokenCodec`` alone: sign, then verify, and the ways verify must
refuse. The refusals matter more than the happy path, because each one is a hole
that would let a forged or stale token authenticate as someone.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.tokens import (
    TokenCodec,
    TokenInvalid,
    hash_token,
    new_refresh_token,
)

NOW = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)


def make_codec(
    secret="test-secret-at-least-thirty-two-bytes-long!!",
    issuer="productivity-app",
    audience="app",
    ttl_min=15,
):
    return TokenCodec(
        secret=secret,
        issuer=issuer,
        audience=audience,
        access_ttl=timedelta(minutes=ttl_min),
    )


def test_sign_then_verify_returns_the_subject():
    codec = make_codec()
    token = codec.sign_access("user-123", NOW)
    assert codec.verify_access(token) == "user-123"


def test_expired_token_is_rejected():
    codec = make_codec()
    # Signed two days ago so the 15-minute token is unambiguously expired
    # regardless of the machine clock the verifier reads.
    token = codec.sign_access("user-123", NOW - timedelta(days=2))
    with pytest.raises(TokenInvalid):
        codec.verify_access(token)


def test_wrong_secret_is_rejected():
    token = make_codec(secret="secret-one-secret-one-secret-one-secret").sign_access(
        "user-123", NOW
    )
    with pytest.raises(TokenInvalid):
        make_codec(secret="secret-two-secret-two-secret-two-secret").verify_access(
            token
        )


def test_wrong_audience_is_rejected():
    token = make_codec(audience="app").sign_access("user-123", NOW)
    with pytest.raises(TokenInvalid):
        make_codec(audience="other").verify_access(token)


def test_wrong_issuer_is_rejected():
    token = make_codec(issuer="productivity-app").sign_access("user-123", NOW)
    with pytest.raises(TokenInvalid):
        make_codec(issuer="somewhere-else").verify_access(token)


def test_garbage_is_rejected():
    with pytest.raises(TokenInvalid):
        make_codec().verify_access("not-a-token")


def test_hash_token_is_deterministic_and_hex():
    digest = hash_token("abc")
    assert digest == hash_token("abc")
    assert len(digest) == 64
    assert digest != hash_token("abd")


def test_new_refresh_token_is_unique_and_opaque():
    a, b = new_refresh_token(), new_refresh_token()
    assert a != b
    assert len(a) >= 40
