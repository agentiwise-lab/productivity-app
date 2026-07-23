"""Tests for the Composio-backed GitHub integration.

The payload fixture below is the real shape returned by
GITHUB_LIST_NOTIFICATIONS, captured from a live call.
"""

from datetime import datetime, timezone

from backend.integrations.composio_github import (
    GITHUB_TOOLKIT_VERSION,
    ComposioGitHubService,
    notification_to_raw_event,
)
from backend.integrations.github import PRRef

SAMPLE = {
    "id": "24512080855",
    "reason": "author",
    "unread": True,
    "updated_at": "2026-07-07T12:31:50Z",
    "repository": {"full_name": "dswh/glued_landing"},
    "subject": {
        "title": "Feature/gif showcase",
        "type": "PullRequest",
        "url": "https://api.github.com/repos/dswh/glued_landing/pulls/23",
        "latest_comment_url": (
            "https://api.github.com/repos/dswh/glued_landing/issues/comments/4903814569"
        ),
    },
}


class _FakeTools:
    def __init__(self, payload):
        self.payload = payload
        self.calls: list[tuple] = []

    def execute(self, slug, user_id=None, arguments=None, version=None):
        self.calls.append((slug, user_id, arguments, version))
        return self.payload


class _FakeComposio:
    def __init__(self, payload):
        self.tools = _FakeTools(payload)


# --- normalization ---------------------------------------------------------


def test_maps_core_fields():
    event = notification_to_raw_event(SAMPLE)
    assert event.source == "github"
    assert event.reason == "author"
    assert event.repo == "dswh/glued_landing"
    assert event.title == "Feature/gif showcase"
    assert event.subject_type == "PullRequest"


def test_source_ref_is_repo_and_number():
    assert notification_to_raw_event(SAMPLE).source_ref == "dswh/glued_landing#23"


def test_builds_browser_url_for_pull_request():
    # subject.url is an api.github.com URL; the feed needs a clickable one.
    assert (
        notification_to_raw_event(SAMPLE).url
        == "https://github.com/dswh/glued_landing/pull/23"
    )


def test_builds_browser_url_for_issue():
    notification = {
        **SAMPLE,
        "subject": {
            **SAMPLE["subject"],
            "type": "Issue",
            "url": "https://api.github.com/repos/dswh/glued_landing/issues/7",
        },
    }
    event = notification_to_raw_event(notification)
    assert event.source_ref == "dswh/glued_landing#7"
    assert event.url == "https://github.com/dswh/glued_landing/issues/7"


def test_subject_without_number_falls_back_to_thread_id():
    notification = {
        **SAMPLE,
        "subject": {"title": "v2 released", "type": "Release", "url": None},
    }
    event = notification_to_raw_event(notification)
    assert event.source_ref == "dswh/glued_landing@24512080855"
    assert event.url == "https://github.com/dswh/glued_landing"


def test_the_notification_keeps_githubs_own_timestamp():
    """Without this the mapper leaves occurred_at empty, ingest falls back to
    the clock, and every polled item claims to have happened just now: cards
    read "now" for three-day-old review requests, and age pressure ranks them
    as if they had only just arrived."""
    event = notification_to_raw_event(SAMPLE)
    assert event.occurred_at == datetime(2026, 7, 7, 12, 31, 50, tzinfo=timezone.utc)


def test_a_missing_or_unparseable_timestamp_is_not_fatal():
    assert notification_to_raw_event({**SAMPLE, "updated_at": None}).occurred_at is None
    assert notification_to_raw_event({**SAMPLE, "updated_at": "nonsense"}).occurred_at is None


def test_is_blocking_only_when_someone_waits_on_the_user():
    for reason in ("review_requested", "approval_requested", "assign"):
        assert notification_to_raw_event({**SAMPLE, "reason": reason}).is_blocking
    for reason in ("author", "subscribed", "state_change", "comment"):
        assert not notification_to_raw_event({**SAMPLE, "reason": reason}).is_blocking


# --- service ---------------------------------------------------------------


def test_list_notifications_maps_payload():
    client = _FakeComposio({"successful": True, "data": {"notifications": [SAMPLE]}})
    service = ComposioGitHubService(client, user_id="me")

    events = service.list_notifications()

    assert len(events) == 1
    assert events[0].source_ref == "dswh/glued_landing#23"
    slug, user_id, args, version = client.tools.calls[0]
    assert slug == "GITHUB_LIST_NOTIFICATIONS"
    assert user_id == "me"
    # `all` must NOT be sent without `since`: that combination returns 0 results.
    assert "all" not in args


def test_list_notifications_sends_all_with_since():
    client = _FakeComposio({"successful": True, "data": {"notifications": []}})
    service = ComposioGitHubService(client, user_id="me")

    service.list_notifications(since=datetime(2026, 1, 1, tzinfo=timezone.utc))

    _, _, args, _ = client.tools.calls[0]
    assert args["all"] is True
    assert args["since"] == "2026-01-01T00:00:00Z"


def test_every_call_pins_the_toolkit_version():
    """Composio refuses manual execution without one, and refuses "latest". An
    unpinned call fails at runtime, not at import, so it needs a test."""
    client = _FakeComposio({"successful": True, "data": {"notifications": []}})
    service = ComposioGitHubService(client, user_id="me")

    service.list_notifications()
    service.comment_on_pull_request(PRRef(repo="a/b", number=1), "hi")

    assert all(call[3] == GITHUB_TOOLKIT_VERSION for call in client.tools.calls)


def test_list_notifications_handles_empty_payload():
    client = _FakeComposio({"successful": True, "data": {}})
    assert ComposioGitHubService(client, user_id="me").list_notifications() == []


def test_comment_on_pull_request_uses_issue_number():
    # PR discussion comments go through GitHub's issue-comment surface.
    client = _FakeComposio(
        {"successful": True, "data": {"id": 55, "html_url": "https://github.com/c/55"}}
    )
    service = ComposioGitHubService(client, user_id="me")

    comment = service.comment_on_pull_request(
        PRRef(repo="dswh/glued_landing", number=23), "LGTM"
    )

    slug, _, args, _ = client.tools.calls[0]
    assert slug == "GITHUB_CREATE_AN_ISSUE_COMMENT"
    assert args == {
        "owner": "dswh",
        "repo": "glued_landing",
        "issue_number": 23,
        "body": "LGTM",
    }
    assert comment.body == "LGTM"
    assert comment.id == "55"
