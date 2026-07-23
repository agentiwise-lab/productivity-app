"""Slack via Composio.

Both Slack triggers are account-wide and push in real time, which is verified:
a DM fires `SLACK_DIRECT_MESSAGE_RECEIVED` only, a channel message fires
`SLACK_CHANNEL_MESSAGE_RECEIVED` only, and two messages produced exactly two
events with no cross-firing.

The mappers below carry most of the product's cost control. Every message in
every channel the user belongs to arrives here, and Slack has no mention
trigger, so the decision "was this person actually addressed" is ours to make in
code. Anything that returns None is never stored and never classified, which is
the difference between paying for the user's own asks and paying for an entire
workspace's chatter.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from backend.models.events import RawEvent
from backend.models.feed import Actor
from backend.models.identity import Identity

SLACK_TOOLKIT_VERSION = "20260721_00"

# Subtypes that arrive on the message trigger but are not somebody talking to
# you: joins, leaves, pins, channel topic edits.
_IGNORED_SUBTYPES = {
    "channel_join",
    "channel_leave",
    "channel_topic",
    "channel_purpose",
    "channel_name",
    "pinned_item",
    "unpinned_item",
    "message_changed",
    "message_deleted",
    "bot_add",
    "bot_remove",
    "thread_broadcast_join",
}

# @channel, @here and @everyone address a room, not a person. Counting them as
# a direct ask is how the urgent tier fills with things nobody meant for you.
_BROADCASTS = ("<!channel", "<!here", "<!everyone")

# Automation only matters when it says the user's own work broke.
_FAILURE_WORDS = (
    "fail",
    "failed",
    "failing",
    "error",
    "broke",
    "broken",
    "crash",
    "down",
    "unhealthy",
    "timeout",
    "rollback",
    "reverted",
    "alert",
)


def _ts_to_datetime(ts: str | None) -> datetime | None:
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _mentions(text: str, user_id: str) -> bool:
    """Match a real mention token, never a substring.

    `U_ME` must not match `<@U_MEREDITH>`: a substring check files other
    people's mentions into this user's feed.
    """
    return re.search(rf"<@{re.escape(user_id)}(\|[^>]*)?>", text) is not None


def _is_failure_report(text: str) -> bool:
    lowered = text.lower()
    return any(word in lowered for word in _FAILURE_WORDS)


def _base_event(
    message: dict[str, Any], *, reason: str, context_chip: str, is_blocking: bool
) -> RawEvent:
    channel = message.get("channel", "")
    ts = message.get("ts", "")
    text = message.get("text", "")
    return RawEvent(
        source="slack",
        source_ref=f"slack:{channel}:{ts}",
        reason=reason,
        subject_type="Message",
        # Slack has no subject line, so the message itself is the title. The
        # card clamps it to two lines and the model gets the full text.
        title=text,
        body=text,
        url=_permalink(message),
        repo="",
        context_chip=context_chip,
        actor=Actor(login=message.get("user") or message.get("bot_id") or ""),
        occurred_at=_ts_to_datetime(ts),
        is_blocking=is_blocking,
        raw=message,
    )


def _permalink(message: dict[str, Any]) -> str:
    """Slack's own permalink when it is present, otherwise one built from ids.

    The built form works in the desktop client, which is where a deep link is
    actually followed from a phone.
    """
    if message.get("permalink"):
        return str(message["permalink"])
    team = message.get("team") or message.get("team_id") or ""
    channel = message.get("channel", "")
    ts = str(message.get("ts", "")).replace(".", "")
    return f"https://app.slack.com/client/{team}/{channel}/p{ts}"


def _unusable(message: dict[str, Any]) -> bool:
    if message.get("subtype") in _IGNORED_SUBTYPES:
        return True
    return not (message.get("text") or "").strip()


def direct_message_to_raw_event(
    message: dict[str, Any], *, identity: Identity
) -> RawEvent | None:
    """A DM is always a person addressing this user, so it always counts."""
    if _unusable(message):
        return None
    # Slack delivers the messages the user sends in a DM channel too.
    if identity.slack_user_id and message.get("user") == identity.slack_user_id:
        return None

    reason = "slack_dm"
    if message.get("bot_id"):
        reason = (
            "slack_bot_failure"
            if _is_failure_report(message.get("text", ""))
            else "slack_bot_noise"
        )

    return _base_event(
        message, reason=reason, context_chip="DM", is_blocking=reason == "slack_dm"
    )


def channel_message_to_raw_event(
    message: dict[str, Any],
    *,
    identity: Identity,
    my_threads: set[str] | None = None,
) -> RawEvent | None:
    """A channel message counts only when this user was actually addressed.

    Two ways that happens: an explicit mention of their user id, or a reply in
    a thread they have posted in. Everything else is somebody else's
    conversation and never reaches storage or the model.
    """
    if _unusable(message):
        return None
    if not identity.slack_user_id:
        # Without the user's own id there is no way to tell a mention from
        # chatter. Surfacing nothing beats guessing.
        return None
    if message.get("user") == identity.slack_user_id:
        return None

    text = message.get("text", "")
    if text.startswith(_BROADCASTS) or any(token in text for token in _BROADCASTS):
        return None

    mentioned = _mentions(text, identity.slack_user_id)
    thread_ts = message.get("thread_ts")
    in_my_thread = bool(thread_ts and thread_ts in (my_threads or set()))
    if not mentioned and not in_my_thread:
        return None

    if message.get("bot_id"):
        reason = (
            "slack_bot_failure" if _is_failure_report(text) else "slack_bot_noise"
        )
    elif mentioned:
        reason = "slack_mention"
    else:
        reason = "slack_thread_reply"

    channel_name = message.get("channel_name") or message.get("channel", "")
    chip = f"#{channel_name}" if not channel_name.startswith("#") else channel_name

    return _base_event(
        message,
        reason=reason,
        context_chip=chip,
        is_blocking=reason in {"slack_mention", "slack_thread_reply"},
    )
