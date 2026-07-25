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
        self.change_requests: list[tuple[str, int, str]] = []
        self.assignments: list[tuple[str, int]] = []

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

    def request_changes_on_pull_request(self, ref: PRRef, body: str) -> None:
        self.change_requests.append((ref.repo, ref.number, body))

    def assign_to_me(self, ref: PRRef) -> None:
        self.assignments.append((ref.repo, ref.number))


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


class FakeIntegrations:
    """The Integrations factory, backed by fixed fakes. Returns the same fake
    for every user_id, which is all a single-user test needs; the point under
    test elsewhere is that production hands each user their own."""

    def __init__(self, github=None, slack=None, linear=None, gmail=None, calendar=None):
        self._m = {
            "github": github,
            "slack": slack,
            "linear": linear,
            "gmail": gmail,
            "calendar": calendar,
        }

    def github(self, user_id):
        return self._m["github"]

    def slack(self, user_id):
        return self._m["slack"]

    def linear(self, user_id):
        return self._m["linear"]

    def gmail(self, user_id):
        return self._m["gmail"]

    def calendar(self, user_id):
        return self._m["calendar"]


def build_feed_service(repo=None, github=None) -> DefaultFeedService:
    """The real feed service with fake edges. Used wherever a test needs a
    working spine but is not testing the spine itself."""
    return DefaultFeedService(
        repo=repo or InMemoryFeedRepository(),
        rules=DefaultRuleClassifier(),
        integrations=FakeIntegrations(github=github or FakeGitHubService()),
    )


def make_event(**overrides) -> RawEvent:
    defaults = dict(
        source="github",
        source_ref="octo/repo#1",
        reason="review_requested",
        subject_type="PullRequest",
        title="Add feature",
        url="https://github.com/octo/repo/pull/1",
        repo="octo/repo",
    )
    defaults.update(overrides)
    return RawEvent(**defaults)


class FakeLinearService:
    """Records comments. ``fail`` makes the next call raise, which is how the
    tests exercise "the upstream said no"."""

    def __init__(self) -> None:
        self.comments: list[tuple[str, str]] = []
        self.fail = False

    def comment(self, source_ref: str, body: str) -> None:
        if self.fail:
            raise RuntimeError("linear said no")
        self.comments.append((source_ref, body))


class FakeGmailService:
    """Records replies and read-marks. ``fail`` makes the next call raise, the
    way the other fakes model an upstream saying no."""

    def __init__(self) -> None:
        self.replies: list[tuple[str, str]] = []
        self.read: list[str] = []
        self.fail = False

    def reply(self, source_ref: str, body: str) -> None:
        if self.fail:
            raise RuntimeError("gmail said no")
        self.replies.append((source_ref, body))

    def mark_read(self, source_ref: str) -> None:
        if self.fail:
            raise RuntimeError("gmail said no")
        self.read.append(source_ref)


class FakeCalendarService:
    """Records RSVPs as (event, accepted) so a test can tell an accept from a
    decline rather than merely observing that something was sent."""

    def __init__(self) -> None:
        self.responses: list[tuple[str, bool]] = []
        self.fail = False

    def respond(self, source_ref: str, accepted: bool) -> None:
        if self.fail:
            raise RuntimeError("calendar said no")
        self.responses.append((source_ref, accepted))
