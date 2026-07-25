"""The records the auth flow reads and writes.

These are the shapes the credentials repository returns, so services and tests
speak in them rather than in raw dict rows. Kept minimal: a user, an OTP
challenge, a refresh token, and the pair of tokens a successful sign-in yields.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class OtpPurpose(str, Enum):
    SIGNUP = "signup"
    RESET = "reset"


class UserRecord(BaseModel):
    id: str
    email: str
    # Null between provisioning and the moment a password is set.
    password_hash: str | None = None
    # Optional display name, set after signup. Null until the user provides one.
    name: str | None = None
    created_at: datetime | None = None


class OtpRecord(BaseModel):
    id: str
    email: str
    purpose: OtpPurpose
    code_hash: str
    expires_at: datetime
    attempts: int = 0
    consumed_at: datetime | None = None
    last_sent_at: datetime


class RefreshRecord(BaseModel):
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    rotated_from: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
