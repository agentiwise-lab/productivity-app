"""Fetch on open, across every connected source.

GitHub, Linear and Gmail are polled because their triggers either cannot carry
the urgent tier or do not exist account-wide. Slack arrives by push and is not
polled here. Calendar is polled for pending invites and read separately, and
live, for the ruler.

One rule governs the whole file: **a source that fails must never take the
others down with it.** Plan 6.4 calls for per-source degradation, and a single
expired Google token bringing back an empty feed would look identical to a quiet
morning.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable

from pydantic import BaseModel

from backend.models.events import RawEvent
from backend.models.feed import UserPreferences
from backend.models.identity import Identity
from backend.models.sources import Source
from backend.services.feed import FeedService

log = logging.getLogger(__name__)


class SyncReport(BaseModel):
    ingested: int = 0
    classified: int = 0
    #: Per source, so the app can say which integration is quiet and which is
    #: broken instead of showing one undifferentiated empty screen.
    per_source: dict[str, int] = {}
    failed: dict[str, str] = {}


class SourceSync:
    def __init__(
        self,
        feed: FeedService,
        integrations: Any | None = None,
        classifier: Any | None = None,
        identity_for: Callable[[str, str], Identity] | None = None,
        clock: Callable[[], datetime] | None = None,
        # Gmail sets this floor: pulling every unread message in the window is
        # three pages and about 37 seconds on a mailbox with a few hundred, and
        # at 25s it was cut off mid-fetch so the whole source reported failure.
        # Nobody waits on this. The app paints from cache and the sources refresh
        # behind it.
        timeout: float = 90.0,
        classify_async: bool = False,
    ) -> None:
        self._timeout = timeout
        self._classify_async = classify_async
        self._background = ThreadPoolExecutor(max_workers=1)
        self._feed = feed
        self._integrations = integrations
        self._classifier = classifier
        self._identity_for = identity_for or (lambda user, provider: Identity())
        self._now = clock or (lambda: datetime.now(timezone.utc))

    def _sources_for(
        self, user_id: str
    ) -> dict[Source, Callable[[], list[RawEvent]]]:
        """The pollers, bound to this user's accounts. Built per refresh rather
        than at construction, because the account each one reads is the caller's,
        not a single shared one."""
        sources: dict[Source, Callable[[], list[RawEvent]]] = {}
        if self._integrations is None:
            return sources

        github = self._integrations.github(user_id)
        if github is not None:
            sources[Source.GITHUB] = github.list_notifications

        linear = self._integrations.linear(user_id)
        if linear is not None:
            sources[Source.LINEAR] = linear.assigned_to_me

        gmail = self._integrations.gmail(user_id)
        if gmail is not None:
            # Only mail that could need a reply. The broad fetch belongs to
            # Later, which reads it live; asking for it here meant pulling 361
            # messages to store 12 and made the refresh eight times slower.
            sources[Source.GMAIL] = gmail.actionable

        calendar = self._integrations.calendar(user_id)
        if calendar is not None:
            sources[Source.CALENDAR] = calendar.pending

        slack = self._integrations.slack(user_id)
        if slack is not None:
            # Slack pushes in real time, but only while we are running. The
            # backfill is what makes this morning's messages exist at all.
            sources[Source.SLACK] = lambda: slack.unread(
                self._identity_for(user_id, "slack")
            )
        return sources

    def refresh(self, user_id: str, prefs: UserPreferences | None = None) -> SyncReport:
        prefs = prefs or UserPreferences(user_id=user_id)
        report = SyncReport()
        sources = self._sources_for(user_id)

        # Fetched in parallel. These are independent network calls to different
        # providers, and run in series they add up: Gmail alone took most of a
        # fifteen-second refresh while GitHub and Calendar sat idle waiting for
        # it. Wall time is now the slowest source, not the sum of all of them.
        fetched: dict[Source, Any] = {}
        with ThreadPoolExecutor(max_workers=max(1, len(sources))) as pool:
            futures = {
                pool.submit(fetch): source for source, fetch in sources.items()
            }
            for future, source in futures.items():
                try:
                    fetched[source] = future.result(timeout=self._timeout)
                except Exception as error:
                    # Degrade this source only. The others still refresh.
                    log.warning("refresh failed for %s", source.value, exc_info=True)
                    report.failed[source.value] = str(error)[:200]

        for source, events in fetched.items():
            identity = self._identity_for(user_id, source.value)
            count = 0
            for event in events:
                try:
                    # None means it reaches no screen and was not stored.
                    if self._feed.ingest(user_id, event, prefs, identity) is not None:
                        count += 1
                except Exception:
                    # One malformed row must not abandon the rest of the batch.
                    log.warning(
                        "could not ingest %s from %s",
                        getattr(event, "source_ref", "?"),
                        source.value,
                        exc_info=True,
                    )
            report.per_source[source.value] = count
            report.ingested += count

        if self._classifier is not None:
            if self._classify_async:
                # The feed is already correct at rule tiers, so nobody waits for
                # the model. Summaries appear on the next read (plan 4.4).
                self._background.submit(self._classify_quietly, user_id)
            else:
                report.classified = self._classify_quietly(user_id)

        return report

    def _classify_quietly(self, user_id: str) -> int:
        try:
            return self._classifier.classify_pending(user_id).classified
        except Exception:
            # Rules-only is a working product; a dead model is not an outage.
            log.warning("classification pass failed", exc_info=True)
            return 0
