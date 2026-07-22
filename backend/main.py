"""FastAPI app for the feed.

``create_app`` takes its dependencies as arguments so tests can inject a fake
GitHub service and a fresh repository. The tracer has no signup: the user is read
from an ``X-User-Id`` header and defaults to a single dev user. Real auth (a
Supabase-issued identity) replaces ``current_user`` later, with no change to the
routes. Isolation still holds because every service call is scoped to the id.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from backend.integrations.github import GitHubService, PRRef, PullRequest, Comment
from backend.models.events import RawEvent
from backend.models.feed import FeedItem
from backend.repositories.feed_repository import FeedRepository, InMemoryFeedRepository
from backend.services.classification import DefaultClassificationService
from backend.services.feed import DefaultFeedService, ItemNotFound
from backend.services.priority import DefaultPriorityService


class _UnconfiguredGitHubService:
    """Placeholder used by the module-level app until a real GitHub App client is
    wired. Reads return empty; write actions fail loudly rather than silently."""

    def list_notifications(self, since=None) -> list[RawEvent]:
        return []

    def get_pull_request(self, ref: PRRef) -> PullRequest:
        raise NotImplementedError("GitHub App client not configured")

    def comment_on_pull_request(self, ref: PRRef, body: str) -> Comment:
        raise NotImplementedError("GitHub App client not configured")


class CommentBody(BaseModel):
    body: str


def current_user(x_user_id: str = Header(default="me")) -> str:
    return x_user_id


def create_app(
    github: GitHubService, repo: FeedRepository | None = None
) -> FastAPI:
    repo = repo or InMemoryFeedRepository()
    feed_service = DefaultFeedService(
        repo=repo,
        classifier=DefaultClassificationService(),
        prioritizer=DefaultPriorityService(),
        github=github,
    )

    app = FastAPI(title="Work Feed (GitHub tracer)")
    # Exposed so the poller/webhook path (and tests) can ingest events.
    app.state.feed_service = feed_service

    @app.get("/feed", response_model=list[FeedItem])
    def get_feed(user_id: str = Depends(current_user)) -> list[FeedItem]:
        return feed_service.list_feed(user_id)

    @app.post("/feed/{item_id}/actions", response_model=FeedItem)
    def post_action(
        item_id: str, payload: CommentBody, user_id: str = Depends(current_user)
    ) -> FeedItem:
        try:
            return feed_service.comment(user_id, item_id, payload.body)
        except ItemNotFound:
            raise HTTPException(status_code=404, detail="feed item not found")

    return app


app = create_app(github=_UnconfiguredGitHubService())
