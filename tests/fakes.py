"""Test doubles and builders. The GitHub fake satisfies the GitHubService
contract, so services under test never touch the network."""

from __future__ import annotations

from datetime import datetime

from backend.integrations.github import Comment, PRRef, PullRequest
from backend.models.events import RawEvent
from backend.models.feed import Actor


class FakeGitHubService:
    """Records comment calls so tests can assert the write-back happened."""

    def __init__(self, notifications: list[RawEvent] | None = None) -> None:
        self._notifications = notifications or []
        self.comments: list[tuple[PRRef, str]] = []

    def list_notifications(self, since: datetime | None = None) -> list[RawEvent]:
        return list(self._notifications)

    def get_pull_request(self, ref: PRRef) -> PullRequest:
        return PullRequest(
            ref=ref,
            title="PR",
            url=f"https://github.com/{ref.repo}/pull/{ref.number}",
            author=Actor(login="someone"),
        )

    def comment_on_pull_request(self, ref: PRRef, body: str) -> Comment:
        self.comments.append((ref, body))
        return Comment(id="c1", url="https://github.com/comment/1", body=body)


def make_event(**overrides) -> RawEvent:
    defaults = dict(
        source_ref="octo/repo#1",
        reason="review_requested",
        subject_type="PullRequest",
        title="Add feature",
        url="https://github.com/octo/repo/pull/1",
        repo="octo/repo",
    )
    defaults.update(overrides)
    return RawEvent(**defaults)
