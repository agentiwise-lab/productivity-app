import itertools
from datetime import datetime, timezone

import pytest

from backend.models.feed import FeedStatus, UserPreferences
from backend.models.tiers import Tier, TypeTag
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.feed import DefaultFeedService, ItemNotFound
from backend.services.rules import DefaultRuleClassifier
from tests.fakes import FakeGitHubService, make_event

prefs = UserPreferences(user_id="me")
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def build(github: FakeGitHubService | None = None) -> DefaultFeedService:
    counter = itertools.count(1)
    return DefaultFeedService(
        repo=InMemoryFeedRepository(),
        rules=DefaultRuleClassifier(),
        github=github or FakeGitHubService(),
        id_factory=lambda: f"id{next(counter)}",
        clock=lambda: NOW,
    )


def test_ingest_classifies_and_stores():
    svc = build()
    stored = svc.ingest("me", make_event(reason="review_requested"), prefs)
    assert stored.rule_tier is Tier.URGENT
    assert stored.type_tag is TypeTag.REVIEW
    assert [row.id for row in svc.list_feed("me", prefs)] == [stored.id]


def test_ingest_stores_no_tier_of_its_own():
    """The tier the user sees belongs to read time. If ingest froze one, an
    item would keep claiming yesterday's urgency."""
    svc = build()
    stored = svc.ingest("me", make_event(reason="review_requested"), prefs)
    assert not hasattr(stored, "tier")
    assert stored.llm_tier is None  # classification has not run yet


def test_list_feed_is_ranked_by_score():
    """Tier dominates the score: an approval outranks a comment however long
    the comment has been waiting."""
    svc = build()
    svc.ingest("me", make_event(source_ref="octo/repo#1", reason="comment"), prefs)
    svc.ingest(
        "me", make_event(source_ref="octo/repo#2", reason="approval_requested"), prefs
    )
    feed = svc.list_feed("me", prefs)
    assert [row.type_tag for row in feed] == [TypeTag.APPROVE, TypeTag.COMMENT]
    assert [row.tier for row in feed] == [Tier.URGENT, Tier.CAN_WAIT]


def test_ingest_dedupes_by_source_ref():
    svc = build()
    first = svc.ingest(
        "me", make_event(source_ref="octo/repo#1", reason="mention"), prefs
    )
    svc.ingest(
        "me", make_event(source_ref="octo/repo#1", reason="review_requested"), prefs
    )
    feed = svc.list_feed("me", prefs)
    assert len(feed) == 1
    assert feed[0].id == first.id  # same row, identity preserved
    assert feed[0].type_tag is TypeTag.REVIEW  # content updated


def test_feed_is_isolated_between_users():
    svc = build()
    svc.ingest("me", make_event(source_ref="octo/repo#1"), prefs)
    svc.ingest(
        "other", make_event(source_ref="octo/repo#1"), UserPreferences(user_id="other")
    )
    assert len(svc.list_feed("me", prefs)) == 1
    assert svc.list_feed("me", prefs)[0].user_id == "me"


def test_comment_calls_github_and_marks_acted():
    github = FakeGitHubService()
    svc = build(github=github)
    item = svc.ingest(
        "me", make_event(source_ref="octo/repo#7", reason="review_requested"), prefs
    )
    updated = svc.comment("me", item.id, "LGTM")
    assert updated.status == FeedStatus.ACTED
    assert updated.handled_at == NOW  # age_pressure needs this; status cannot give it
    ref, body = github.comments[0]
    assert (ref.repo, ref.number, body) == ("octo/repo", 7, "LGTM")


def test_comment_on_missing_item_raises():
    svc = build()
    with pytest.raises(ItemNotFound):
        svc.comment("me", "does-not-exist", "hi")


# --- what reaches Later --------------------------------------------------


def _noise_event(reason="gmail_bulk", **over):
    from backend.models.events import RawEvent

    payload = dict(
        source="gmail",
        source_ref="gmail:promo-1",
        reason=reason,
        subject_type="Message",
        title="50% off everything",
        url="",
        repo="",
    )
    payload.update(over)
    return RawEvent(**payload)


def test_a_newsletter_is_not_stored_because_no_screen_reads_it_from_here():
    """It is still visible: Later streams it live from Gmail. Storing it as
    well meant a month of newsletters in the database backing a list that is
    fetched fresh on every open."""
    svc = build()
    assert svc.ingest("me", _noise_event(), prefs) is None
    assert svc.list_feed("me", prefs) == []


def test_a_backlog_issue_can_wait_rather_than_being_noise():
    """It is the user's own task. Filing it as noise put their backlog in the
    same bucket as promotional email."""
    svc = build()
    stored = svc.ingest(
        "me",
        _noise_event(
            source="linear", source_ref="linear:AGE-21", reason="linear_backlog",
        ),
        prefs,
    )
    assert stored.rule_tier is Tier.CAN_WAIT
    assert stored.type_tag is TypeTag.ASSIGNED


def test_something_the_rules_defer_is_stored_because_the_tier_is_not_settled():
    """A plain email floors at today and needs the model. Discarding it on the
    rule tier would throw mail away before anything had judged it."""
    svc = build()
    stored = svc.ingest("me", _noise_event(reason="gmail_message"), prefs)
    assert stored is not None
    assert len(svc.list_feed("me", prefs)) == 1
