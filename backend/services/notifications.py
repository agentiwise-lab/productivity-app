"""Push notifications, through Expo.

The product's promise is that a buzz means something. That promise is kept by
three rules, all enforced here rather than trusted to callers:

1. **Urgent only**, unless the user widened it themselves.
2. **Once per item, ever.** Every refresh re-reads the same urgent items, so
   without a seen-set the user is alerted about the same thing all morning,
   which is exactly how people learn to disable notifications.
3. **One notification per batch.** Five buzzes for five items is the dump this
   product exists to replace.

Nothing here raises. A dead push provider must never break a feed refresh: not
being notified is a small failure, and not being able to open the app is a
large one.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Protocol

from backend.models.feed import FeedItem, UserPreferences
from backend.models.tiers import Tier
from backend.services.ranking import effective_tier

log = logging.getLogger(__name__)


class NotifyLevel(str, Enum):
    URGENT = "urgent"
    URGENT_TODAY = "urgent_today"
    OFF = "off"


_ALLOWED: dict[NotifyLevel, set[Tier]] = {
    NotifyLevel.URGENT: {Tier.URGENT},
    NotifyLevel.URGENT_TODAY: {Tier.URGENT, Tier.TODAY},
    NotifyLevel.OFF: set(),
}


class PushTransport(Protocol):
    def send(self, messages: list[dict]) -> None:
        ...


def build_message(token: str, items: list[FeedItem]) -> dict:
    """One notification for the whole batch.

    A single item gets named: who wants what. Several get counted, because a
    list of five names on a lock screen is not readable and the user is going
    to open the app anyway.
    """
    if len(items) == 1:
        item = items[0]
        who = item.sender_name or item.sender_handle
        return {
            "to": token,
            "title": f"{who} needs you" if who else "Something needs you",
            "body": item.summary or item.title,
            "data": {"item_id": item.id, "url": item.url},
            "sound": "default",
        }

    return {
        "to": token,
        "title": f"{len(items)} things need you",
        "body": ", ".join(
            filter(None, (item.sender_name or item.sender_handle for item in items[:3]))
        )
        or "Open to see what came in.",
        "data": {"item_ids": [item.id for item in items]},
        "sound": "default",
    }


class DefaultNotificationService:
    def __init__(
        self,
        push: PushTransport,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._push = push
        self._now = clock or (lambda: datetime.now(timezone.utc))
        # Item ids already alerted on. In production this belongs in the
        # database next to the item; in a single process a set is enough and
        # the behaviour it guarantees is the same.
        self._notified: set[str] = set()

    def notify(
        self,
        token: str | None,
        items: list[FeedItem],
        prefs: UserPreferences,
        level: NotifyLevel,
    ) -> None:
        if not token:
            return

        due = [item for item in items if self._should_notify(item, prefs, level)]
        if not due:
            return

        try:
            self._push.send([build_message(token, due)])
        except Exception:
            log.warning("push failed for %d items", len(due), exc_info=True)
            return

        # Only after a successful send, so a transient outage does not silently
        # consume the one alert an item ever gets.
        self._notified.update(item.id for item in due)

    def _should_notify(
        self, item: FeedItem, prefs: UserPreferences, level: NotifyLevel
    ) -> bool:
        if item.id in self._notified:
            return False
        if item.handled_at is not None:
            return False

        now = self._now()
        if item.snoozed_until is not None and item.snoozed_until > now:
            # The user already said "not now" about this exact thing.
            return False
        if item.context_chip and item.context_chip in prefs.muted_channels:
            return False
        if item.repo and item.repo in prefs.muted_repos:
            return False

        return effective_tier(item, now=now) in _ALLOWED[level]


class ExpoPushTransport:
    """Expo's push endpoint. No SDK needed: it is one POST."""

    ENDPOINT = "https://exp.host/--/api/v2/push/send"

    def __init__(self, client=None) -> None:
        self._client = client

    def send(self, messages: list[dict]) -> None:
        import httpx

        client = self._client or httpx.Client(timeout=10.0)
        response = client.post(self.ENDPOINT, json=messages)
        response.raise_for_status()
