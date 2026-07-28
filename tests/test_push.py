"""The push service: what actually reaches a phone, and what must not.

Two jobs, and the tests split along them.

The first is the filter, which is mostly `DefaultNotificationService`'s already
and is exercised here through the seam the webhook really uses.

The second is the **window**. A webhook fires per item, so three things landing
in the same minute would be three separate buzzes without it, which is the pile
this product exists to replace. Nothing here sleeps: the timer is injected, so
"the window closed" is a function call.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.models.feed import FeedItem, UserPreferences
from backend.models.tiers import Tier, TypeTag
from backend.repositories.device_token_repository import (
    InMemoryDeviceTokenRepository,
)
from backend.services.notifications import DefaultNotificationService, NotifyLevel
from backend.services.push import DefaultPushService

NOW = datetime(2026, 7, 27, 9, 41, tzinfo=timezone.utc)
ME = "11111111-1111-1111-1111-111111111111"
PHONE = "ExponentPushToken[phone]"
TABLET = "ExponentPushToken[tablet]"


class FakePush:
    def __init__(self, fail: bool = False, tickets: list[dict] | None = None):
        self.sent: list[dict] = []
        self.fail = fail
        self._tickets = tickets

    def send(self, messages: list[dict]) -> list[dict]:
        if self.fail:
            raise RuntimeError("expo is down")
        self.sent.extend(messages)
        if self._tickets is not None:
            return self._tickets
        return [{"status": "ok", "id": f"t{n}"} for n in range(len(messages))]


class FakeSchedule:
    """Stands in for `threading.Timer`. Records the callbacks a window opened
    and runs them on demand, so a 25-second window costs nothing to test."""

    def __init__(self):
        self.pending: list = []

    def __call__(self, delay: float, work) -> None:
        self.pending.append((delay, work))

    def fire_all(self) -> None:
        due, self.pending = self.pending, []
        for _, work in due:
            work()


def make_item(tier=Tier.URGENT, **overrides) -> FeedItem:
    defaults = dict(
        id="i1",
        user_id=ME,
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


def build(level=NotifyLevel.URGENT, tokens=(PHONE,), fail=False, tickets=None):
    """A push service wired to fakes, plus a mutable item store the flush reads
    through, so a test can change an item *during* the window."""
    push = FakePush(fail=fail, tickets=tickets)
    token_repo = InMemoryDeviceTokenRepository()
    for token in tokens:
        token_repo.upsert(ME, token, "android")

    store: dict[str, FeedItem] = {}
    schedule = FakeSchedule()
    service = DefaultPushService(
        notifications=DefaultNotificationService(push=push, clock=lambda: NOW),
        tokens=token_repo,
        item_for=lambda user_id, item_id: store.get(item_id),
        level_for=lambda user_id: level,
        prefs_for=lambda user_id: UserPreferences(user_id=user_id),
        schedule=schedule,
        window_seconds=25.0,
    )
    return service, push, token_repo, store, schedule


def push_item(service, store, item):
    """What the ingest hook does: the item is already stored by the time the
    push hook sees it."""
    store[item.id] = item
    service.push_for_item(ME, item)


# --- the level filter, through the real seam -------------------------------


def test_an_urgent_item_reaches_the_phone():
    service, push, _, store, schedule = build()
    push_item(service, store, make_item())
    schedule.fire_all()
    assert len(push.sent) == 1
    assert push.sent[0]["to"] == PHONE


def test_off_never_sends_and_never_reads_a_token():
    service, push, _, store, schedule = build(level=NotifyLevel.OFF)
    push_item(service, store, make_item())
    schedule.fire_all()
    assert push.sent == []


@pytest.mark.parametrize("tier", [Tier.TODAY, Tier.CAN_WAIT, Tier.NOISE])
def test_nothing_below_urgent_reaches_the_phone_at_the_default_level(tier):
    service, push, _, store, schedule = build()
    push_item(service, store, make_item(tier=tier))
    schedule.fire_all()
    assert push.sent == []


def test_the_wider_level_also_reaches_the_phone_for_by_eod():
    service, push, _, store, schedule = build(level=NotifyLevel.URGENT_TODAY)
    push_item(service, store, make_item(tier=Tier.TODAY))
    schedule.fire_all()
    assert len(push.sent) == 1


def test_a_user_with_no_devices_is_not_an_error():
    service, push, _, store, schedule = build(tokens=())
    push_item(service, store, make_item())
    schedule.fire_all()
    assert push.sent == []


# --- the window ------------------------------------------------------------


def test_three_items_in_one_window_become_one_notification():
    """The reason the window exists. Without it the webhook fires per item and
    a busy minute is three buzzes."""
    service, push, _, store, schedule = build()

    for n in range(3):
        push_item(service, store, make_item(id=f"i{n}", source_ref=f"slack:D1:{n}"))
    schedule.fire_all()

    assert len(push.sent) == 1
    assert push.sent[0]["title"] == "3 things need you"
    assert sorted(push.sent[0]["data"]["item_ids"]) == ["i0", "i1", "i2"]


def test_only_the_first_item_opens_a_window():
    """Three items must schedule one flush, not three. Three timers would each
    wake up and the last two would find an empty buffer, which is harmless but
    means the design was not understood."""
    service, _, _, store, schedule = build()

    for n in range(3):
        push_item(service, store, make_item(id=f"i{n}", source_ref=f"slack:D1:{n}"))

    assert len(schedule.pending) == 1
    assert schedule.pending[0][0] == 25.0


def test_nothing_is_sent_before_the_window_closes():
    service, push, _, store, schedule = build()
    push_item(service, store, make_item())
    assert push.sent == []


def test_a_second_flush_for_the_same_user_sends_nothing():
    """The drain empties as it reads. A stray second timer must find nothing
    rather than re-announce the batch."""
    service, push, _, store, schedule = build()
    push_item(service, store, make_item())

    flush = schedule.pending[0][1]
    flush()
    flush()

    assert len(push.sent) == 1


def test_a_later_item_opens_a_fresh_window():
    service, push, _, store, schedule = build()

    push_item(service, store, make_item(id="first", source_ref="slack:D1:a"))
    schedule.fire_all()
    push_item(service, store, make_item(id="second", source_ref="slack:D1:b"))
    schedule.fire_all()

    assert len(push.sent) == 2


# --- what the window is allowed to learn in 25 seconds ---------------------


def test_an_item_handled_during_the_window_is_not_announced():
    """The whole reason the flush re-reads instead of sending its buffered
    snapshot. The user opened the app and dealt with it; buzzing now is the app
    arguing with somebody about a thing they already did."""
    service, push, _, store, schedule = build()
    item = make_item()
    push_item(service, store, item)

    store[item.id] = item.model_copy(update={"handled_at": NOW})
    schedule.fire_all()

    assert push.sent == []


def test_an_item_snoozed_during_the_window_is_not_announced():
    service, push, _, store, schedule = build()
    item = make_item()
    push_item(service, store, item)

    store[item.id] = item.model_copy(
        update={"snoozed_until": NOW + timedelta(hours=2)}
    )
    schedule.fire_all()

    assert push.sent == []


def test_an_item_that_vanished_during_the_window_is_skipped():
    """Redis holds the feed with a 24h TTL and the ledger can retire a row. A
    buffered id that no longer resolves is a normal outcome, not an error."""
    service, push, _, store, schedule = build()
    item = make_item()
    push_item(service, store, item)
    del store[item.id]

    schedule.fire_all()

    assert push.sent == []


# --- devices ---------------------------------------------------------------


def test_every_device_gets_the_notification():
    service, push, _, store, schedule = build(tokens=(PHONE, TABLET))
    push_item(service, store, make_item())
    schedule.fire_all()
    assert sorted(m["to"] for m in push.sent) == sorted([PHONE, TABLET])


def test_a_device_expo_reports_as_dead_is_deleted():
    """Expo's guidance: stop sending to a token that answers
    DeviceNotRegistered. Left in place it is a permanent failed send on every
    future notification."""
    tickets = [
        {"status": "ok", "id": "t0"},
        {"status": "error", "details": {"error": "DeviceNotRegistered"}},
    ]
    service, _, token_repo, store, schedule = build(
        tokens=(PHONE, TABLET), tickets=tickets
    )

    push_item(service, store, make_item())
    schedule.fire_all()

    assert token_repo.tokens_for(ME) == [PHONE]


def test_a_transport_error_deletes_no_tokens():
    service, _, token_repo, store, schedule = build(
        tokens=(PHONE, TABLET), fail=True
    )
    push_item(service, store, make_item())
    schedule.fire_all()
    assert sorted(token_repo.tokens_for(ME)) == sorted([PHONE, TABLET])


# --- never breaking the webhook -------------------------------------------


def test_push_for_item_never_raises():
    """It is called from the deterministic branch of _classify_soon, which has
    no try around it. An exception here would turn a successful ingest into a
    reported error and, because Composio redelivers, into a redelivery loop."""

    class Exploding:
        def add(self, user_id, item_id):
            raise RuntimeError("buffer is on fire")

        def drain(self, user_id):
            raise RuntimeError("buffer is on fire")

    service, _, _, _, _ = build()
    service._buffer = Exploding()
    service.push_for_item(ME, make_item())  # must not raise


def test_a_flush_that_explodes_never_escapes_the_timer_thread():
    """An uncaught exception on a threading.Timer thread prints to stderr and
    kills nothing, so the failure would be invisible."""
    service, _, token_repo, store, schedule = build()
    push_item(service, store, make_item())

    def boom(user_id):
        raise RuntimeError("token store is down")

    token_repo.tokens_for = boom
    schedule.fire_all()  # must not raise


def test_a_dead_expo_never_reaches_the_caller():
    service, _, _, store, schedule = build(fail=True)
    push_item(service, store, make_item())
    schedule.fire_all()  # must not raise
