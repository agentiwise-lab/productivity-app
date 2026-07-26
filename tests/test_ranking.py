"""Read-time tier and score: sections 3.8 and 3.9.

The whole point of these tests is that nothing here is frozen at ingest. Every
case fixes ``now`` explicitly and asserts what the same stored row says at a
different moment.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.models.feed import FeedItem, UserPreferences
from backend.models.tiers import Tier, TypeTag
from backend.services.ranking import effective_tier, score

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
PREFS = UserPreferences(user_id="u1")


def make_item(**overrides) -> FeedItem:
    defaults = dict(
        id="i1",
        user_id="u1",
        source="github",
        source_ref="octo/repo#1",
        type_tag=TypeTag.REVIEW,
        rule_tier=Tier.TODAY,
        title="Add feature",
        url="https://github.com/octo/repo/pull/1",
        occurred_at=NOW - timedelta(minutes=10),
    )
    defaults.update(overrides)
    return FeedItem(**defaults)


# --- 3.8 effective tier ----------------------------------------------------


def test_llm_tier_wins_over_the_rule_floor_once_it_lands():
    item = make_item(rule_tier=Tier.TODAY, llm_tier=Tier.CAN_WAIT)
    assert effective_tier(item, now=NOW) is Tier.CAN_WAIT


def test_the_band_floor_blocks_the_model_from_demoting_below_it():
    """The triage bug this whole part exists to kill: the model filed a review
    request as can_wait. The band floor for review_requested is Today, so the
    clamp lifts the model's rating back to the floor."""
    item = make_item(
        signal="review_requested", rule_tier=Tier.TODAY, llm_tier=Tier.CAN_WAIT
    )
    assert effective_tier(item, now=NOW) is Tier.TODAY


def test_the_band_lets_the_model_lift_within_it():
    """Same band, the other direction: the model may raise a review request to
    urgent, because the ceiling allows it."""
    item = make_item(
        signal="review_requested", rule_tier=Tier.TODAY, llm_tier=Tier.URGENT
    )
    assert effective_tier(item, now=NOW) is Tier.URGENT


def test_a_meeting_within_the_hour_is_urgent():
    item = make_item(
        source="calendar",
        signal="calendar_meeting",
        occurred_at=NOW + timedelta(minutes=30),
        deadline=NOW + timedelta(minutes=90),
    )
    assert effective_tier(item, now=NOW) is Tier.URGENT


def test_an_in_progress_meeting_is_still_urgent():
    item = make_item(
        source="calendar",
        signal="calendar_meeting",
        occurred_at=NOW - timedelta(minutes=10),
        deadline=NOW + timedelta(minutes=50),
    )
    assert effective_tier(item, now=NOW) is Tier.URGENT


def test_a_meeting_later_today_is_by_eod_not_urgent():
    """A passed-deadline promotion must never make a meeting on the day urgent
    hours ahead; only the last hour before it starts does."""
    item = make_item(
        source="calendar",
        signal="calendar_meeting",
        occurred_at=NOW + timedelta(hours=5),
        deadline=NOW + timedelta(hours=6),
    )
    assert effective_tier(item, now=NOW) is Tier.TODAY


def test_gmail_may_sink_to_later_because_its_floor_is_noise():
    """Gmail is the one source whose floor is noise: a newsletter-ish message
    the model rates as noise stays noise rather than being propped up."""
    item = make_item(
        source="gmail", signal="gmail_message", rule_tier=Tier.CAN_WAIT,
        llm_tier=Tier.NOISE,
    )
    assert effective_tier(item, now=NOW) is Tier.NOISE


def test_rule_tier_is_used_while_classification_is_still_pending():
    """The feed never blocks on the model (4.4), so an unclassified item must
    still render at its rule tier."""
    item = make_item(rule_tier=Tier.URGENT, llm_tier=None)
    assert effective_tier(item, now=NOW) is Tier.URGENT


def test_a_passed_deadline_promotes_to_urgent():
    """The bug this whole section exists to prevent: the same stored row reads
    Today before its deadline and Urgent after it."""
    item = make_item(rule_tier=Tier.TODAY, deadline=NOW + timedelta(hours=1))
    assert effective_tier(item, now=NOW) is Tier.TODAY
    assert effective_tier(item, now=NOW + timedelta(hours=2)) is Tier.URGENT


def test_a_deadline_within_three_hours_lifts_can_wait_to_today():
    item = make_item(
        rule_tier=Tier.CAN_WAIT,
        llm_tier=Tier.CAN_WAIT,
        deadline=NOW + timedelta(hours=2),
    )
    assert effective_tier(item, now=NOW) is Tier.TODAY


def test_a_deadline_within_three_hours_never_demotes_an_urgent_item():
    item = make_item(rule_tier=Tier.URGENT, deadline=NOW + timedelta(hours=2))
    assert effective_tier(item, now=NOW) is Tier.URGENT


def test_urgent_untouched_for_over_a_day_is_demoted():
    """If nobody chased it for 24 hours it was not urgent. Without this the
    urgent tier silts up and stops meaning anything."""
    item = make_item(rule_tier=Tier.URGENT, occurred_at=NOW - timedelta(hours=30))
    assert effective_tier(item, now=NOW) is Tier.TODAY


def test_an_overdue_item_is_not_demoted_by_age():
    """Age demotion must never fight a passed deadline."""
    item = make_item(
        rule_tier=Tier.URGENT,
        occurred_at=NOW - timedelta(hours=30),
        deadline=NOW - timedelta(hours=1),
    )
    assert effective_tier(item, now=NOW) is Tier.URGENT


def test_a_snoozed_item_reports_its_tier_but_scores_below_everything():
    item = make_item(rule_tier=Tier.URGENT, snoozed_until=NOW + timedelta(hours=3))
    assert score(item, PREFS, now=NOW) < 0


def test_snooze_expires():
    item = make_item(rule_tier=Tier.URGENT, snoozed_until=NOW - timedelta(minutes=1))
    assert score(item, PREFS, now=NOW) > 0


# --- 3.9 score -------------------------------------------------------------


def test_tier_dominates_the_score():
    """No stack of bonuses on a Today item may outrank a plain Urgent one."""
    urgent = make_item(rule_tier=Tier.URGENT)
    loaded_today = make_item(
        rule_tier=Tier.TODAY,
        is_blocking=True,
        sender_handle="priya",
        deadline=NOW + timedelta(hours=1),
        occurred_at=NOW - timedelta(days=5),
    )
    prefs = UserPreferences(user_id="u1", vip_actors={"priya"})
    assert score(urgent, PREFS, now=NOW) > score(loaded_today, prefs, now=NOW)


def test_blocking_outranks_non_blocking_in_the_same_tier():
    blocking = make_item(is_blocking=True)
    quiet = make_item(is_blocking=False)
    assert score(blocking, PREFS, now=NOW) > score(quiet, PREFS, now=NOW)


def test_a_vip_sender_outranks_a_stranger():
    prefs = UserPreferences(user_id="u1", vip_actors={"priya"})
    vip = make_item(sender_handle="priya")
    stranger = make_item(sender_handle="someone")
    assert score(vip, prefs, now=NOW) > score(stranger, prefs, now=NOW)


def test_age_pressure_is_capped():
    """Age must nudge, not dominate: an ancient Can wait item must never
    outrank a fresh Today one."""
    ancient = make_item(rule_tier=Tier.CAN_WAIT, occurred_at=NOW - timedelta(days=30))
    fresh = make_item(rule_tier=Tier.TODAY, occurred_at=NOW)
    assert score(fresh, PREFS, now=NOW) > score(ancient, PREFS, now=NOW)


@pytest.mark.parametrize(
    "hours_out,expected_order",
    [(-1, 3), (2, 2), (12, 1), (100, 0)],
)
def test_deadline_pressure_increases_as_the_deadline_approaches(
    hours_out, expected_order
):
    item = make_item(
        rule_tier=Tier.CAN_WAIT,
        llm_tier=Tier.CAN_WAIT,
        deadline=NOW + timedelta(hours=hours_out),
    )
    baseline = make_item(rule_tier=Tier.CAN_WAIT, llm_tier=Tier.CAN_WAIT)
    delta = score(item, PREFS, now=NOW) - score(baseline, PREFS, now=NOW)
    assert (delta > 0) == (expected_order > 0)


def test_a_muted_repo_scores_to_the_floor():
    prefs = UserPreferences(user_id="u1", muted_repos={"octo/repo"})
    item = make_item(rule_tier=Tier.URGENT, repo="octo/repo")
    assert score(item, prefs, now=NOW) < 0


def test_within_a_tier_the_platform_decides_the_order():
    """The simple first-cut within-tier rule: platform priority. A GitHub urgent
    sorts before a Slack urgent regardless of the Slack item being newer."""
    gh = make_item(source="github", rule_tier=Tier.URGENT, occurred_at=NOW - timedelta(hours=5))
    slack = make_item(source="slack", rule_tier=Tier.URGENT, occurred_at=NOW)
    assert score(gh, PREFS, now=NOW) > score(slack, PREFS, now=NOW)


def test_platform_order_never_crosses_a_tier():
    """Even the lowest-priority platform on a higher tier beats the highest-
    priority platform a tier below it."""
    gmail_today = make_item(source="gmail", rule_tier=Tier.TODAY)
    github_can_wait = make_item(source="github", rule_tier=Tier.CAN_WAIT, is_blocking=True)
    assert score(gmail_today, PREFS, now=NOW) > score(github_can_wait, PREFS, now=NOW)
