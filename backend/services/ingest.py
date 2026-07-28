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

from backend.integrations.calendar import starting_soon_to_raw_event
from backend.integrations.composio_github import notification_to_raw_event
from backend.integrations.gmail import message_to_raw_event
from backend.integrations.google_docs import (
    drive_comment_to_raw_event,
    drive_share_to_raw_event,
)
from backend.integrations.linear import (
    comment_event_to_raw_event,
    issue_to_raw_event as _linear_issue_to_raw_event,
)
from backend.integrations.slack import (
    channel_message_to_raw_event,
    direct_message_to_raw_event,
)
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
#
# The GitHub mappers ignore identity; the Slack ones cannot, because Slack has
# no mention trigger and "was this person addressed" is decided in our code.
_MAPPERS: dict[str, Callable[..., RawEvent | None]] = {
    "GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER": (
        lambda data, identity, threads: _notification_to_raw_event(data)
    ),
    "GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER": (
        lambda data, identity, threads: _issue_to_raw_event(data)
    ),
    "SLACK_DIRECT_MESSAGE_RECEIVED": (
        lambda data, identity, threads: direct_message_to_raw_event(
            data, identity=identity
        )
    ),
    "SLACK_CHANNEL_MESSAGE_RECEIVED": (
        lambda data, identity, threads: channel_message_to_raw_event(
            data, identity=identity, my_threads=threads
        )
    ),
    # Gmail and Calendar have real triggers; Linear does not (its triggers need a
    # team_id we do not have at connect time) and Google Docs has none at all —
    # both stay poll-only. The Gmail mapper also produces Google Docs items when
    # the sender is a Docs notification address.
    "GMAIL_NEW_GMAIL_MESSAGE": (
        lambda data, identity, threads: message_to_raw_event(data)
    ),
    "GOOGLECALENDAR_EVENT_STARTING_SOON_TRIGGER": (
        lambda data, identity, threads: starting_soon_to_raw_event(data)
    ),
    # Linear's triggers are team-scoped; the mappers filter to this user. Issue
    # creation keeps only issues assigned to them (deterministic, by due date);
    # comments keep others' comments (LLM-in-a-band). Both verified against a
    # live payload capture (2026-07-26).
    "LINEAR_ISSUE_CREATED_TRIGGER": (
        # Skip entirely without a resolved id: a None assignee filter would let
        # every team-created issue through, not just this user's.
        lambda data, identity, threads: (
            _linear_issue_to_raw_event(data, assignee_id=identity.linear_user_id)
            if getattr(identity, "linear_user_id", None)
            else None
        )
    ),
    "LINEAR_COMMENT_EVENT_TRIGGER": (
        lambda data, identity, threads: comment_event_to_raw_event(
            data, identity=identity
        )
    ),
    # Google Drive: native comment/share triggers, replacing the Gmail sniffing.
    "GOOGLEDRIVE_COMMENT_ADDED_TRIGGER": (
        lambda data, identity, threads: drive_comment_to_raw_event(data)
    ),
    "GOOGLEDRIVE_FILE_SHARED_PERMISSIONS_ADDED": (
        lambda data, identity, threads: drive_share_to_raw_event(data)
    ),
}

# Trigger slug prefix -> the provider whose identity the mapper needs. Gmail and
# Calendar mappers ignore identity, but the prefix must still resolve so the
# connection lookup does not blank.
_SLUG_PROVIDER = {
    "GITHUB": "github",
    "SLACK": "slack",
    "GMAIL": "gmail",
    "GOOGLECALENDAR": "calendar",
    "LINEAR": "linear",
    # Drive triggers belong to the Docs source's (now Drive) connection.
    "GOOGLEDRIVE": "google_docs",
}

# Trigger slug prefix -> the provider whose connection it belongs to.
_PROVIDERS = {
    "GITHUB": "github",
    "SLACK": "slack",
    "GMAIL": "gmail",
    "GOOGLECALENDAR": "calendar",
    "LINEAR": "linear",
    "GOOGLEDRIVE": "google_docs",
}


class WebhookIngestService:
    def __init__(
        self,
        feed: FeedService,
        connections: ConnectionRepository,
        prefs_for: Callable[[str], UserPreferences] | None = None,
        threads_for: Callable[[str], set[str]] | None = None,
        classifier: Any | None = None,
        background: Callable[[Callable[[], Any]], Any] | None = None,
        publish: Callable[[str], None] | None = None,
        on_item_ready: Callable[[str, Any], None] | None = None,
    ) -> None:
        self._feed = feed
        self._connections = connections
        # Signals open clients (via the SSE stream) that this user's feed changed,
        # so a trigger landing while the app is open appends without a poll.
        self._publish = publish or (lambda user_id: None)
        # The same moment, for a phone rather than an open screen: this item is
        # renderable and has a real tier. What happens next is the push
        # service's business, so this is a plain callable and the push module is
        # never imported here.
        self._on_item_ready = on_item_ready or (lambda user_id, item: None)
        self._prefs_for = prefs_for or (lambda user_id: UserPreferences(user_id=user_id))
        # Threads the user has posted in. Plan 3.10 accepts the limitation:
        # threads joined before installing are invisible until someone mentions
        # you, because Slack gives us no way to learn about them.
        self._threads_for = threads_for or (lambda user_id: set())
        # Classifying the single pushed item, off the delivery's critical path:
        # Composio retry-storms on a slow HTTP response, so the item is
        # classified *after* the 200 goes out, not before. It is held (invisible)
        # by the read-time filter until that ~1s classify lands, so it still
        # appears already-classified, never as a placeholder.
        self._classifier = classifier
        self._background = background or (lambda work: work())

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

        provider = _SLUG_PROVIDER.get(slug.split("_", 1)[0], "")
        identity = self._connections.identity_for(user_id, provider)
        threads = self._threads_for(user_id)

        try:
            event = mapper(envelope.get("data") or {}, identity, threads)
        except Exception:
            log.warning("failed to map trigger %r", slug, exc_info=True)
            return IngestResult(handled=False, reason="malformed_payload")

        if event is None:
            # Not a failure. Most Slack traffic lands here by design: it was
            # somebody else's conversation, and dropping it before storage is
            # what keeps the feed and the model bill about this user.
            log.debug("trigger %r produced no item", slug)
            return IngestResult(handled=False, reason="not_for_this_user")

        item = self._feed.ingest(user_id, event, self._prefs_for(user_id), identity)
        if item is None:
            # Settled as noise by the rules and not stored.
            return IngestResult(handled=False, reason="not_for_this_user")
        self._classify_soon(user_id, item)
        return IngestResult(handled=True, reason="ingested", item_id=item.id)

    def _classify_soon(self, user_id: str, item) -> None:
        """Classify this one item just after the ack, if it needs the model.

        Publishes a change signal once the item is renderable: immediately for a
        deterministic item, or after the model lands for a banded one — so an open
        screen appends it only when it has a real tier, never as a placeholder."""
        if self._classifier is None or not item.needs_llm or item.llm_tier is not None:
            self._publish(user_id)  # deterministic / already-judged: ready now
            self._ready(user_id, item)
            return
        try:
            self._background(
                lambda: (
                    self._classifier.classify_item(user_id, item),
                    self._publish(user_id),
                    self._ready(user_id, item),
                )
            )
        except Exception:
            # A classify that could not even be scheduled must not fail the
            # webhook: the item is still ingested and the next refresh sweeps it.
            log.warning("could not schedule classify for %s", item.id, exc_info=True)

    def _ready(self, user_id: str, item) -> None:
        """Offer a renderable item to the push hook, defensively.

        The hook already promises not to raise, and this catches anyway. The
        deterministic branch above has no ``try`` around it, so an escape would
        propagate out of ``handle()`` and be reported as an ingest failure for an
        item that was in fact stored. Composio redelivers a failed webhook, which
        turns that into a redelivery loop over a notification.
        """
        try:
            self._on_item_ready(user_id, item)
        except Exception:
            log.warning("push hook failed for %s", item.id, exc_info=True)

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
