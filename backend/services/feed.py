"""Feed orchestration: the spine.

``ingest`` turns a RawEvent into a stored, rule-classified FeedItem. It never
waits on the model: the rule tier is assigned and the row is stored immediately,
so the item is visible at once, and classification catches up later (plan 4.4).

``list_feed`` computes the tier and the score at read time and returns the rows
ranked. ``comment`` acts from the feed back into GitHub.

It depends only on the other services' contracts, never their implementations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, tzinfo
from typing import Any, Callable, Protocol
from uuid import uuid4

from backend.integrations.github import GitHubService, PRRef
from backend.models.events import RawEvent
from backend.models.feed import FeedItem, FeedRow, FeedStatus, UserPreferences
from backend.models.identity import Identity
from backend.repositories.feed_repository import FeedRepository
from backend.services.hashing import content_hash
from backend.services.ranking import effective_tier, read_time_reason, score
from backend.models.tiers import Tier
from backend.services.rules import RuleClassifier, RuleVerdict

log = logging.getLogger(__name__)


class ItemNotFound(Exception):
    """Raised when an action targets a feed item that does not exist for a user."""


def _reaches_no_screen(verdict: RuleVerdict) -> bool:
    """True when storing this row would serve nothing.

    Home shows what needs the user. Later reads the provider live. So an item
    the rules settle as noise appears on neither screen, and keeping it means a
    month of newsletters in the database backing a list that is fetched fresh
    anyway: 349 of one refresh's 361 emails, all of them churn.

    Only settled verdicts qualify. An item still waiting on the model has no
    tier yet, and one the model has judged stays put: it is a small set, and
    keeping it is what stops every refresh re-classifying the same messages.

    ``ephemeral`` is what separates a newsletter from the user's own untouched
    Linear backlog: both settle as noise, but only the newsletter is churn worth
    dropping. A non-ephemeral noise item is kept as a visible "later" row.
    """
    return verdict.tier is Tier.NOISE and not verdict.needs_llm and verdict.ephemeral


def _is_held(item: FeedItem) -> bool:
    """True while the model still owes this item a verdict.

    An item the rules deferred (``needs_llm``) has no real tier until the model
    lands one. Showing it meanwhile would mean a placeholder tier and a blank
    reason, which is exactly what this redesign exists to prevent. The
    ``llm_attempted_at`` marker is what keeps this from also hiding a *failed*
    item: once the model has tried and given up, the item is no longer held —
    it surfaces at its band ceiling instead."""
    return (
        item.needs_llm
        and item.llm_tier is None
        and item.llm_attempted_at is None
    )


def _calendar_off_day(item: FeedItem, now: datetime, tz: tzinfo) -> bool:
    """A calendar_meeting whose start is not the user's local today does not
    belong on Home: the poll window spills a day either side of midnight. Invites
    (needsAction) are kept regardless — they want an answer whenever they land."""
    if item.source != "calendar" or item.signal == "calendar_invite":
        return False
    start = item.occurred_at
    if start is None:
        return False
    return start.astimezone(tz).date() != now.astimezone(tz).date()


def _meeting_has_passed(item: FeedItem, now: datetime) -> bool:
    """A calendar item whose meeting has ended is over and does not belong on the
    feed at any tier. ``deadline`` carries the meeting's end. This also clears any
    stale calendar rows left from before a refresh, whose end is already past."""
    return (
        item.source == "calendar"
        and item.deadline is not None
        and item.deadline <= now
    )


def _pr_ref_from_source_ref(source_ref: str) -> PRRef:
    """Parse "owner/name#number" into a PRRef."""
    repo, _, number = source_ref.partition("#")
    if not repo or not number.isdigit():
        raise ValueError(f"source_ref is not a PR reference: {source_ref!r}")
    return PRRef(repo=repo, number=int(number))


class FeedService(Protocol):
    def ingest(
        self,
        user_id: str,
        event: RawEvent,
        prefs: UserPreferences,
        identity: Identity | None = None,
    ) -> FeedItem | None:
        """None when the item reaches no screen and was not stored."""
        ...

    def list_feed(
        self,
        user_id: str,
        prefs: UserPreferences | None = None,
        tz: tzinfo = timezone.utc,
    ) -> list[FeedRow]:
        ...

    def comment(self, user_id: str, item_id: str, body: str) -> FeedItem:
        ...


class DefaultFeedService:
    def __init__(
        self,
        repo: FeedRepository,
        rules: RuleClassifier,
        integrations: Any | None = None,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repo = repo
        self._rules = rules
        self._integrations = integrations
        self._new_id = id_factory or (lambda: uuid4().hex)
        self._now = clock or (lambda: datetime.now(timezone.utc))

    def ingest(
        self,
        user_id: str,
        event: RawEvent,
        prefs: UserPreferences,
        identity: Identity | None = None,
    ) -> FeedItem | None:
        verdict = self._rules.classify(event, identity=identity or Identity())
        if _reaches_no_screen(verdict):
            return None
        now = self._now()
        item = FeedItem(
            id=self._new_id(),
            user_id=user_id,
            source=event.source,
            source_ref=event.source_ref,
            rule_tier=verdict.tier,
            type_tag=verdict.type_tag,
            needs_llm=verdict.needs_llm,
            signal=verdict.signal,
            content_hash=content_hash(event),
            title=event.title,
            url=event.url,
            repo=event.repo,
            context_chip=event.context_chip or event.repo or None,
            actors=[event.actor] if event.actor else [],
            sender_handle=event.actor.login if event.actor else None,
            sender_name=(
                event.actor.display_name or event.actor.login if event.actor else None
            ),
            deadline=event.deadline or event.milestone_due,
            occurred_at=event.occurred_at or now,
            body=event.body,
            is_blocking=event.is_blocking,
            created_at=now,
            raw=event.raw,
        )
        return self._repo.upsert(item)

    def list_feed(
        self,
        user_id: str,
        prefs: UserPreferences | None = None,
        tz: tzinfo = timezone.utc,
    ) -> list[FeedRow]:
        prefs = prefs or UserPreferences(user_id=user_id)
        now = self._now()
        rows = []
        held = 0
        for item in self._repo.list_by_user(user_id):
            # Held items (deferred to the model, not yet judged) never reach a
            # screen: a placeholder tier and a blank reason is the one thing this
            # feed must not show. Passed meetings are equally over.
            if _is_held(item):
                held += 1
                continue
            if _meeting_has_passed(item, now):
                continue
            if _calendar_off_day(item, now, tz):
                continue
            tier = effective_tier(item, now=now, tz=tz)
            # Noise-tier items are kept and returned: To-dos renders them at the
            # bottom (below can_wait), so the Later material the refresh already
            # identified is visible in the feed (Vicky's call 2026-07-27). The Day
            # ring ignores noise client-side, and Later (a separate live mirror)
            # excludes anything on Home, so each item still appears in one place.
            data = item.model_dump()
            reason = read_time_reason(item, now=now, tz=tz)
            if reason is not None:
                data["reason"] = reason
            rows.append(
                FeedRow(
                    **data,
                    tier=tier,
                    priority_score=score(item, prefs, now=now, tz=tz),
                )
            )
        rows.sort(key=lambda row: row.priority_score, reverse=True)
        log.info(
            "feed user=%s rows=%d hidden_held=%d tz=%s | %s",
            user_id,
            len(rows),
            held,
            getattr(tz, "key", tz),
            ", ".join(f"{r.source}:{r.tier.value}" for r in rows[:12]) or "-",
        )
        return rows

    def comment(self, user_id: str, item_id: str, body: str) -> FeedItem:
        item = self._repo.get(user_id, item_id)
        if item is None:
            raise ItemNotFound(item_id)
        self._integrations.github(user_id).comment_on_pull_request(
            _pr_ref_from_source_ref(item.source_ref), body
        )
        return self._repo.mark_handled(
            user_id, item_id, status=FeedStatus.ACTED, at=self._now()
        )
