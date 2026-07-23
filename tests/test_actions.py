"""Acting from the feed: Phase 3.

An action is the only thing in this product that other people can see. A reply
sent twice, or sent to the wrong place, is not recoverable by us, so the tests
here are mostly about what must not happen: no double sends, no cross-user
writes, and no local state change when the upstream call failed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.models.feed import FeedStatus, UserPreferences
from backend.models.tiers import Tier
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.actions import ActionFailed, DefaultActionService, UnknownAction
from backend.services.feed import DefaultFeedService, ItemNotFound
from backend.services.rules import DefaultRuleClassifier
from tests.fakes import FakeGitHubService, FakeSlackService, make_event

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)
PREFS = UserPreferences(user_id="me")


def build():
    repo = InMemoryFeedRepository()
    github = FakeGitHubService()
    slack = FakeSlackService()
    feed = DefaultFeedService(
        repo=repo, rules=DefaultRuleClassifier(), github=github, clock=lambda: NOW
    )
    actions = DefaultActionService(
        repo=repo, github=github, slack=slack, clock=lambda: NOW
    )
    return actions, feed, repo, github, slack


def slack_event(**overrides):
    defaults = dict(
        source="slack",
        source_ref="slack:D01ABC:1784812011.000100",
        reason="slack_dm",
        subject_type="Message",
        title="can you unblock the deploy?",
        url="https://app.slack.com/x",
        repo="",
    )
    defaults.update(overrides)
    return make_event(**defaults)


# --- replying --------------------------------------------------------------


def test_replying_to_slack_sends_the_message_and_closes_the_item():
    actions, feed, repo, _, slack = build()
    item = feed.ingest("me", slack_event(), PREFS)

    updated = actions.perform("me", item.id, "reply", body="on it")

    assert slack.sent == [("D01ABC", "on it", None)]
    assert updated.status is FeedStatus.ACTED
    assert updated.handled_at == NOW
    assert repo.list_by_user("me", now=NOW) == []


def test_replying_in_a_thread_keeps_the_reply_in_the_thread():
    actions, feed, _, _, slack = build()
    item = feed.ingest(
        "me", slack_event(raw={"thread_ts": "1784812000.000100"}), PREFS
    )

    actions.perform("me", item.id, "reply", body="looking")

    assert slack.sent[0][2] == "1784812000.000100"


def test_commenting_on_github_posts_the_comment():
    actions, feed, _, github, _ = build()
    item = feed.ingest("me", make_event(source_ref="octo/repo#7"), PREFS)

    actions.perform("me", item.id, "comment", body="LGTM")

    ref, body = github.comments[0]
    assert (ref.repo, ref.number, body) == ("octo/repo", 7, "LGTM")


def test_approving_a_pull_request_submits_an_approval_not_a_comment():
    """A comment saying "approved" does not approve anything. If this called
    the comment tool the PR would stay blocked and the user would believe they
    had unblocked it."""
    actions, feed, _, github, _ = build()
    item = feed.ingest(
        "me", make_event(source_ref="octo/repo#7", reason="review_requested"), PREFS
    )

    actions.perform("me", item.id, "approve")

    assert github.approvals == [("octo/repo", 7)]
    assert github.comments == []


def test_an_empty_reply_is_refused_before_it_is_sent():
    actions, feed, _, _, slack = build()
    item = feed.ingest("me", slack_event(), PREFS)

    with pytest.raises(ActionFailed):
        actions.perform("me", item.id, "reply", body="   ")

    assert slack.sent == []


# --- failure handling ------------------------------------------------------


def test_a_failed_send_leaves_the_item_in_the_feed():
    """If the upstream call failed, the user has not replied. Closing the item
    anyway would hide a message they still owe someone an answer to."""
    actions, feed, repo, _, slack = build()
    slack.fail = True
    item = feed.ingest("me", slack_event(), PREFS)

    with pytest.raises(ActionFailed):
        actions.perform("me", item.id, "reply", body="on it")

    assert repo.get("me", item.id).status is FeedStatus.UNREAD


def test_acting_twice_on_one_item_sends_once():
    """The app is optimistic and a flaky network invites a retry. A second
    send would post the same reply into the channel twice."""
    actions, feed, _, _, slack = build()
    item = feed.ingest("me", slack_event(), PREFS)

    actions.perform("me", item.id, "reply", body="on it")
    with pytest.raises(ActionFailed):
        actions.perform("me", item.id, "reply", body="on it")

    assert len(slack.sent) == 1


def test_acting_on_another_users_item_is_refused():
    actions, feed, _, _, slack = build()
    item = feed.ingest("me", slack_event(), PREFS)

    with pytest.raises(ItemNotFound):
        actions.perform("someone-else", item.id, "reply", body="hello")

    assert slack.sent == []


def test_an_unknown_action_raises_rather_than_doing_nothing_quietly():
    actions, feed, _, _, _ = build()
    item = feed.ingest("me", slack_event(), PREFS)

    with pytest.raises(UnknownAction):
        actions.perform("me", item.id, "teleport")


# --- snooze and dismiss ----------------------------------------------------


def test_snoozing_hides_the_item_until_the_time_passes():
    actions, feed, repo, _, _ = build()
    item = feed.ingest("me", slack_event(), PREFS)

    actions.snooze("me", item.id, until=NOW + timedelta(hours=3))

    stored = repo.get("me", item.id)
    assert stored.status is FeedStatus.SNOOZED
    assert stored.snoozed_until == NOW + timedelta(hours=3)


def test_a_snoozed_item_is_still_in_the_thirty_day_window():
    """Snooze is not dismissal. It has to come back, and Later must still show
    it in the meantime."""
    actions, feed, repo, _, _ = build()
    item = feed.ingest("me", slack_event(), PREFS)
    actions.snooze("me", item.id, until=NOW + timedelta(hours=3))

    assert [row.id for row in repo.list_by_user("me", now=NOW)] == [item.id]


def test_dismissing_marks_it_read_upstream_too():
    """Read state syncs both ways (3.11). Dismissing here but leaving it bold
    in Slack means doing the work twice."""
    actions, feed, _, _, slack = build()
    item = feed.ingest("me", slack_event(), PREFS)

    actions.perform("me", item.id, "mark_read")

    assert slack.read == ["slack:D01ABC:1784812011.000100"]
    assert item.id not in [row.id for row in feed.list_feed("me", PREFS)]
