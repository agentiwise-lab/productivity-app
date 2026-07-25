"""The user's public-facing profile: what the You tab shows and the greeting
reads. Deliberately tiny and separate from the auth records, which carry secrets
this must never expose."""

from __future__ import annotations

from pydantic import BaseModel


class Profile(BaseModel):
    email: str
    name: str | None = None
