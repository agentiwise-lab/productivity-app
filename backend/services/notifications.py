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
    """Four on the wire, three on the screen: the toggle in You expresses OFF,
    so the segmented control never has to offer it.

    `urgent_today` keeps its wire value even though it is labelled "By EOD"
    everywhere a person can see it. Renaming a persisted enum because its label
    changed is a migration that buys nothing.
    """

    URGENT = "urgent"
    URGENT_TODAY = "urgent_today"
    ALL = "all"
    OFF = "off"


#: `Tier.NOISE` is deliberately absent from every level, including ALL. Later is
#: by definition what did not need you, and buzzing about it would undo the one
#: promise the product makes.
_ALLOWED: dict[NotifyLevel, set[Tier]] = {
    NotifyLevel.URGENT: {Tier.URGENT},
    NotifyLevel.URGENT_TODAY: {Tier.URGENT, Tier.TODAY},
    NotifyLevel.ALL: {Tier.URGENT, Tier.TODAY, Tier.CAN_WAIT},
    NotifyLevel.OFF: set(),
}


class PushTransport(Protocol):
    def send(self, messages: list[dict]) -> list[dict]:
        """Returns Expo's tickets, one per message and in the same order.

        The return value is not decoration: a ticket is the only place Expo
        reports ``DeviceNotRegistered``, and a token that earns it must never be
        sent to again."""
        ...


class SeenStore(Protocol):
    """Which items this user has already been alerted about.

    Split into a read and a write, rather than one atomic claim, because the
    order matters: an item is marked *after* a successful send, so a transient
    Expo outage cannot silently consume the one alert an item ever gets.
    """

    def seen(self, item_id: str) -> bool:
        ...

    def mark(self, item_ids: list[str]) -> None:
        ...


class InMemorySeenStore:
    """The default, and correct for a single process. Production injects the
    Redis-backed one instead, so a restart does not re-announce everything the
    user was already told about."""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def seen(self, item_id: str) -> bool:
        return item_id in self._seen

    def mark(self, item_ids: list[str]) -> None:
        self._seen.update(item_ids)


#: Expo's ticket error meaning the app is gone from that device: uninstalled,
#: permission revoked, or deregistered by FCM/APNs. The only ticket error that
#: justifies deleting a token; everything else (a rate limit, an oversized
#: message) is our problem and would silently unsubscribe a working phone.
DEVICE_NOT_REGISTERED = "DeviceNotRegistered"


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
        seen: SeenStore | None = None,
    ) -> None:
        self._push = push
        self._now = clock or (lambda: datetime.now(timezone.utc))
        self._seen = seen or InMemorySeenStore()

    def notify(
        self,
        tokens: list[str],
        items: list[FeedItem],
        prefs: UserPreferences,
        level: NotifyLevel,
    ) -> list[str]:
        """Alert every one of this user's devices, once, about what is due.

        Takes *all* the user's tokens rather than one, and that is the whole
        reason the signature is a list. Called once per device instead, the
        first call would mark the batch seen and every later device would find
        nothing left to say, so a user with a phone and a tablet would be told
        on exactly one of them.

        Returns the tokens Expo reported as dead, for the caller to delete. This
        service does not own the token table and should not reach into it.
        """
        if not tokens:
            return []

        due = [item for item in items if self._should_notify(item, prefs, level)]
        if not due:
            return []

        messages = [build_message(token, due) for token in tokens]
        try:
            tickets = self._push.send(messages)
        except Exception:
            log.warning("push failed for %d items", len(due), exc_info=True)
            return []

        # Only after a successful send, so a transient outage does not silently
        # consume the one alert an item ever gets. Marked once for the whole
        # fan-out, never per device.
        self._seen.mark([item.id for item in due])
        return self._dead_tokens(tokens, tickets)

    @staticmethod
    def _dead_tokens(tokens: list[str], tickets: list[dict] | None) -> list[str]:
        """Tickets come back index-aligned with the messages we sent, so a
        ticket's position names its token. A short or absent list is not an
        error worth raising over: it just means we learned nothing."""
        dead: list[str] = []
        for token, ticket in zip(tokens, tickets or []):
            details = (ticket or {}).get("details") or {}
            if details.get("error") == DEVICE_NOT_REGISTERED:
                dead.append(token)
        return dead

    def _should_notify(
        self, item: FeedItem, prefs: UserPreferences, level: NotifyLevel
    ) -> bool:
        if self._seen.seen(item.id):
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

    #: Expo rejects a request carrying more than this many messages.
    MAX_PER_REQUEST = 100

    def __init__(self, client=None) -> None:
        self._client = client

    def send(self, messages: list[dict]) -> list[dict]:
        import httpx

        client = self._client or httpx.Client(timeout=10.0)
        tickets: list[dict] = []
        # Chunked so the index-alignment the caller relies on survives a user
        # with an implausible number of devices, rather than the request being
        # rejected whole.
        for start in range(0, len(messages), self.MAX_PER_REQUEST):
            chunk = messages[start : start + self.MAX_PER_REQUEST]
            response = client.post(self.ENDPOINT, json=chunk)
            response.raise_for_status()
            tickets.extend((response.json() or {}).get("data") or [])
        return tickets
