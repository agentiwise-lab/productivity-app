"""Composio webhook ingest.

One endpoint receives every trigger for every user, so the first job here is
routing, and it is the job with the worst failure mode: an event filed under the
wrong id is not a bug report, it is one person reading another person's
messages.

The rule that prevents it: **the user id comes from ``metadata.user_id`` and
from nowhere else.** ``data`` is the provider's own payload, and its ``user``
field is the *sender*, not the recipient. Anything that cannot name its user is
dropped.

Signature verification happens at the route, before an envelope reaches this
service, so everything below can treat the envelope as authentic but still not
as well-formed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from pydantic import BaseModel

from backend.integrations.composio_github import notification_to_raw_event
from backend.models.events import RawEvent
from backend.models.feed import Actor, UserPreferences
from backend.models.identity import Identity
from backend.services.feed import FeedService

log = logging.getLogger(__name__)

TRIGGER_MESSAGE = "composio.trigger.message"
CONNECTION_EXPIRED = "composio.connected_account.expired"


class ConnectionRepository(Protocol):
    def mark_status(self, user_id: str, provider: str, status: str) -> None:
        ...

    def identity_for(self, user_id: str, provider: str) -> Identity:
        ...


class IngestResult(BaseModel):
    handled: bool
    reason: str
    item_id: str | None = None


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _issue_to_raw_event(data: dict[str, Any]) -> RawEvent | None:
    """GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER delivers a GitHub issue object.

    Unlike the notification trigger this one carries the body and the labels,
    which is exactly what section 3.1 needs to judge an assigned issue: the
    raiser's own stated urgency, not a default.
    """
    repo = (data.get("repository") or {}).get("full_name", "")
    number = data.get("number")
    if not repo or number is None:
        return None

    return RawEvent(
        source="github",
        source_ref=f"{repo}#{number}",
        reason="assign",
        subject_type="Issue",
        title=data.get("title") or "",
        url=data.get("html_url") or f"https://github.com/{repo}/issues/{number}",
        repo=repo,
        actor=Actor(login=(data.get("user") or {}).get("login", "")),
        labels=[
            label.get("name", "") if isinstance(label, dict) else str(label)
            for label in (data.get("labels") or [])
        ],
        milestone_due=_parse_time((data.get("milestone") or {}).get("due_on")),
        body=data.get("body"),
        occurred_at=_parse_time(data.get("updated_at") or data.get("created_at")),
        is_blocking=True,  # somebody put this on you by name
        raw=data,
    )


def _notification_to_raw_event(data: dict[str, Any]) -> RawEvent | None:
    if not (data.get("repository") or {}).get("full_name"):
        return None
    event = notification_to_raw_event(data)
    event.occurred_at = _parse_time(data.get("updated_at"))
    return event


# Trigger slug -> payload mapper. Verified against the live trigger instances.
# An unlisted slug is ignored rather than guessed at.
_MAPPERS: dict[str, Callable[[dict], RawEvent | None]] = {
    "GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER": _notification_to_raw_event,
    "GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER": _issue_to_raw_event,
}

# Trigger slug prefix -> the provider whose connection it belongs to.
_PROVIDERS = {"GITHUB": "github", "SLACK": "slack"}


class WebhookIngestService:
    def __init__(
        self,
        feed: FeedService,
        connections: ConnectionRepository,
        prefs_for: Callable[[str], UserPreferences] | None = None,
    ) -> None:
        self._feed = feed
        self._connections = connections
        self._prefs_for = prefs_for or (lambda user_id: UserPreferences(user_id=user_id))

    def handle(self, envelope: dict[str, Any]) -> IngestResult:
        event_type = envelope.get("type", "")

        if event_type == CONNECTION_EXPIRED:
            return self._handle_expired(envelope)
        if event_type != TRIGGER_MESSAGE:
            log.info("ignoring webhook of type %r", event_type)
            return IngestResult(handled=False, reason="unknown_event_type")

        metadata = envelope.get("metadata") or {}
        user_id = metadata.get("user_id")
        if not user_id:
            # Never fall back to anything inside `data`. See the module docstring.
            log.warning("dropping trigger event with no metadata.user_id")
            return IngestResult(handled=False, reason="no_user")

        slug = metadata.get("trigger_slug", "")
        mapper = _MAPPERS.get(slug)
        if mapper is None:
            log.info("no mapper for trigger %r", slug)
            return IngestResult(handled=False, reason="unmapped_trigger")

        try:
            event = mapper(envelope.get("data") or {})
        except Exception:
            log.warning("failed to map trigger %r", slug, exc_info=True)
            return IngestResult(handled=False, reason="malformed_payload")

        if event is None:
            log.warning("trigger %r carried an unusable payload", slug)
            return IngestResult(handled=False, reason="malformed_payload")

        item = self._feed.ingest(
            user_id,
            event,
            self._prefs_for(user_id),
            self._connections.identity_for(user_id, event.source),
        )
        return IngestResult(handled=True, reason="ingested", item_id=item.id)

    def _handle_expired(self, envelope: dict[str, Any]) -> IngestResult:
        """A dead connection must be visible. Left unrecorded, that source
        simply goes quiet, and a quiet feed reads as 'nothing needs me' when it
        means 'we lost access' (plan 6.4)."""
        data = envelope.get("data") or {}
        user_id = data.get("user_id")
        provider = (data.get("toolkit") or {}).get("slug", "")
        if not user_id or not provider:
            return IngestResult(handled=False, reason="malformed_payload")

        self._connections.mark_status(user_id, provider, "expired")
        log.warning("connection expired: user=%s provider=%s", user_id, provider)
        return IngestResult(handled=True, reason="connection_expired")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
