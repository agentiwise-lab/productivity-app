"""Minting and reading our own access tokens.

The app owns identity end to end, so this is where a signed access token is
created and verified. It is deliberately pure: no I/O, no clock of its own (the
caller passes ``now``), so the whole thing is exercised in memory with no
credentials and no wall-clock flakiness.

The access token carries only ``sub`` (the user's uuid). Everything the API
needs is already keyed by that id, so putting email or roles in the token would
be duplicating state that can go stale. Refresh tokens are *not* JWTs: they are
opaque random strings stored only as a hash, so a database read never yields a
usable token.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
import secrets

import jwt


class TokenInvalid(Exception):
    """Raised for any unverifiable access token: bad signature, expired, or a
    wrong issuer/audience. The route turns this into a 401, and the reason is
    deliberately not distinguished to the caller."""


@dataclass(frozen=True)
class TokenCodec:
    secret: str
    issuer: str
    audience: str
    access_ttl: timedelta

    def sign_access(self, user_id: str, now: datetime) -> str:
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + self.access_ttl,
            "iss": self.issuer,
            "aud": self.audience,
        }
        return jwt.encode(payload, self.secret, algorithm="HS256")

    def verify_access(self, token: str) -> str:
        try:
            claims = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256"],
                audience=self.audience,
                issuer=self.issuer,
                # iat is informational, not a control: expiry is what bounds a
                # token's life. Verifying it only adds a clock-skew failure mode
                # where a token minted a second in the future is briefly invalid.
                options={"verify_iat": False},
            )
        except jwt.PyJWTError as error:
            raise TokenInvalid(str(error)) from error

        subject = claims.get("sub")
        if not subject:
            raise TokenInvalid("token has no subject")
        return subject


def new_refresh_token() -> str:
    """An opaque, high-entropy token. Never stored in the clear; see
    ``hash_token``."""
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    """What we store and look up by. A stolen database row therefore yields a
    hash, not a token that can be replayed."""
    return sha256(token.encode("utf-8")).hexdigest()
