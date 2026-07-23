"""Core feed domain types.

A ``FeedItem`` is one thing that may need the user, across any integration.

Two fields do the heavy lifting and are deliberately kept apart. ``rule_tier``
is what the deterministic rules concluded at ingest; ``llm_tier`` is what the
model concluded later, or None while classification is pending. Neither is "the
tier": the tier the user sees is computed on every read from these plus the
current clock (``services.ranking``). Storing a single frozen tier was the bug
this shape exists to prevent.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from backend.models.tiers import Tier, TypeTag


class FeedStatus(str, Enum):
    UNREAD = "unread"
    ACTED = "acted"
    DISMISSED = "dismissed"
    SNOOZED = "snoozed"


class TierSource(str, Enum):
    RULE = "rule"
    LLM = "llm"


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

    # --- judgement, stored ---
    rule_tier: Tier
    llm_tier: Tier | None = None
    tier_source: TierSource = TierSource.RULE
    type_tag: TypeTag = TypeTag.FYI
    # Set by the rules when urgency lives in prose. The classification queue is
    # exactly the rows where this is true and llm_tier is still None.
    needs_llm: bool = False

    # --- card content (6.1: none of this is optional on the card) ---
    title: str
    summary: str | None = None  # the AI one-liner shown as subtext
    reason: str | None = None  # "why this is urgent", shown in the detail sheet
    url: str
    repo: str = ""
    context_chip: str | None = None  # "#eng-releases", "glued_landing", "DM"
    sender_name: str | None = None
    sender_handle: str | None = None
    actors: list[Actor] = Field(default_factory=list)

    # --- timing ---
    deadline: datetime | None = None
    occurred_at: datetime | None = None  # the source's timestamp, not ours
    created_at: datetime | None = None  # when we ingested
    snoozed_until: datetime | None = None
    handled_at: datetime | None = None

    # True when a named person is explicitly waiting on this user.
    is_blocking: bool = False
    status: FeedStatus = FeedStatus.UNREAD
    # Hash of the classified content. The LLM cache is keyed on this, not on
    # source_ref, because a thread's content changes under a stable reference.
    content_hash: str | None = None
    #: The full readable content: an email body, a Slack message, an issue
    #: description. The card shows a summary; the sheet shows this.
    body: str | None = None
    raw: dict = Field(default_factory=dict)

    def body_text(self) -> str:
        """What the model reads and the sheet renders."""
        return self.body or str(self.raw.get("text") or "") or self.title


class FeedRow(FeedItem):
    """A feed item as the client sees it: the stored row plus the two things
    that only exist at read time. Kept as a separate type so nothing can
    accidentally persist a computed tier back into the database."""

    tier: Tier
    priority_score: float


class UserPreferences(BaseModel):
    """Per-user customization that tunes ranking. Empty = sensible defaults."""

    user_id: str
    priority_repos: set[str] = Field(default_factory=set)
    vip_actors: set[str] = Field(default_factory=set)
    muted_repos: set[str] = Field(default_factory=set)
    muted_channels: set[str] = Field(default_factory=set)
