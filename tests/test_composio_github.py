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


class _SlugTools:
    """Answers each Composio slug differently, so the enrichment path (which
    calls a second slug after the notifications list) can be tested."""

    def __init__(self, notification, issue_body="", comment_body=""):
        self._notification = notification
        self._issue_body = issue_body
        self._comment_body = comment_body
        self.calls: list[tuple] = []

    def execute(self, slug, user_id=None, arguments=None, version=None):
        self.calls.append((slug, arguments))
        if slug == "GITHUB_LIST_NOTIFICATIONS":
            return {"data": {"notifications": [self._notification]}}
        if slug == "GITHUB_GET_AN_ISSUE":
            return {"data": {"body": self._issue_body}}
        if slug == "GITHUB_GET_AN_ISSUE_COMMENT":
            return {"data": {"body": self._comment_body}}
        return {"data": {}}


class _SlugComposio:
    def __init__(self, tools):
        self.tools = tools


def _mention(latest_comment_url):
    return {
        "id": "1",
        "reason": "mention",
        "repository": {"full_name": "octo/repo"},
        "subject": {
            "title": "testing 4",
            "type": "Issue",
            "url": "https://api.github.com/repos/octo/repo/issues/4",
            "latest_comment_url": latest_comment_url,
        },
        "updated_at": "2026-07-26T11:00:00Z",
    }


def test_a_mention_in_the_issue_body_is_enriched_with_the_real_text():
    """The notifications API has no body, so the card showed a synthetic
    "you were mentioned" line. When the notification points back at the issue,
    the issue body is the sentence you were mentioned in."""
    tools = _SlugTools(
        _mention("https://api.github.com/repos/octo/repo/issues/4"),
        issue_body="@vicky see this issue properly",
    )
    events = ComposioGitHubService(_SlugComposio(tools), user_id="me").list_notifications()
    assert events[0].body == "@vicky see this issue properly"
    assert any(
        c[0] == "GITHUB_GET_AN_ISSUE" and c[1]["issue_number"] == 4 for c in tools.calls
    )


def test_a_reply_notification_is_enriched_from_the_comment():
    tools = _SlugTools(
        _mention("https://api.github.com/repos/octo/repo/issues/comments/99"),
        comment_body="left you a reply",
    )
    events = ComposioGitHubService(_SlugComposio(tools), user_id="me").list_notifications()
    assert events[0].body == "left you a reply"
    assert any(
        c[0] == "GITHUB_GET_AN_ISSUE_COMMENT" and c[1]["comment_id"] == 99
        for c in tools.calls
    )


def test_a_failed_enrichment_keeps_the_synthetic_body():
    """One bad fetch must not blank the card or fail the refresh."""

    class _Boom(_SlugTools):
        def execute(self, slug, user_id=None, arguments=None, version=None):
            if slug != "GITHUB_LIST_NOTIFICATIONS":
                raise RuntimeError("github said no")
            return super().execute(slug, user_id, arguments, version)

    tools = _Boom(_mention("https://api.github.com/repos/octo/repo/issues/4"))
    events = ComposioGitHubService(_SlugComposio(tools), user_id="me").list_notifications()
    assert events[0].body  # the synthetic description survives
    assert "mentioned" in events[0].body.lower()


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
