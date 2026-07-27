"""Later: what arrived and did not need you, read live from each source.

Nothing here is stored, and that is the whole design. Later held 360 rows at one
point, which meant keeping a month of newsletters in the database to render a
list that is different tomorrow anyway: churn dressed up as state. It is now a
mirror of what the provider currently says is unread, unanswered or open, and it
can no more disagree with Gmail than Gmail can disagree with itself.

Rows are yielded in batches rather than returned once, because pulling every
unread message takes the better part of a minute and the screen should fill from
the first page. A source that fails mid-stream keeps what it already produced: a
partial list is worth more than an error.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html import unescape
from queue import Queue
from typing import Any, Callable

from pydantic import BaseModel

from backend.models.events import RawEvent
from backend.models.sources import Source

log = logging.getLogger(__name__)

#: Per source, per open. Later is a glance at what is sitting there, not an
#: archive to page through to the end of.
DEFAULT_LIMIT = 200


class LaterRow(BaseModel):
    """Deliberately thinner than a FeedRow. Nothing here has a tier, because
    nothing here was judged: these are the items that did not reach Home."""

    source: Source
    source_ref: str
    title: str
    summary: str | None = None
    sender_name: str | None = None
    context_chip: str | None = None
    url: str = ""
    occurred_at: datetime | None = None


def _text(raw: str) -> str:
    """Mail arrives escaped for HTML, so an apostrophe reaches the phone as
    `&#39;` and a quotation mark as `&quot;`. These lines are rendered as text
    and never as markup, so the escaping is not protecting anything: it is just
    plumbing showing through the middle of a sentence."""
    return unescape(raw).strip()


def _to_row(event: RawEvent) -> LaterRow:
    actor = getattr(event, "actor", None)
    body = _text(event.body or "")
    return LaterRow(
        source=Source(event.source),
        source_ref=event.source_ref,
        title=_text(event.title),
        summary=(body.splitlines()[0][:140] or None) if body else None,
        sender_name=(actor.display_name or actor.login) if actor else None,
        context_chip=event.context_chip,
        url=event.url or "",
        occurred_at=event.occurred_at,
    )


class LaterService:
    def __init__(
        self,
        integrations: Any | None = None,
        identity_for: Callable[[str, str], Any] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._integrations = integrations
        self._identity_for = identity_for
        self._now = clock or (lambda: datetime.now(timezone.utc))

    def stream(
        self,
        user_id: str,
        source: Source,
        *,
        on_home: set[str],
        limit: int = DEFAULT_LIMIT,
    ) -> Iterator[list[LaterRow]]:
        """Batches of rows for one source, newest first.

        ``on_home`` is the set of source_refs already showing on Home. An item
        in both places would be the two screens disagreeing about one message.
        """
        pages = self._pages(user_id, source, limit)
        if pages is None:
            return

        sent = 0
        try:
            for page in pages:
                batch: list[LaterRow] = []
                for event in page:
                    if event.source_ref in on_home:
                        continue
                    batch.append(_to_row(event))
                    sent += 1
                    if sent >= limit:
                        break
                if batch:
                    yield batch
                if sent >= limit:
                    return
        except Exception:
            # Whatever already arrived stands. The alternative is throwing away
            # a page the user can see in favour of an empty error screen.
            log.warning("later stream failed for %s", source.value, exc_info=True)

    def stream_all(
        self,
        user_id: str,
        *,
        on_home: set[str],
        limit: int = DEFAULT_LIMIT,
    ) -> Iterator[list[LaterRow]]:
        """Every source at once, batches yielded in whatever order they arrive.

        One source at a time meant the user waited on Gmail's ten seconds before
        anything appeared, and waited again on every tap of the strip. Fanned
        out, the first rows show at the *fastest* source's latency and the total
        is the slowest one rather than the sum, so switching source becomes a
        filter over rows already in hand instead of a fresh fetch.

        Each source runs on its own thread feeding a queue that this generator
        drains, which is what lets a batch be yielded the moment it exists. A
        source that fails takes itself out and leaves the rest streaming.
        """
        sources = [
            source
            for source in (
                Source.GMAIL,
                Source.SLACK,
                Source.LINEAR,
                Source.GITHUB,
                Source.GOOGLE_DOCS,
                Source.CALENDAR,
            )
            if self._pages(user_id, source, limit) is not None
        ]
        if not sources:
            return

        batches: Queue[list[LaterRow] | None] = Queue()

        def run(source: Source) -> None:
            try:
                for batch in self.stream(
                    user_id, source, on_home=on_home, limit=limit
                ):
                    batches.put(batch)
            except Exception:
                log.warning("later stream failed for %s", source.value, exc_info=True)
            finally:
                # Always, or the drain below waits forever on a source that died.
                batches.put(None)

        with ThreadPoolExecutor(max_workers=len(sources)) as pool:
            for source in sources:
                pool.submit(run, source)

            done = 0
            while done < len(sources):
                batch = batches.get()
                if batch is None:
                    done += 1
                    continue
                yield batch

    # ------------------------------------------------------------ internals

    def _pages(
        self, user_id: str, source: Source, limit: int
    ) -> Iterator[list[RawEvent]] | None:
        """One generator of pages per source, or None when not connected."""
        if self._integrations is None:
            return None
        if source is Source.GMAIL:
            gmail = self._integrations.gmail(user_id)
            if gmail is not None:
                return gmail.unread_pages(limit=limit)
        if source is Source.SLACK:
            slack = self._integrations.slack(user_id)
            if slack is not None:
                # Later uses the broader `recent` (DMs + channel activity, minus
                # self), not `unread` (DM-only, for Home): otherwise every DM is
                # elevated to Home and Slack Later reads empty (bible 3.3).
                return self._one_page(
                    lambda: slack.recent(self._identity("slack", user_id))
                )
        if source is Source.LINEAR:
            linear = self._integrations.linear(user_id)
            if linear is not None:
                return self._one_page(linear.assigned_to_me)
        if source is Source.GITHUB:
            github = self._integrations.github(user_id)
            if github is not None:
                return self._one_page(github.list_notifications)
        if source is Source.GOOGLE_DOCS:
            docs_factory = getattr(self._integrations, "google_docs", None)
            if docs_factory is not None:
                docs = docs_factory(user_id)
                if docs is not None:
                    return self._one_page(docs.mentions)
        if source is Source.CALENDAR:
            calendar = self._integrations.calendar(user_id)
            if calendar is not None:
                # Only unanswered invites, never accepted meetings: an invite
                # for today or tomorrow is already on Home (Urgent / By EOD) and
                # the on_home filter drops it, so what remains here is exactly the
                # after-tomorrow invites that sit in Later. Meetings would flood
                # this with every upcoming event, so they are left out.
                return self._one_page(
                    lambda: [
                        event
                        for event in calendar.pending()
                        if event.reason == "calendar_invite"
                    ]
                )
        return None

    @staticmethod
    def _one_page(fetch: Callable[[], list[RawEvent]]) -> Iterator[list[RawEvent]]:
        """Sources that answer in a single call still arrive as a stream, so
        the endpoint has one shape rather than two."""
        yield fetch()

    def _identity(self, provider: str, user_id: str) -> Any:
        from backend.models.identity import Identity

        if self._identity_for is None:
            return Identity()
        return self._identity_for(user_id, provider)
