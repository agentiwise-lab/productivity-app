import itertools
from datetime import datetime, timezone

import pytest

from backend.models.feed import FeedStatus, UserPreferences
from backend.models.tiers import Tier, TypeTag
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.feed import DefaultFeedService, ItemNotFound
from backend.services.rules import DefaultRuleClassifier
from tests.fakes import FakeGitHubService, FakeIntegrations, make_event

prefs = UserPreferences(user_id="me")
NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def build(github: FakeGitHubService | None = None) -> DefaultFeedService:
    counter = itertools.count(1)
    return DefaultFeedService(
        repo=InMemoryFeedRepository(),
        rules=DefaultRuleClassifier(),
        integrations=FakeIntegrations(github=github or FakeGitHubService()),
        id_factory=lambda: f"id{next(counter)}",
        clock=lambda: NOW,
    )


def _classify(svc: DefaultFeedService, item_id: str, tier: Tier = Tier.TODAY) -> None:
    """Land a model verdict so a held (needs_llm) item becomes visible. A banded
    item is held off the feed until the model rates it, which is the behaviour
    these list_feed tests then check."""
    svc._repo.apply_classification(
        "me", item_id, tier=tier, summary="s", reason="r", at=NOW
    )


def test_ingest_stores_and_holds_until_classified():
    svc = build()
    stored = svc.ingest("me", make_event(reason="review_requested"), prefs)
    assert stored.rule_tier is Tier.TODAY  # the floor; the model may lift it
    assert stored.type_tag is TypeTag.REVIEW
    assert stored.needs_llm is True
    # Held off the feed until the model lands a verdict, never as a placeholder.
    assert svc.list_feed("me", prefs) == []
    _classify(svc, stored.id, Tier.TODAY)
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
    comment = svc.ingest(
        "me", make_event(source_ref="octo/repo#1", reason="comment"), prefs
    )
    approval = svc.ingest(
        "me", make_event(source_ref="octo/repo#2", reason="approval_requested"), prefs
    )
    # Both are banded and held until judged; the model rates the approval Today
    # and the comment Can wait (both within their bands).
    _classify(svc, comment.id, Tier.CAN_WAIT)
    _classify(svc, approval.id, Tier.TODAY)
    feed = svc.list_feed("me", prefs)
    assert [row.type_tag for row in feed] == [TypeTag.APPROVE, TypeTag.COMMENT]
    # Tier dominates the order.
    assert [row.tier for row in feed] == [Tier.TODAY, Tier.CAN_WAIT]


def test_ingest_dedupes_by_source_ref():
    svc = build()
    first = svc.ingest(
        "me", make_event(source_ref="octo/repo#1", reason="mention"), prefs
    )
    svc.ingest(
        "me", make_event(source_ref="octo/repo#1", reason="review_requested"), prefs
    )
    _classify(svc, first.id, Tier.TODAY)
    feed = svc.list_feed("me", prefs)
    assert len(feed) == 1
    assert feed[0].id == first.id  # same row, identity preserved
    assert feed[0].type_tag is TypeTag.REVIEW  # content updated


def test_feed_is_isolated_between_users():
    svc = build()
    me_item = svc.ingest("me", make_event(source_ref="octo/repo#1"), prefs)
    svc.ingest(
        "other", make_event(source_ref="octo/repo#1"), UserPreferences(user_id="other")
    )
    _classify(svc, me_item.id)
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


def test_a_passed_meeting_is_dropped_from_the_feed():
    """A calendar item whose meeting has ended is gone from the feed at any tier.
    This also clears stale calendar rows left over from before a refresh."""
    svc = build()
    svc.ingest(
        "me",
        make_event(
            source="calendar",
            source_ref="calendar:1",
            reason="calendar_meeting",
            occurred_at=datetime(2026, 7, 23, 9, tzinfo=timezone.utc),
            deadline=datetime(2026, 7, 23, 10, tzinfo=timezone.utc),  # ended before NOW (12:00)
        ),
        prefs,
    )
    assert svc.list_feed("me", prefs) == []


def test_a_linear_issue_with_no_due_date_is_kept_and_shown_not_dropped():
    """A Linear task with no due date is deterministic (no model) and never
    dropped: read-time tiering settles it at can_wait, so it shows on the feed
    rather than being held or discarded like a newsletter."""
    svc = build()
    stored = svc.ingest(
        "me",
        _noise_event(source="linear", source_ref="linear:AGE-21", reason="linear"),
        prefs,
    )
    assert stored is not None  # kept, not dropped
    assert stored.needs_llm is False  # deterministic; never held
    assert stored.type_tag is TypeTag.ASSIGNED
    feed = svc.list_feed("me", prefs)
    assert [row.id for row in feed] == [stored.id]
    assert feed[0].tier is Tier.CAN_WAIT


def test_something_the_rules_defer_is_stored_but_held_until_judged():
    """A plain email needs the model. It is stored (throwing it away on the rule
    tier would lose mail before anything judged it) but held off the feed until
    the model lands a verdict, never shown as a placeholder."""
    svc = build()
    stored = svc.ingest("me", _noise_event(reason="gmail_message"), prefs)
    assert stored is not None
    assert stored.needs_llm is True
    assert svc.list_feed("me", prefs) == []  # held
    _classify(svc, stored.id, Tier.CAN_WAIT)
    assert len(svc.list_feed("me", prefs)) == 1
