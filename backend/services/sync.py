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
        github: Any | None = None,
        linear: Any | None = None,
        gmail: Any | None = None,
        calendar: Any | None = None,
        classifier: Any | None = None,
        identity_for: Callable[[str, str], Identity] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._feed = feed
        self._sources: dict[Source, Callable[[], list[RawEvent]]] = {}
        if github is not None:
            self._sources[Source.GITHUB] = github.list_notifications
        if linear is not None:
            self._sources[Source.LINEAR] = linear.assigned_to_me
        if gmail is not None:
            self._sources[Source.GMAIL] = gmail.unread
        if calendar is not None:
            self._sources[Source.CALENDAR] = calendar.pending
        self._classifier = classifier
        self._identity_for = identity_for or (lambda user, provider: Identity())
        self._now = clock or (lambda: datetime.now(timezone.utc))

    def refresh(self, user_id: str, prefs: UserPreferences | None = None) -> SyncReport:
        prefs = prefs or UserPreferences(user_id=user_id)
        report = SyncReport()

        for source, fetch in self._sources.items():
            try:
                events = fetch()
            except Exception as error:
                # Degrade this source only. The others still refresh.
                log.warning("refresh failed for %s", source.value, exc_info=True)
                report.failed[source.value] = str(error)[:200]
                continue

            identity = self._identity_for(user_id, source.value)
            count = 0
            for event in events:
                try:
                    self._feed.ingest(user_id, event, prefs, identity)
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
            try:
                report.classified = self._classifier.classify_pending(user_id).classified
            except Exception:
                # Rules-only is a working product; a dead model is not an outage.
                log.warning("classification pass failed", exc_info=True)

        return report
