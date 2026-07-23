"""Push notifications: Urgent only.

The restraint is the feature. A product that pushes everything is the thing the
user already has and wants to escape, so the tests here are mostly about what
must stay silent. If this filter loosens, the product's whole claim goes with it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.models.feed import FeedItem, UserPreferences
from backend.models.tiers import Tier, TypeTag
from backend.services.notifications import (
    DefaultNotificationService,
    NotifyLevel,
    build_message,
)

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


class FakePush:
    def __init__(self, fail: bool = False):
        self.sent: list[dict] = []
        self.fail = fail

    def send(self, messages: list[dict]) -> None:
        if self.fail:
            raise RuntimeError("expo is down")
        self.sent.extend(messages)


def make_item(tier=Tier.URGENT, **overrides) -> FeedItem:
    defaults = dict(
        id="i1",
        user_id="me",
        source="slack",
        source_ref="slack:D1:1.1",
        rule_tier=tier,
        type_tag=TypeTag.REPLY,
        title="can you unblock the staging deploy?",
        summary="Priya is blocked on the deploy",
        url="https://slack.com/x",
        sender_name="Priya",
        occurred_at=NOW,
        created_at=NOW,
    )
    defaults.update(overrides)
    return FeedItem(**defaults)


def build(level=NotifyLevel.URGENT, fail=False):
    push = FakePush(fail=fail)
    service = DefaultNotificationService(push=push, clock=lambda: NOW)
    prefs = UserPreferences(user_id="me")
    return service, push, prefs, level


# --- what pushes -----------------------------------------------------------


def test_an_urgent_item_pushes():
    service, push, prefs, level = build()
    service.notify("token-1", [make_item()], prefs, level)
    assert len(push.sent) == 1


@pytest.mark.parametrize("tier", [Tier.TODAY, Tier.CAN_WAIT, Tier.NOISE])
def test_nothing_below_urgent_pushes_at_the_default_level(tier):
    service, push, prefs, level = build()
    service.notify("token-1", [make_item(tier=tier)], prefs, level)
    assert push.sent == []


def test_the_wider_level_also_pushes_today():
    service, push, prefs, _ = build()
    service.notify(
        "token-1", [make_item(tier=Tier.TODAY)], prefs, NotifyLevel.URGENT_TODAY
    )
    assert len(push.sent) == 1


def test_off_pushes_nothing_at_all():
    service, push, prefs, _ = build()
    service.notify("token-1", [make_item()], prefs, NotifyLevel.OFF)
    assert push.sent == []


def test_a_snoozed_item_does_not_push():
    """Snoozing says "not now". Pushing anyway is the app arguing with the
    user about their own decision."""
    service, push, prefs, level = build()
    item = make_item(snoozed_until=NOW + timedelta(hours=2))
    service.notify("token-1", [item], prefs, level)
    assert push.sent == []


def test_an_item_from_a_muted_source_does_not_push():
    service, push, _, level = build()
    prefs = UserPreferences(user_id="me", muted_channels={"#noisy"})
    service.notify(
        "token-1", [make_item(context_chip="#noisy")], prefs, level
    )
    assert push.sent == []


def test_an_already_handled_item_does_not_push():
    service, push, prefs, level = build()
    service.notify("token-1", [make_item(handled_at=NOW)], prefs, level)
    assert push.sent == []


# --- not pushing twice -----------------------------------------------------


def test_the_same_item_pushes_only_once_ever():
    """Every refresh re-reads the same urgent items. Without this the user gets
    the same alert every few minutes, which trains them to turn it off."""
    service, push, prefs, level = build()
    item = make_item()
    service.notify("token-1", [item], prefs, level)
    service.notify("token-1", [item], prefs, level)
    assert len(push.sent) == 1


def test_a_batch_of_urgent_items_becomes_one_notification():
    """Five separate buzzes for five items is the dump this product exists to
    replace."""
    service, push, prefs, level = build()
    items = [make_item(id=f"i{n}", source_ref=f"slack:D1:{n}") for n in range(5)]
    service.notify("token-1", items, prefs, level)

    assert len(push.sent) == 1
    assert "5" in push.sent[0]["title"]


def test_no_token_means_no_send_and_no_error():
    service, push, prefs, level = build()
    service.notify(None, [make_item()], prefs, level)
    assert push.sent == []


def test_a_push_failure_never_reaches_the_caller():
    """A dead notification service must not break a feed refresh."""
    service, _, prefs, level = build(fail=True)
    service.notify("token-1", [make_item()], prefs, level)  # must not raise


# --- message shape ---------------------------------------------------------


def test_a_single_message_names_the_person_and_the_ask():
    message = build_message("token-1", [make_item()])
    assert message["title"] == "Priya needs you"
    assert message["body"] == "Priya is blocked on the deploy"
    assert message["data"]["item_id"] == "i1"


def test_a_message_falls_back_to_the_title_when_there_is_no_summary():
    """Classification is asynchronous, so an urgent item can push before the
    model has said anything about it."""
    message = build_message("token-1", [make_item(summary=None)])
    assert message["body"] == "can you unblock the staging deploy?"
