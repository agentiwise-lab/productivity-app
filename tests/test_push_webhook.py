"""Composio webhook to Expo message, through the real HTTP route.

Everything else about push is unit-tested against its own contract. This is the
one test that proves the pieces actually compose: a real POST to
`/webhooks/composio`, the real router, the real ingest service, the real hook,
the real window, and a fake only at the two edges the test must control (the
HTTP call to Expo, and the passage of 25 seconds).

Without it, every seam could be individually correct and the feature still send
nothing, because nobody wired `on_item_ready`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.repositories.device_token_repository import (
    InMemoryDeviceTokenRepository,
)
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.notifications import DefaultNotificationService, NotifyLevel
from backend.services.push import DefaultPushService
from tests.fakes import FakeGitHubService
from tests.test_ingest import USER, envelope

TOKEN = "ExponentPushToken[on-the-phone]"


class FakePush:
    def __init__(self):
        self.sent: list[dict] = []

    def send(self, messages: list[dict]) -> list[dict]:
        self.sent.extend(messages)
        return [{"status": "ok", "id": f"t{n}"} for n in range(len(messages))]


class FakeSchedule:
    def __init__(self):
        self.pending: list = []

    def __call__(self, delay, work):
        self.pending.append(work)

    def fire_all(self):
        due, self.pending = self.pending, []
        for work in due:
            work()


def notification(number: int) -> dict:
    return {
        "id": f"245120808{number}",
        "reason": "review_requested",
        "repository": {"full_name": "octo/repo"},
        "subject": {
            "type": "PullRequest",
            "title": f"Add rate limiting part {number}",
            "url": f"https://api.github.com/repos/octo/repo/pulls/{number}",
        },
        "updated_at": "2026-07-27T11:00:00Z",
    }


def build(level=NotifyLevel.URGENT_TODAY, tokens=(TOKEN,)):
    repo = InMemoryFeedRepository()
    devices = InMemoryDeviceTokenRepository()
    for token in tokens:
        devices.upsert(USER, token, "android")

    push = FakePush()
    schedule = FakeSchedule()
    service = DefaultPushService(
        notifications=DefaultNotificationService(push=push),
        tokens=devices,
        item_for=lambda user_id, item_id: repo.get(user_id, item_id),
        level_for=lambda user_id: level,
        schedule=schedule,
    )

    app = create_app(
        github=FakeGitHubService(),
        repo=repo,
        auth_mode="dev",
        # The webhook is authenticated by signature, not by a bearer token.
        # Handing back the parsed body is what the real verifier does once the
        # signature checks out.
        verify_webhook=lambda body, headers: __import__("json").loads(body),
        device_tokens=devices,
        on_item_ready=service.push_for_item,
    )
    return TestClient(app), push, schedule, repo, devices


def deliver(client, number: int):
    return client.post(
        "/webhooks/composio",
        json=envelope(
            "GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER", notification(number)
        ),
    )


def test_one_webhook_becomes_one_notification_on_the_phone():
    """A review request lands as By EOD, so this runs at the level that covers
    it. The `urgent`-only case is the test below, and the pair is what proves
    the level actually decides something."""
    client, push, schedule, _, _ = build()

    assert deliver(client, 1).json()["handled"] is True
    assert push.sent == []  # the window is still open

    schedule.fire_all()

    assert len(push.sent) == 1
    assert push.sent[0]["to"] == TOKEN
    assert "Add rate limiting part 1" in (
        push.sent[0]["body"] + push.sent[0]["title"]
    )


def test_a_by_eod_item_stays_silent_at_the_urgent_only_level():
    """The same webhook, one setting narrower, and the phone stays quiet. This
    is the product's whole claim, asserted through the real route rather than
    against the filter in isolation."""
    client, push, schedule, repo, _ = build(level=NotifyLevel.URGENT)

    deliver(client, 1)
    schedule.fire_all()

    assert push.sent == []
    # ...and it is still in the feed, because the setting governs the buzz and
    # never the collecting.
    assert len(repo.list_by_user(USER)) == 1


def test_two_webhooks_in_one_window_become_a_single_notification():
    """The whole reason the window exists, proved end to end rather than
    against the buffer in isolation."""
    client, push, schedule, _, _ = build()

    deliver(client, 1)
    deliver(client, 2)
    schedule.fire_all()

    assert len(push.sent) == 1
    assert push.sent[0]["title"] == "2 things need you"
    assert len(push.sent[0]["data"]["item_ids"]) == 2


def test_the_same_webhook_delivered_twice_buzzes_once():
    """Composio redelivers anything it failed to deliver, and the refresh sweep
    re-reads the same items. Neither may produce a second buzz."""
    client, push, schedule, _, _ = build()

    deliver(client, 1)
    schedule.fire_all()
    deliver(client, 1)
    schedule.fire_all()

    assert len(push.sent) == 1


def test_the_webhook_still_acks_when_there_is_nobody_to_notify():
    """No device registered. The ingest must not care: a 200 here is what stops
    Composio from redelivering forever."""
    client, push, schedule, _, _ = build(tokens=())

    assert deliver(client, 1).status_code == 200
    schedule.fire_all()
    assert push.sent == []


def test_notifications_switched_off_reaches_no_phone():
    client, push, schedule, _, _ = build(level=NotifyLevel.OFF)

    deliver(client, 1)
    schedule.fire_all()

    assert push.sent == []


def test_the_item_still_lands_in_the_feed_when_push_is_off():
    """Off means "do not buzz me", never "do not collect it"."""
    client, _, schedule, repo, _ = build(level=NotifyLevel.OFF)

    deliver(client, 1)
    schedule.fire_all()

    assert len(repo.list_by_user(USER)) == 1
