"""Test doubles and builders. The GitHub fake satisfies the GitHubService
contract, so services under test never touch the network."""

from __future__ import annotations

from datetime import datetime

from backend.integrations.github import Comment, PRRef, PullRequest
from backend.integrations.slack_service import SlackMessageRef
from backend.models.events import RawEvent
from backend.models.feed import Actor
from backend.models.identity import Identity
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.feed import DefaultFeedService
from backend.services.rules import DefaultRuleClassifier


class FakeGitHubService:
    """Records comment calls so tests can assert the write-back happened."""

    def __init__(self, notifications: list[RawEvent] | None = None) -> None:
        self._notifications = notifications or []
        self.comments: list[tuple[PRRef, str]] = []
        self.approvals: list[tuple[str, int]] = []

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

    def approve_pull_request(self, ref: PRRef, body: str = "") -> None:
        self.approvals.append((ref.repo, ref.number))


class FakeSlackService:
    """Records sends and read-cursor moves. ``fail`` makes the next call raise,
    which is how the tests exercise "the upstream said no"."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str | None]] = []
        self.read: list[str] = []
        self.fail = False

    def reply(self, source_ref: str, text: str, thread_ts: str | None = None):
        if self.fail:
            raise RuntimeError("slack said no")
        channel = source_ref.split(":")[1]
        self.sent.append((channel, text, thread_ts))
        return SlackMessageRef(channel=channel, ts="1.1")

    def mark_read(self, source_ref: str) -> None:
        if self.fail:
            raise RuntimeError("slack said no")
        self.read.append(source_ref)

    def resolve_identity(self) -> Identity:
        return Identity(slack_user_id="U_ME")


class FakeConnectionRepository:
    """Records connection status changes so tests can assert an expired
    connection was surfaced rather than silently swallowed."""

    def __init__(self) -> None:
        self.statuses: dict[tuple[str, str], str] = {}
        self.identities: dict[tuple[str, str], Identity] = {}

    def mark_status(self, user_id: str, provider: str, status: str) -> None:
        self.statuses[(user_id, provider)] = status

    def identity_for(self, user_id: str, provider: str) -> Identity:
        return self.identities.get((user_id, provider), Identity())


def build_feed_service(repo=None, github=None) -> DefaultFeedService:
    """The real feed service with fake edges. Used wherever a test needs a
    working spine but is not testing the spine itself."""
    return DefaultFeedService(
        repo=repo or InMemoryFeedRepository(),
        rules=DefaultRuleClassifier(),
        github=github or FakeGitHubService(),
    )


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
