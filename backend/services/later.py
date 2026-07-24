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
from datetime import datetime, timezone
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


def _to_row(event: RawEvent) -> LaterRow:
    actor = getattr(event, "actor", None)
    return LaterRow(
        source=Source(event.source),
        source_ref=event.source_ref,
        title=event.title,
        summary=(event.body or "").strip().splitlines()[0][:140] or None
        if event.body
        else None,
        sender_name=(actor.display_name or actor.login) if actor else None,
        context_chip=event.context_chip,
        url=event.url or "",
        occurred_at=event.occurred_at,
    )


class LaterService:
    def __init__(
        self,
        gmail: Any | None = None,
        slack: Any | None = None,
        linear: Any | None = None,
        github: Any | None = None,
        identity_for: Callable[[str, str], Any] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._gmail = gmail
        self._slack = slack
        self._linear = linear
        self._github = github
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

    # ------------------------------------------------------------ internals

    def _pages(
        self, user_id: str, source: Source, limit: int
    ) -> Iterator[list[RawEvent]] | None:
        """One generator of pages per source, or None when not connected."""
        if source is Source.GMAIL and self._gmail is not None:
            return self._gmail.unread_pages(limit=limit)
        if source is Source.SLACK and self._slack is not None:
            return self._one_page(
                lambda: self._slack.unread(self._identity("slack", user_id))
            )
        if source is Source.LINEAR and self._linear is not None:
            return self._one_page(self._linear.assigned_to_me)
        if source is Source.GITHUB and self._github is not None:
            return self._one_page(self._github.list_notifications)
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
