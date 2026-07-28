"""Deciding that a phone should buzz, and making sure it buzzes once.

`DefaultNotificationService` already owns *what* is worth announcing. This owns
*when*, and the answer is not "the moment an item lands", for one reason:

The webhook fires per item. Three things arriving in the same minute would be
three separate buzzes, which is precisely the pile the product exists to
replace. So an item does not send, it **joins a window**. The first item of a
window schedules a flush; everything arriving inside that window joins it; the
flush sends one notification for the lot.

Two properties fall out of that shape and both are load-bearing:

**Nothing touches a database on the webhook path.** `push_for_item` appends to
memory and, at most, schedules a timer. Every read (the level, the tokens, the
items) happens on the flush 25 seconds later. `ingest.py` already moves
classification off this path because Composio retry-storms on a slow response,
and two round trips per item would have undone that. It also means the notify
level is read at send time, so somebody who switches to Off inside the window is
not buzzed by an item buffered a moment earlier.

**The flush re-reads the items.** A snapshot buffered 25 seconds ago does not
know the user has since opened the app and handled or snoozed the thing, and
those are exactly the two fields the filter checks. Announcing something the
user just dealt with is the failure this product exists to prevent, so the
buffer holds *ids* and the flush resolves them fresh.

Nothing here raises. It is called from the deterministic branch of
`_classify_soon`, which has no `try` around it, so an escape would turn a
successful ingest into a reported error and, because Composio redelivers,
into a redelivery loop.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Protocol

from backend.models.feed import FeedItem, UserPreferences
from backend.services.notifications import DefaultNotificationService, NotifyLevel
from backend.repositories.device_token_repository import DeviceTokenRepository

log = logging.getLogger(__name__)

#: How long a window stays open. Long enough that a burst of related items
#: (a thread waking up, a morning's mail landing at once) becomes one buzz,
#: short enough that an urgent thing is not stale by the time it arrives.
WINDOW_SECONDS = 25.0


class PendingBuffer(Protocol):
    def add(self, user_id: str, item_id: str) -> bool:
        """Join this user's open window, opening one if there is none.

        Returns True only for the item that *opened* the window, which is the
        caller's signal to schedule exactly one flush. Three items must produce
        one timer, not three.
        """
        ...

    def drain(self, user_id: str) -> list[str]:
        """Take everything waiting, atomically.

        Empties as it reads, so a second timer firing for the same user gets
        nothing back and sends nothing rather than re-announcing the batch.
        """
        ...


class InMemoryPendingBuffer:
    """Correct for this deployment, which runs a single uvicorn worker
    (docs/deployment-plan.md: the classification cache requires it). With one
    process there is nothing to fragment, and a Redis-backed buffer would buy
    complexity and no behaviour.

    Locked because the flush runs on a timer thread while the webhook thread is
    still appending.

    The accepted cost: a restart inside a live window drops that window's buzz.
    The items are still in the feed and on the next screen the user opens, and
    the seen store will not let them be re-announced later.
    """

    def __init__(self) -> None:
        self._pending: dict[str, list[str]] = {}
        self._lock = threading.Lock()

    def add(self, user_id: str, item_id: str) -> bool:
        with self._lock:
            waiting = self._pending.setdefault(user_id, [])
            opened_the_window = not waiting
            # Guard against the same item arriving twice inside one window (a
            # redelivered webhook), which would otherwise make a single item
            # render as "2 things need you".
            if item_id not in waiting:
                waiting.append(item_id)
            return opened_the_window

    def drain(self, user_id: str) -> list[str]:
        with self._lock:
            return self._pending.pop(user_id, [])


class RedisSeenStore:
    """The "once, ever" guarantee, made to survive a restart.

    `SETNX`-style writes with a TTL matching the feed's own 24h. Item ids are
    deterministic (uuid5 over the source ref), so an item that survives a cold
    Redis rebuild keeps its id and stays marked.

    Fails open on a Redis error: not knowing whether we have announced
    something is a reason to risk announcing it twice, never a reason to drop
    the alert entirely.
    """

    def __init__(self, redis, ttl_seconds: int = 24 * 60 * 60) -> None:
        self._r = redis
        self._ttl = ttl_seconds

    @staticmethod
    def _key(item_id: str) -> str:
        return f"notified:{item_id}"

    def seen(self, item_id: str) -> bool:
        try:
            return bool(self._r.exists(self._key(item_id)))
        except Exception:
            log.warning("seen-store read failed for %s", item_id, exc_info=True)
            return False

    def mark(self, item_ids: list[str]) -> None:
        try:
            for item_id in item_ids:
                self._r.set(self._key(item_id), "1", ex=self._ttl)
        except Exception:
            log.warning("seen-store write failed", exc_info=True)


class PushService(Protocol):
    def push_for_item(self, user_id: str, item: FeedItem) -> None:
        ...


def _timer_schedule(delay: float, work: Callable[[], None]) -> None:
    timer = threading.Timer(delay, work)
    # Daemon so a pending window cannot hold a shutdown open for 25 seconds.
    timer.daemon = True
    timer.start()


class DefaultPushService:
    def __init__(
        self,
        notifications: DefaultNotificationService,
        tokens: DeviceTokenRepository,
        item_for: Callable[[str, str], FeedItem | None],
        level_for: Callable[[str], NotifyLevel],
        prefs_for: Callable[[str], UserPreferences] | None = None,
        buffer: PendingBuffer | None = None,
        schedule: Callable[[float, Callable[[], None]], None] | None = None,
        window_seconds: float = WINDOW_SECONDS,
    ) -> None:
        self._notifications = notifications
        self._tokens = tokens
        self._item_for = item_for
        self._level_for = level_for
        self._prefs_for = prefs_for or (
            lambda user_id: UserPreferences(user_id=user_id)
        )
        self._buffer = buffer or InMemoryPendingBuffer()
        # Injected so tests close a window with a function call instead of a
        # sleep. Production is a daemon threading.Timer.
        self._schedule = schedule or _timer_schedule
        self._window = window_seconds

    def push_for_item(self, user_id: str, item: FeedItem) -> None:
        """The ingest hook. Memory only: see the module docstring."""
        try:
            if self._buffer.add(user_id, item.id):
                self._schedule(self._window, lambda: self._flush(user_id))
        except Exception:
            log.warning("could not buffer %s for push", item.id, exc_info=True)

    def _flush(self, user_id: str) -> None:
        """The window closed. Everything expensive happens here.

        Wrapped whole, because this runs on a timer thread where an uncaught
        exception prints to stderr and is otherwise invisible.
        """
        try:
            item_ids = self._buffer.drain(user_id)
            if not item_ids:
                return  # a second timer for the same user; the batch is gone

            level = self._level_for(user_id)
            if level == NotifyLevel.OFF:
                return  # read now, not at buffer time, so a late Off is honoured

            tokens = self._tokens.tokens_for(user_id)
            if not tokens:
                return

            # Re-read: the buffered snapshot does not know what the user did in
            # the last 25 seconds, and an id that no longer resolves (TTL,
            # retired by the ledger) is a normal outcome rather than an error.
            items = [
                item
                for item in (self._item_for(user_id, item_id) for item_id in item_ids)
                if item is not None
            ]
            if not items:
                return

            dead = self._notifications.notify(
                tokens, items, self._prefs_for(user_id), level
            )
            for token in dead:
                log.info("dropping a device Expo reported as gone")
                self._tokens.delete(token)
        except Exception:
            log.warning("push flush failed for %s", user_id, exc_info=True)
