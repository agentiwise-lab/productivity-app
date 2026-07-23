"""FastAPI app for the feed.

``create_app`` takes its dependencies as arguments, so tests inject fakes and
production injects the real Composio, Supabase and OpenRouter clients. Nothing
in this file reads an environment variable; that is ``composition.py``'s job,
which keeps the routes testable and keeps configuration in one place.

Routes are deliberately thin. Each one authenticates, delegates to a service
contract, and translates an exception into a status code.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Callable

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.auth import AuthMode, build_current_user
from backend.integrations.github import Comment, GitHubService, PRRef, PullRequest
from backend.models.events import RawEvent
from backend.models.feed import FeedItem, FeedRow, UserPreferences
from backend.models.sources import CATALOGUE, Source, SourceInfo
from backend.services.stats import SourceDashboard
from backend.repositories.feed_repository import FeedRepository, InMemoryFeedRepository
from backend.services.actions import (
    ActionFailed,
    DefaultActionService,
    UnknownAction,
)
from backend.services.classifier import DefaultClassificationService
from backend.services.feed import DefaultFeedService, ItemNotFound
from backend.services.ingest import IngestResult, WebhookIngestService
from backend.services.rules import DefaultRuleClassifier

log = logging.getLogger(__name__)


class _UnconfiguredGitHubService:
    """Placeholder for an app built without a GitHub client. Reads return empty;
    writes fail loudly rather than silently doing nothing."""

    def list_notifications(self, since=None) -> list[RawEvent]:
        return []

    def get_pull_request(self, ref: PRRef) -> PullRequest:
        raise NotImplementedError("GitHub client not configured")

    def comment_on_pull_request(self, ref: PRRef, body: str) -> Comment:
        raise NotImplementedError("GitHub client not configured")

    def approve_pull_request(self, ref: PRRef, body: str = "") -> None:
        raise NotImplementedError("GitHub client not configured")


class _UnconfiguredSlackService:
    """Fails loudly. A Slack action that silently did nothing would tell the
    user they had replied when nobody received anything."""

    def reply(self, source_ref: str, text: str, thread_ts: str | None = None):
        raise NotImplementedError("Slack client not configured")

    def mark_read(self, source_ref: str) -> None:
        raise NotImplementedError("Slack client not configured")

    def resolve_identity(self):
        from backend.models.identity import Identity

        return Identity()


class _NullConnectionRepository:
    def mark_status(self, user_id: str, provider: str, status: str) -> None:
        log.warning("connection %s/%s -> %s (not persisted)", user_id, provider, status)

    def identity_for(self, user_id: str, provider: str):
        from backend.models.identity import Identity

        return Identity()


class ActionBody(BaseModel):
    body: str = ""
    action: str = "comment"


class SnoozeBody(BaseModel):
    until: datetime


class RefreshResult(BaseModel):
    ingested: int
    classified: int
    per_source: dict[str, int] = {}
    failed: dict[str, str] = {}


class MeetingOut(BaseModel):
    title: str
    start: datetime
    end: datetime
    conference_url: str | None = None


def create_app(
    github: GitHubService | None = None,
    repo: FeedRepository | None = None,
    *,
    slack: Any | None = None,
    auth_mode: AuthMode = "dev",
    jwt_secret: str | None = None,
    connections: Any | None = None,
    classifier: DefaultClassificationService | None = None,
    connection_service: Any | None = None,
    stats: Any | None = None,
    calendar: Any | None = None,
    sync: Any | None = None,
    verify_webhook: Callable[[bytes, dict], dict] | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    github = github or _UnconfiguredGitHubService()
    repo = repo or InMemoryFeedRepository()
    connections = connections or _NullConnectionRepository()

    feed_service = DefaultFeedService(
        repo=repo, rules=DefaultRuleClassifier(), github=github
    )
    action_service = DefaultActionService(
        repo=repo, github=github, slack=slack or _UnconfiguredSlackService()
    )
    ingest_service = WebhookIngestService(feed=feed_service, connections=connections)
    current_user = build_current_user(auth_mode, jwt_secret)

    app = FastAPI(title="Work feed")
    app.state.feed_service = feed_service
    app.state.ingest_service = ingest_service

    # Only the web build needs this: a native app issues no preflight. Origins
    # are listed explicitly and never "*", because this API is authenticated
    # and a wildcard would let any page a user visits read their feed.
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/feed", response_model=list[FeedRow])
    def get_feed(user_id: str = Depends(current_user)) -> list[FeedRow]:
        return feed_service.list_feed(user_id, UserPreferences(user_id=user_id))

    @app.post("/feed/refresh", response_model=RefreshResult)
    def refresh(user_id: str = Depends(current_user)) -> RefreshResult:
        """Fetch on open, across every polled source.

        GitHub, Linear, Gmail and Calendar are pulled here because their
        triggers either cannot carry the urgent tier or do not exist
        account-wide. Slack arrives by push and is not polled.
        """
        prefs = UserPreferences(user_id=user_id)
        if sync is not None:
            report = sync.refresh(user_id, prefs)
            return RefreshResult(
                ingested=report.ingested,
                classified=report.classified,
                per_source=report.per_source,
                failed=report.failed,
            )

        events = github.list_notifications()
        for event in events:
            feed_service.ingest(user_id, event, prefs)
        classified = 0
        if classifier is not None:
            classified = classifier.classify_pending(user_id).classified
        return RefreshResult(ingested=len(events), classified=classified)

    @app.get("/connections", response_model=list[SourceInfo])
    def get_connections(user_id: str = Depends(current_user)) -> list[SourceInfo]:
        """Every supported source, always, with its live status.

        Sources is a menu rather than a report, so an integration the user has
        not connected still has a row telling them it exists.
        """
        items = repo.list_by_user(user_id)
        if connection_service is None:
            return [
                SourceInfo(source=source, label=label)
                for source, label, _ in CATALOGUE
            ]
        return connection_service.list_sources(user_id, items)

    @app.post("/connections/{provider}/link")
    def post_link(provider: Source, user_id: str = Depends(current_user)) -> dict:
        if connection_service is None:
            raise HTTPException(status_code=503, detail="connections not configured")
        return {"url": connection_service.link_url(user_id, provider)}

    @app.get("/sources/{provider}", response_model=SourceDashboard)
    def get_source_dashboard(
        provider: Source, user_id: str = Depends(current_user)
    ) -> SourceDashboard:
        """What has been going on in one source.

        A different question from the feed's "what needs me now", and the reason
        Sources is a tab rather than a settings page.
        """
        if stats is None:
            raise HTTPException(status_code=503, detail="stats not configured")
        return stats.dashboard(provider, repo.list_by_user(user_id))

    @app.get("/day", response_model=list[MeetingOut])
    def get_day(user_id: str = Depends(current_user)) -> list[MeetingOut]:
        """Read live on every open. A cached schedule is one that will
        eventually be shown after it stopped being true."""
        if calendar is None:
            return []
        try:
            return [
                MeetingOut(
                    title=m.title,
                    start=m.start,
                    end=m.end,
                    conference_url=m.conference_url,
                )
                for m in calendar.today()
            ]
        except Exception:
            log.warning("could not read the calendar", exc_info=True)
            return []

    @app.post("/feed/{item_id}/actions", response_model=FeedItem)
    def post_action(
        item_id: str, payload: ActionBody, user_id: str = Depends(current_user)
    ) -> FeedItem:
        try:
            return action_service.perform(
                user_id, item_id, payload.action, body=payload.body
            )
        except ItemNotFound:
            raise HTTPException(status_code=404, detail="feed item not found")
        except UnknownAction as error:
            raise HTTPException(status_code=400, detail=str(error))
        except ActionFailed as error:
            # 409, not 500: the request was well formed and we simply could not
            # complete it. The app shows the item again rather than retrying.
            raise HTTPException(status_code=409, detail=str(error))

    @app.post("/feed/{item_id}/snooze", response_model=FeedItem)
    def post_snooze(
        item_id: str, payload: SnoozeBody, user_id: str = Depends(current_user)
    ) -> FeedItem:
        try:
            return action_service.snooze(user_id, item_id, payload.until)
        except ItemNotFound:
            raise HTTPException(status_code=404, detail="feed item not found")

    @app.post("/feed/{item_id}/dismiss", response_model=FeedItem)
    def post_dismiss(
        item_id: str, user_id: str = Depends(current_user)
    ) -> FeedItem:
        try:
            return action_service.perform(user_id, item_id, "dismiss")
        except ItemNotFound:
            raise HTTPException(status_code=404, detail="feed item not found")
        except ActionFailed as error:
            raise HTTPException(status_code=409, detail=str(error))

    @app.post("/webhooks/composio", response_model=IngestResult)
    async def composio_webhook(request: Request) -> IngestResult:
        """Unauthenticated by URL and authenticated by signature.

        Anything we simply do not handle still answers 200: Composio retries a
        failed delivery, so returning an error for an unmapped trigger would
        turn a shrug into an endless redelivery loop.
        """
        body = await request.body()
        if verify_webhook is None:
            raise HTTPException(status_code=503, detail="webhooks not configured")
        try:
            envelope = verify_webhook(body, dict(request.headers))
        except Exception:
            log.warning("rejected an unverified webhook", exc_info=True)
            raise HTTPException(status_code=401, detail="invalid signature")

        return ingest_service.handle(envelope)

    return app
