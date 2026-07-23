"""GitHub integration contract.

Only this Protocol is imported by callers (services, routes, tests). The real
implementation (a GitHub App client) and the test fake both satisfy it, so the
rest of the backend never depends on how GitHub is actually reached. This is the
seam the human owns; the implementation behind it is swappable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from backend.models.events import RawEvent
from backend.models.feed import Actor


class PRRef(BaseModel):
    repo: str  # "owner/name"
    number: int


class PullRequest(BaseModel):
    ref: PRRef
    title: str
    url: str
    author: Actor
    requested_reviewers: list[Actor] = []
    mergeable: bool | None = None
    updated_at: datetime | None = None


class Comment(BaseModel):
    id: str
    url: str
    body: str


class GitHubService(Protocol):
    """Read from and act on GitHub. Callers import this, never a concrete class."""

    def list_notifications(self, since: datetime | None = None) -> list[RawEvent]:
        """The user's notification inbox as normalized RawEvents (poll-based)."""
        ...

    def get_pull_request(self, ref: PRRef) -> PullRequest:
        """Enrich a PR reference with the details ranking needs."""
        ...

    def comment_on_pull_request(self, ref: PRRef, body: str) -> Comment:
        """Act from the feed: post a comment back to a PR."""
        ...

    def approve_pull_request(self, ref: PRRef, body: str = "") -> None:
        """Submit an approving review.

        Deliberately separate from commenting. A comment whose text says
        "approved" does not approve anything, so collapsing these two would
        leave the pull request blocked while telling the user it was unblocked.
        """
        ...
