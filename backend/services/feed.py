"""Feed orchestration: the spine.

``ingest`` turns a RawEvent into a stored, rule-classified FeedItem. It never
waits on the model: the rule tier is assigned and the row is stored immediately,
so the item is visible at once, and classification catches up later (plan 4.4).

``list_feed`` computes the tier and the score at read time and returns the rows
ranked. ``comment`` acts from the feed back into GitHub.

It depends only on the other services' contracts, never their implementations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Protocol
from uuid import uuid4

from backend.integrations.github import GitHubService, PRRef
from backend.models.events import RawEvent
from backend.models.feed import FeedItem, FeedRow, FeedStatus, UserPreferences
from backend.models.identity import Identity
from backend.repositories.feed_repository import FeedRepository
from backend.services.hashing import content_hash
from backend.services.ranking import effective_tier, score
from backend.services.rules import RuleClassifier


class ItemNotFound(Exception):
    """Raised when an action targets a feed item that does not exist for a user."""


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
    ) -> FeedItem:
        ...

    def list_feed(
        self, user_id: str, prefs: UserPreferences | None = None
    ) -> list[FeedRow]:
        ...

    def comment(self, user_id: str, item_id: str, body: str) -> FeedItem:
        ...


class DefaultFeedService:
    def __init__(
        self,
        repo: FeedRepository,
        rules: RuleClassifier,
        github: GitHubService,
        id_factory: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repo = repo
        self._rules = rules
        self._github = github
        self._new_id = id_factory or (lambda: uuid4().hex)
        self._now = clock or (lambda: datetime.now(timezone.utc))

    def ingest(
        self,
        user_id: str,
        event: RawEvent,
        prefs: UserPreferences,
        identity: Identity | None = None,
    ) -> FeedItem:
        verdict = self._rules.classify(event, identity=identity or Identity())
        now = self._now()
        item = FeedItem(
            id=self._new_id(),
            user_id=user_id,
            source=event.source,
            source_ref=event.source_ref,
            rule_tier=verdict.tier,
            type_tag=verdict.type_tag,
            needs_llm=verdict.needs_llm,
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
            is_blocking=event.is_blocking,
            created_at=now,
            raw=event.raw,
        )
        return self._repo.upsert(item)

    def list_feed(
        self, user_id: str, prefs: UserPreferences | None = None
    ) -> list[FeedRow]:
        prefs = prefs or UserPreferences(user_id=user_id)
        now = self._now()
        rows = [
            FeedRow(
                **item.model_dump(),
                tier=effective_tier(item, now=now),
                priority_score=score(item, prefs, now=now),
            )
            for item in self._repo.list_by_user(user_id)
        ]
        rows.sort(key=lambda row: row.priority_score, reverse=True)
        return rows

    def comment(self, user_id: str, item_id: str, body: str) -> FeedItem:
        item = self._repo.get(user_id, item_id)
        if item is None:
            raise ItemNotFound(item_id)
        self._github.comment_on_pull_request(
            _pr_ref_from_source_ref(item.source_ref), body
        )
        return self._repo.mark_handled(
            user_id, item_id, status=FeedStatus.ACTED, at=self._now()
        )
