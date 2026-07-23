"""Normalized inbound signal.

GitHub delivers "something happened" two ways (the Notifications poll and
webhooks). Both are normalized into a ``RawEvent`` before classification, so no
downstream code needs to know which channel it came from. RawEvents are thin by
design: GitHub notifications carry a coarse ``reason`` plus a subject reference,
not content. Enrichment fills in the rest before an event becomes a FeedItem.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.models.feed import Actor


class RawEvent(BaseModel):
    source: str = "github"
    # Stable id for the underlying subject, e.g. "owner/repo#42".
    source_ref: str
    # GitHub notification `reason` (e.g. "review_requested", "mention").
    reason: str
    subject_type: str  # "PullRequest" | "Issue" | "Discussion" | ...
    title: str
    url: str
    repo: str
    actor: Actor | None = None  # who triggered the event
    # Refinements pulled during enrichment that can override the coarse reason.
    review_state: str | None = None  # "changes_requested" | "approved" | ...
    check_conclusion: str | None = None  # "failure" | "success" | ...
    # Who owns the subject. Distinct from `actor`: the CI-failure rule is scoped
    # to the user's *own* PR, which the coarse notification reason cannot tell us.
    subject_author: str | None = None
    # Enrichment can reveal that a PR is both review-requested and approval-
    # gated, while the notification carries only one coarse reason. The
    # precedence ladder needs both facts to pick a single winning tag.
    review_requested: bool = False
    approval_requested: bool = False
    labels: list[str] = Field(default_factory=list)
    milestone_due: datetime | None = None
    deadline: datetime | None = None
    # Free text the LLM reads. Never used by rules.
    body: str | None = None
    # The chip on the card: "#eng-releases", "DM", a repo name.
    context_chip: str | None = None
    # The source's own timestamp, not our ingest time. Ranking uses this.
    occurred_at: datetime | None = None
    is_blocking: bool = False
    raw: dict = Field(default_factory=dict)
