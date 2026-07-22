"""Normalized inbound signal.

GitHub delivers "something happened" two ways (the Notifications poll and
webhooks). Both are normalized into a ``RawEvent`` before classification, so no
downstream code needs to know which channel it came from. RawEvents are thin by
design: GitHub notifications carry a coarse ``reason`` plus a subject reference,
not content. Enrichment fills in the rest before an event becomes a FeedItem.
"""

from __future__ import annotations

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
    actor: Actor | None = None
    # Refinements pulled during enrichment that can override the coarse reason.
    review_state: str | None = None  # "changes_requested" | "approved" | ...
    check_conclusion: str | None = None  # "failure" | "success" | ...
    is_blocking: bool = False
    raw: dict = Field(default_factory=dict)
