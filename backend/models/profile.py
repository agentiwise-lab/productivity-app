"""The user's public-facing profile: what the You tab shows and the greeting
reads. Deliberately tiny and separate from the auth records, which carry secrets
this must never expose."""

from __future__ import annotations

from pydantic import BaseModel

from backend.services.notifications import NotifyLevel


class Profile(BaseModel):
    email: str
    name: str | None = None
    #: What the You tab's "Notify me" control reads and writes. Sent on every
    #: GET /me so the app can render the control from the stored value rather
    #: than from a local default that resets on every launch.
    notify_level: NotifyLevel = NotifyLevel.URGENT
