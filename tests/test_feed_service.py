import itertools

import pytest

from backend.models.feed import ActionType, FeedStatus, UserPreferences
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.classification import DefaultClassificationService
from backend.services.feed import DefaultFeedService, ItemNotFound
from backend.services.priority import DefaultPriorityService
from tests.fakes import FakeGitHubService, make_event

prefs = UserPreferences(user_id="me")


def build(github: FakeGitHubService | None = None) -> DefaultFeedService:
    counter = itertools.count(1)
    return DefaultFeedService(
        repo=InMemoryFeedRepository(),
        classifier=DefaultClassificationService(),
        prioritizer=DefaultPriorityService(),
        github=github or FakeGitHubService(),
        id_factory=lambda: f"id{next(counter)}",
    )


def test_ingest_classifies_scores_and_stores():
    svc = build()
    stored = svc.ingest("me", make_event(reason="review_requested"), prefs)
    assert stored.action_type == ActionType.REVIEW
    assert stored.priority_score > 0
    assert svc.list_feed("me") == [stored]


def test_list_feed_sorted_by_priority():
    svc = build()
    svc.ingest("me", make_event(source_ref="octo/repo#1", reason="subscribed"), prefs)
    svc.ingest(
        "me", make_event(source_ref="octo/repo#2", reason="approval_requested"), prefs
    )
    feed = svc.list_feed("me")
    assert [i.action_type for i in feed] == [ActionType.APPROVE, ActionType.FYI]


def test_ingest_dedupes_by_source_ref():
    svc = build()
    first = svc.ingest("me", make_event(source_ref="octo/repo#1", reason="mention"), prefs)
    svc.ingest("me", make_event(source_ref="octo/repo#1", reason="review_requested"), prefs)
    feed = svc.list_feed("me")
    assert len(feed) == 1
    assert feed[0].id == first.id  # same row, identity preserved
    assert feed[0].action_type == ActionType.REVIEW  # content updated


def test_feed_is_isolated_between_users():
    svc = build()
    svc.ingest("me", make_event(source_ref="octo/repo#1"), prefs)
    svc.ingest(
        "other", make_event(source_ref="octo/repo#1"), UserPreferences(user_id="other")
    )
    assert len(svc.list_feed("me")) == 1
    assert len(svc.list_feed("other")) == 1
    assert svc.list_feed("me")[0].user_id == "me"


def test_comment_calls_github_and_marks_acted():
    github = FakeGitHubService()
    svc = build(github=github)
    item = svc.ingest(
        "me", make_event(source_ref="octo/repo#7", reason="review_requested"), prefs
    )
    updated = svc.comment("me", item.id, "LGTM")
    assert updated.status == FeedStatus.ACTED
    assert len(github.comments) == 1
    ref, body = github.comments[0]
    assert (ref.repo, ref.number, body) == ("octo/repo", 7, "LGTM")


def test_comment_on_missing_item_raises():
    svc = build()
    with pytest.raises(ItemNotFound):
        svc.comment("me", "does-not-exist", "hi")
