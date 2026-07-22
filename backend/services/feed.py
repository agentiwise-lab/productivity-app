"""Feed orchestration: the spine that ties the tracer together.

``ingest`` turns a RawEvent into a stored, classified, scored FeedItem.
``list_feed`` returns a user's items ranked. ``comment`` acts from the feed back
into GitHub. It depends only on the other services' contracts, never their
implementations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, Protocol
from uuid import uuid4

from backend.integrations.github import GitHubService, PRRef
from backend.models.events import RawEvent
from backend.models.feed import FeedItem, FeedStatus, UserPreferences
from backend.repositories.feed_repository import FeedRepository
from backend.services.classification import ClassificationService
from backend.services.priority import PriorityService


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
        self, user_id: str, event: RawEvent, prefs: UserPreferences
    ) -> FeedItem:
        ...

    def list_feed(self, user_id: str) -> list[FeedItem]:
        ...

    def comment(self, user_id: str, item_id: str, body: str) -> FeedItem:
        ...


class DefaultFeedService:
    def __init__(
        self,
        repo: FeedRepository,
        classifier: ClassificationService,
        prioritizer: PriorityService,
        github: GitHubService,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._repo = repo
        self._classifier = classifier
        self._prioritizer = prioritizer
        self._github = github
        self._new_id = id_factory or (lambda: uuid4().hex)

    def ingest(
        self, user_id: str, event: RawEvent, prefs: UserPreferences
    ) -> FeedItem:
        item = FeedItem(
            id=self._new_id(),
            user_id=user_id,
            source=event.source,
            source_ref=event.source_ref,
            action_type=self._classifier.classify(event),
            title=event.title,
            url=event.url,
            repo=event.repo,
            actors=[event.actor] if event.actor else [],
            is_blocking=event.is_blocking,
            created_at=datetime.now(timezone.utc),
        )
        item.priority_score = self._prioritizer.score(item, prefs)
        return self._repo.upsert(item)

    def list_feed(self, user_id: str) -> list[FeedItem]:
        items = self._repo.list_by_user(user_id)
        return sorted(items, key=lambda i: i.priority_score, reverse=True)

    def comment(self, user_id: str, item_id: str, body: str) -> FeedItem:
        item = self._repo.get(user_id, item_id)
        if item is None:
            raise ItemNotFound(item_id)
        self._github.comment_on_pull_request(
            _pr_ref_from_source_ref(item.source_ref), body
        )
        acted = item.model_copy(update={"status": FeedStatus.ACTED})
        return self._repo.upsert(acted)
