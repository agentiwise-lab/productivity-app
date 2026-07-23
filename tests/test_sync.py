"""Fetch on open across sources.

The behaviour under test is almost entirely about failure. One broken
integration must degrade to itself: an expired Google token that emptied the
whole feed would be indistinguishable from a quiet morning.
"""

from __future__ import annotations

from backend.models.feed import UserPreferences
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.sync import SourceSync
from tests.fakes import FakeGitHubService, build_feed_service, make_event

PREFS = UserPreferences(user_id="me")


class FakeSource:
    def __init__(self, events=None, error: Exception | None = None):
        self._events = events or []
        self._error = error

    def _fetch(self):
        if self._error:
            raise self._error
        return list(self._events)

    list_notifications = _fetch
    assigned_to_me = _fetch
    unread = _fetch
    pending = _fetch


class FakeClassifier:
    def __init__(self, error=None):
        self.calls = 0
        self._error = error

    def classify_pending(self, user_id):
        self.calls += 1
        if self._error:
            raise self._error
        return type("R", (), {"classified": 3})()


def build(**sources):
    repo = InMemoryFeedRepository()
    sync = SourceSync(feed=build_feed_service(repo=repo, github=FakeGitHubService()), **sources)
    return sync, repo


def linear_event(ref="linear:AGE-1"):
    return make_event(source="linear", source_ref=ref, reason="linear_high")


def gmail_event(ref="gmail:m1"):
    return make_event(source="gmail", source_ref=ref, reason="gmail_message")


def test_every_configured_source_is_polled():
    sync, repo = build(
        github=FakeSource([make_event(source_ref="octo/repo#1")]),
        linear=FakeSource([linear_event()]),
        gmail=FakeSource([gmail_event()]),
    )
    report = sync.refresh("me", PREFS)

    assert report.ingested == 3
    assert set(report.per_source) == {"github", "linear", "gmail"}
    assert len(repo.list_by_user("me")) == 3


def test_one_broken_source_does_not_empty_the_feed():
    sync, repo = build(
        github=FakeSource([make_event(source_ref="octo/repo#1")]),
        calendar=FakeSource(error=RuntimeError("token expired")),
    )
    report = sync.refresh("me", PREFS)

    assert report.ingested == 1
    assert "calendar" in report.failed
    assert len(repo.list_by_user("me")) == 1


def test_the_failure_is_named_so_the_app_can_say_which_source_broke():
    sync, _ = build(gmail=FakeSource(error=RuntimeError("token expired")))
    assert "token expired" in sync.refresh("me", PREFS).failed["gmail"]


def test_one_bad_row_does_not_abandon_the_rest_of_its_batch():
    class Broken:
        source_ref = "linear:bad"

    sync, repo = build(linear=FakeSource([linear_event(), Broken(), linear_event("linear:AGE-2")]))
    report = sync.refresh("me", PREFS)

    assert report.ingested == 2
    assert len(repo.list_by_user("me")) == 2


def test_classification_runs_once_after_everything_is_ingested():
    """Once per refresh, not once per source: the batch is the unit of cost."""
    classifier = FakeClassifier()
    sync, _ = build(
        github=FakeSource([make_event(source_ref="octo/repo#1")]),
        linear=FakeSource([linear_event()]),
        classifier=classifier,
    )
    report = sync.refresh("me", PREFS)

    assert classifier.calls == 1
    assert report.classified == 3


def test_a_dead_model_still_returns_the_items():
    sync, repo = build(
        github=FakeSource([make_event(source_ref="octo/repo#1")]),
        classifier=FakeClassifier(error=RuntimeError("openrouter down")),
    )
    report = sync.refresh("me", PREFS)

    assert report.ingested == 1
    assert report.classified == 0
    assert len(repo.list_by_user("me")) == 1


def test_refreshing_twice_does_not_duplicate():
    sync, repo = build(linear=FakeSource([linear_event()]))
    sync.refresh("me", PREFS)
    sync.refresh("me", PREFS)
    assert len(repo.list_by_user("me")) == 1
