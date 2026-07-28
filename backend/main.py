"""FastAPI app for the feed.

``create_app`` takes its dependencies as arguments, so tests inject fakes and
production injects the real Composio, Supabase and OpenRouter clients. Nothing
in this file reads an environment variable; that is ``composition.py``'s job,
which keeps the routes testable and keeps configuration in one place.

Routes are deliberately thin. Each one authenticates, delegates to a service
contract, and translates an exception into a status code.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, tzinfo
from typing import Any, Callable, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.auth import AuthMode, build_current_user
from backend.api.auth_router import build_auth_router
from backend.integrations.github import Comment, GitHubService, PRRef, PullRequest
from backend.tokens import TokenCodec
from backend.models.events import RawEvent
from backend.models.feed import FeedItem, FeedRow, UserPreferences
from backend.models.profile import Profile
from backend.models.sources import CATALOGUE, Source, SourceInfo
from backend.services.stats import SourceDashboard
from backend.repositories.feed_repository import FeedRepository, InMemoryFeedRepository
from backend.services.actions import (
    ActionFailed,
    DefaultActionService,
    UnknownAction,
)
from backend.services.classifier import DefaultClassificationService
from backend.services.connections import MissingAuthConfig
from backend.services.feed import DefaultFeedService, ItemNotFound
from backend.services.ingest import IngestResult, WebhookIngestService
from backend.services.profile import UserNotFound
from backend.services.rules import DefaultRuleClassifier

log = logging.getLogger(__name__)


def _parse_tz(name: str | None) -> tzinfo:
    """A client-supplied IANA zone name, or UTC when absent or unrecognised.

    Never raises: a bad zone from a client is a fall-back to UTC, not a 500."""
    if not name:
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        return timezone.utc


def _on_home_refs(repo: FeedRepository, user_id: str) -> set[str]:
    """The source_refs Later must exclude: everything currently stored for the
    feed.

    Noise-tier items now render in To-dos (at the bottom), so they are on Home and
    must be excluded from Later too — otherwise a model-rated-noise item would show
    in both places. Later stays the residual: the live provider set minus whatever
    the refresh already pulled into the feed (deterministic noise, never stored, is
    the bulk of it)."""
    return {item.source_ref for item in repo.list_by_user(user_id)}


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

    def request_changes_on_pull_request(self, ref: PRRef, body: str) -> None:
        raise NotImplementedError("GitHub client not configured")

    def assign_to_me(self, ref: PRRef) -> None:
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


class _StaticIntegrations:
    """Adapts a fixed set of services to the per-user factory interface, by
    returning the same one for every user. This is the test and single-service
    path; production passes a real ``ComposioIntegrations`` that mints each
    user's own."""

    def __init__(self, github=None, slack=None, linear=None, gmail=None, calendar=None):
        self._m = {
            "github": github,
            "slack": slack,
            "linear": linear,
            "gmail": gmail,
            "calendar": calendar,
        }

    def github(self, user_id: str):
        return self._m["github"]

    def slack(self, user_id: str):
        return self._m["slack"]

    def linear(self, user_id: str):
        return self._m["linear"]

    def gmail(self, user_id: str):
        return self._m["gmail"]

    def calendar(self, user_id: str):
        return self._m["calendar"]


class _NullConnectionRepository:
    def mark_status(self, user_id: str, provider: str, status: str) -> None:
        log.warning("connection %s/%s -> %s (not persisted)", user_id, provider, status)

    def identity_for(self, user_id: str, provider: str):
        from backend.models.identity import Identity

        return Identity()


class ActionBody(BaseModel):
    """The action name is required, deliberately.

    It used to default to ``comment``, which meant a client that forgot to send
    one had every button perform the same thing: Approve posted a comment and
    left the review outstanding. A missing name is now a 422 rather than a
    quiet wrong answer.
    """

    action: str
    body: str = ""


class SnoozeBody(BaseModel):
    until: datetime


class ProfileBody(BaseModel):
    """PATCH /me. Both fields optional, and `None` means different things.

    For `name`, `None` is a value: it clears the name back to no-name, which is
    what the You tab's blank-and-save does. For `notify_level` there is no such
    thing as "no level", so `None` can only mean "not part of this request".

    The asymmetry is why a sentinel is needed rather than a shared rule: without
    it, editing your display name would silently reset your notification
    setting. `model_fields_set` is what tells the two apart.
    """

    name: str | None = None
    notify_level: str | None = None


class DeviceBody(BaseModel):
    token: str
    #: Constrained here as well as by the column's check constraint, so a typo
    #: is a 422 naming the field rather than a 500 out of Postgres.
    platform: Literal["ios", "android"]


class DeviceTokenBody(BaseModel):
    """Unregister takes the token in the body rather than the path.

    An Expo token is literally `ExponentPushToken[...]`, and square brackets are
    reserved characters RFC 3986 does not allow unencoded in a path segment. In
    a body the value needs no encoding, and nothing has to agree about it.
    """

    token: str


class RefreshResult(BaseModel):
    ingested: int
    classified: int
    #: Ingested but not yet classified when the refresh returned. The app shows
    #: "still classifying N" instead of reading an incomplete feed as finished.
    held: int = 0
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
    integrations: Any | None = None,
    auth_mode: AuthMode = "dev",
    token_codec: TokenCodec | None = None,
    auth_service: Any | None = None,
    connections: Any | None = None,
    classifier: DefaultClassificationService | None = None,
    connection_service: Any | None = None,
    profile_service: Any | None = None,
    device_tokens: Any | None = None,
    on_item_ready: Callable[[str, Any], None] | None = None,
    stats: Any | None = None,
    later: Any | None = None,
    calendar: Any | None = None,
    linear: Any | None = None,
    gmail: Any | None = None,
    sync: Any | None = None,
    verify_webhook: Callable[[bytes, dict], dict] | None = None,
    cors_origins: list[str] | None = None,
) -> FastAPI:
    github = github or _UnconfiguredGitHubService()
    repo = repo or InMemoryFeedRepository()
    connections = connections or _NullConnectionRepository()

    # Production passes the per-user factory; tests inject individual fakes,
    # which are wrapped so the services see one interface either way. Absent
    # providers stay absent, so an action with no client is refused rather than
    # quietly skipped.
    resolved_integrations = integrations or _StaticIntegrations(
        github=github,
        slack=slack or _UnconfiguredSlackService(),
        linear=linear,
        calendar=calendar,
        gmail=gmail,
    )
    feed_service = DefaultFeedService(
        repo=repo, rules=DefaultRuleClassifier(), integrations=resolved_integrations
    )
    action_service = DefaultActionService(
        repo=repo, integrations=resolved_integrations
    )
    # Classifies the single pushed item after the 200 ack (Decision C). A small
    # pool keeps the webhook response off the model's latency.
    webhook_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="webhook")
    ingest_service = WebhookIngestService(
        feed=feed_service,
        connections=connections,
        classifier=classifier,
        background=lambda work: webhook_pool.submit(work),
        # Redis stores publish a change signal so open screens append live; the
        # in-memory/Supabase stores have no pub/sub and this is simply absent.
        publish=getattr(repo, "publish_change", None),
        # The same "this item is renderable" moment, for a phone rather than an
        # open screen. A plain callable, so ingest never imports the push stack.
        on_item_ready=on_item_ready,
    )
    current_user = build_current_user(auth_mode, token_codec)

    app = FastAPI(title="Work feed")
    app.state.feed_service = feed_service
    app.state.ingest_service = ingest_service

    # Unauthenticated by design: these routes are how a user gets a token in the
    # first place. Present only when an auth service is wired (dev/test builds
    # can omit it and drive the app with the X-User-Id header).
    if auth_service is not None:
        app.include_router(build_auth_router(auth_service))

    # Only the web build needs this: a native app issues no preflight. Origins
    # are listed explicitly and never "*", because this API is authenticated
    # and a wildcard would let any page a user visits read their feed.
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(cors_origins),
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
            allow_headers=["*"],
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/feed", response_model=list[FeedRow])
    def get_feed(
        tz: str | None = None, user_id: str = Depends(current_user)
    ) -> list[FeedRow]:
        # The client sends its IANA zone (e.g. "Asia/Kolkata"); "today" for a
        # Linear due date is that calendar day, not UTC's. Unknown/absent -> UTC.
        return feed_service.list_feed(
            user_id, UserPreferences(user_id=user_id), tz=_parse_tz(tz)
        )

    @app.get("/feed/stream")
    def feed_stream(user_id: str = Depends(current_user)) -> StreamingResponse:
        """A live signal that this user's feed changed.

        When a trigger lands while the app is open, the webhook publishes to the
        user's Redis channel and this stream forwards a lightweight ``changed``
        event; the client then does one cheap GET /feed (a single Redis read),
        so the item appears without a manual refresh and without any polling.
        Only the Redis store has pub/sub; other stores answer 503.
        """
        pubsub_factory = getattr(repo, "pubsub", None)
        channel_for = getattr(repo, "events_channel", None)
        if pubsub_factory is None or channel_for is None:
            raise HTTPException(status_code=503, detail="stream not available")

        def events():
            ps = pubsub_factory()
            ps.subscribe(channel_for(user_id))
            try:
                # An initial event so the client knows the stream is open.
                yield "event: ready\ndata: {}\n\n"
                while True:
                    # Blocks up to 20s, then a heartbeat keeps the connection
                    # alive through the proxy. No busy-polling.
                    message = ps.get_message(
                        ignore_subscribe_messages=True, timeout=20.0
                    )
                    if message and message.get("type") == "message":
                        yield "event: changed\ndata: {}\n\n"
                    else:
                        yield ": keepalive\n\n"
            finally:
                try:
                    ps.close()
                except Exception:
                    pass

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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
                held=report.held,
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
        try:
            return {"url": connection_service.link_url(user_id, provider)}
        except MissingAuthConfig:
            # A deployment gap, not a user error: this toolkit has no auth config.
            raise HTTPException(
                status_code=503, detail=f"{provider.value} is not available to connect"
            )

    @app.get("/connections/{provider}/status", response_model=SourceInfo)
    def get_connection_status(
        provider: Source, user_id: str = Depends(current_user)
    ) -> SourceInfo:
        """Reconcile one source against Composio after the user returns from
        consent. The mobile app polls this until it reads connected."""
        if connection_service is None:
            raise HTTPException(status_code=503, detail="connections not configured")
        return connection_service.status(user_id, provider)

    @app.delete("/connections/{provider}", status_code=204)
    def delete_connection(
        provider: Source, user_id: str = Depends(current_user)
    ) -> None:
        if connection_service is None:
            raise HTTPException(status_code=503, detail="connections not configured")
        connection_service.disconnect(user_id, provider)

    @app.get("/me", response_model=Profile)
    def get_me(user_id: str = Depends(current_user)) -> Profile:
        if profile_service is None:
            raise HTTPException(status_code=503, detail="profile not configured")
        try:
            return profile_service.get(user_id)
        except UserNotFound:
            raise HTTPException(status_code=404, detail="user not found")

    @app.patch("/me", response_model=Profile)
    def patch_me(
        body: ProfileBody, user_id: str = Depends(current_user)
    ) -> Profile:
        if profile_service is None:
            raise HTTPException(status_code=503, detail="profile not configured")
        # Only the fields the client actually sent. A name edit must not carry
        # a null notify_level along with it and reset the setting.
        sent = body.model_fields_set
        try:
            profile = profile_service.get(user_id)
            if "name" in sent:
                profile = profile_service.set_name(user_id, body.name)
            if "notify_level" in sent and body.notify_level is not None:
                profile = profile_service.set_notify_level(user_id, body.notify_level)
            return profile
        except UserNotFound:
            raise HTTPException(status_code=404, detail="user not found")
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error))

    @app.post("/devices", status_code=204)
    def register_device(
        body: DeviceBody, user_id: str = Depends(current_user)
    ) -> None:
        """Point this device at this account.

        Called on every app launch rather than once at signup, because an Expo
        token rotates on reinstall and on some restores, so the write has to be
        idempotent by design instead of by luck.
        """
        if device_tokens is None:
            raise HTTPException(status_code=503, detail="devices not configured")
        device_tokens.upsert(user_id, body.token, body.platform)

    @app.post("/devices/unregister", status_code=204)
    def unregister_device(
        body: DeviceTokenBody, user_id: str = Depends(current_user)
    ) -> None:
        """Stop sending here: sign-out, or notifications switched off.

        Deleting a token that is already gone is deliberately not an error. Both
        callers race by nature, and so does the sweep that reacts to Expo
        reporting a device as dead.
        """
        if device_tokens is None:
            raise HTTPException(status_code=503, detail="devices not configured")
        device_tokens.delete(body.token)

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
        return stats.dashboard(user_id, provider, repo.list_by_user(user_id))

    @app.get("/later")
    def stream_later_all(
        limit: int = 200, user_id: str = Depends(current_user)
    ) -> StreamingResponse:
        """Every source at once, streamed as each one answers.

        One connection rather than one per source. The client keeps all the
        rows and filters by source locally, so the strip switches instantly
        instead of starting a fresh ten-second fetch on every tap.
        """
        if later is None:
            raise HTTPException(status_code=503, detail="later not configured")

        on_home = _on_home_refs(repo, user_id)

        def events():
            try:
                for batch in later.stream_all(user_id, on_home=on_home, limit=limit):
                    payload = json.dumps([row.model_dump(mode="json") for row in batch])
                    yield f"event: rows\ndata: {payload}\n\n"
            except Exception:
                log.warning("later stream failed", exc_info=True)
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/later/{provider}")
    def stream_later(
        provider: Source, limit: int = 200, user_id: str = Depends(current_user)
    ) -> StreamingResponse:
        """What arrived from one source and did not need you, streamed.

        Server-sent events rather than one response: pulling every unread
        message takes most of a minute, and a list that appears only after all
        of it reads as broken. Each event is a batch of rows, and the client
        appends as they land.

        Nothing here is stored. This asks the provider what is currently
        unread, unanswered or open, so it cannot drift from what the user sees
        in Gmail or Slack the way a saved copy would.
        """
        if later is None:
            raise HTTPException(status_code=503, detail="later not configured")

        # Home is the exclusion set: an item on both screens would be the two
        # of them disagreeing about the same message.
        on_home = _on_home_refs(repo, user_id)

        def events():
            try:
                for batch in later.stream(
                    user_id, provider, on_home=on_home, limit=limit
                ):
                    payload = json.dumps([row.model_dump(mode="json") for row in batch])
                    yield f"event: rows\ndata: {payload}\n\n"
            except Exception:
                log.warning("later stream failed", exc_info=True)
            yield "event: done\ndata: {}\n\n"

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/day", response_model=list[MeetingOut])
    def get_day(user_id: str = Depends(current_user)) -> list[MeetingOut]:
        """Read live on every open. A cached schedule is one that will
        eventually be shown after it stopped being true.

        Reads the calendar through the per-user factory, exactly as the feed
        does. The endpoint used to read a bare ``calendar`` closure that
        composition never wired, so it was always ``None`` and every day
        returned empty while the feed showed calendar items fine.
        """
        cal = resolved_integrations.calendar(user_id)
        if cal is None:
            return []
        try:
            return [
                MeetingOut(
                    title=m.title,
                    start=m.start,
                    end=m.end,
                    conference_url=m.conference_url,
                )
                for m in cal.day_window()
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

        # An authentic but poison event (a non-UUID user_id that makes the DB
        # raise, an unforeseen payload shape) must never become a 500: Composio
        # redelivers a failed webhook, so a 500 turns one bad event into an
        # endless redelivery loop. Anything past the signature check answers 200.
        try:
            return ingest_service.handle(envelope)
        except Exception:
            log.warning("ingest failed; acknowledging to stop redelivery", exc_info=True)
            return IngestResult(handled=False, reason="ingest_error")

    return app
