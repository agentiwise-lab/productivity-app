"""Core feed domain types.

These are the stable data shapes the rest of the backend is built around. A
``FeedItem`` is one thing that may need the user across any integration; the
tracer only produces GitHub items, but the shape is source-agnostic.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """What the user is being asked to do. The whole feed reduces to these."""

    REVIEW = "review"
    APPROVE = "approve"
    REPLY = "reply"
    DECIDE = "decide"
    FYI = "fyi"


class FeedStatus(str, Enum):
    UNREAD = "unread"
    ACTED = "acted"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"


class Actor(BaseModel):
    login: str
    display_name: str | None = None


class FeedItem(BaseModel):
    """One item in a user's ranked feed. Isolated per ``user_id``."""

    id: str
    user_id: str
    source: str = "github"
    # Stable id for the underlying subject (e.g. "owner/repo#42"). Dedupe key
    # together with user_id: a notification and a webhook for the same subject
    # collapse to one item.
    source_ref: str
    action_type: ActionType
    title: str
    url: str
    repo: str
    actors: list[Actor] = Field(default_factory=list)
    deadline: datetime | None = None
    # True when someone else is waiting on this user to act (strong rank signal).
    is_blocking: bool = False
    priority_score: float = 0.0
    status: FeedStatus = FeedStatus.UNREAD
    created_at: datetime | None = None


class UserPreferences(BaseModel):
    """Per-user customization that tunes ranking. Empty = sensible defaults."""

    user_id: str
    priority_repos: set[str] = Field(default_factory=set)
    vip_actors: set[str] = Field(default_factory=set)
    muted_repos: set[str] = Field(default_factory=set)
