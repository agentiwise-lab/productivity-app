"""Acting on Slack, through Composio.

Contract first: callers import ``SlackService`` and never this implementation.

Everything here is a write somebody else sees, so the parsing is strict. A
``source_ref`` that cannot be read raises instead of falling back to a default
channel, because the failure mode of guessing is a private reply posted
somewhere public.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from backend.integrations.slack import (
    SLACK_TOOLKIT_VERSION,
    channel_message_to_raw_event,
    direct_message_to_raw_event,
)
from backend.models.events import RawEvent
from backend.models.identity import Identity

log = logging.getLogger(__name__)

#: How far back an unread backfill reaches. Matches the feed's own retention,
#: so the app never shows something it would immediately drop.
BACKFILL = timedelta(days=30)

#: Conversations scanned per refresh. Beyond this the call cost grows without
#: the feed getting more useful: what matters is unread, and unread is rare.
MAX_CONVERSATIONS = 12
MAX_PER_CONVERSATION = 20


class SlackMessageRef(BaseModel):
    channel: str
    ts: str


class SlackService(Protocol):
    def reply(
        self, source_ref: str, text: str, thread_ts: str | None = None
    ) -> SlackMessageRef:
        ...

    def mark_read(self, source_ref: str) -> None:
        ...

    def unread(
        self, identity: Identity, now: datetime | None = None
    ) -> list[RawEvent]:
        ...

    def resolve_identity(self) -> Identity:
        ...


def parse_source_ref(source_ref: str) -> SlackMessageRef:
    """"slack:<channel>:<ts>" and nothing else."""
    parts = source_ref.split(":")
    if len(parts) != 3 or parts[0] != "slack" or not parts[1] or not parts[2]:
        raise ValueError(f"not a Slack source_ref: {source_ref!r}")
    return SlackMessageRef(channel=parts[1], ts=parts[2])


class ComposioSlackService:
    def __init__(
        self, composio: Any, user_id: str, version: str = SLACK_TOOLKIT_VERSION
    ) -> None:
        self._composio = composio
        self._user_id = user_id
        self._version = version

    @staticmethod
    def _data(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result.get("data") or {}
        return getattr(result, "data", {}) or {}

    def _execute(self, slug: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._data(
            self._composio.tools.execute(
                slug,
                user_id=self._user_id,
                arguments=arguments,
                version=self._version,
            )
        )

    def reply(
        self, source_ref: str, text: str, thread_ts: str | None = None
    ) -> SlackMessageRef:
        ref = parse_source_ref(source_ref)
        arguments: dict[str, Any] = {"channel": ref.channel, "text": text}
        if thread_ts:
            # Without this the reply lands in the channel rather than the
            # thread, in front of everyone rather than the people talking.
            arguments["thread_ts"] = thread_ts

        data = self._execute("SLACK_SEND_MESSAGE", arguments)
        return SlackMessageRef(channel=ref.channel, ts=str(data.get("ts") or ""))

    def mark_read(self, source_ref: str) -> None:
        ref = parse_source_ref(source_ref)
        self._execute(
            "SLACK_SET_READ_CURSOR_IN_A_CONVERSATION",
            {"channel": ref.channel, "ts": ref.ts},
        )

    def unread(self, identity: Identity, now: datetime | None = None) -> list[RawEvent]:
        """Unread DMs and mentions from the last 30 days.

        Triggers only fire while the backend is running, so without this the
        app is blind to anything that happened before it started: a message
        from this morning simply does not exist. Fetched live on every refresh
        and never archived; only the items that survive the mention and unread
        filters become feed rows, and those age out with everything else.
        """
        now = now or datetime.now(timezone.utc)
        oldest = (now - BACKFILL).timestamp()

        wanted = [
            conversation
            for conversation in self._conversations()
            if conversation.get("id")
            # Slack reports what the user has not read. Anything below that
            # mark they have already dealt with, by their own action.
            and conversation.get("unread_count_display") != 0
        ]
        if not wanted:
            return []

        # One history call per conversation, run together. In series a dozen
        # conversations overran the refresh timeout on their own and Slack
        # dropped out of the sync entirely.
        with ThreadPoolExecutor(max_workers=min(8, len(wanted))) as pool:
            histories = list(
                pool.map(
                    lambda conversation: (
                        conversation,
                        self._history(conversation["id"], oldest),
                    ),
                    wanted,
                )
            )

        found: list[RawEvent] = []
        for conversation, messages in histories:
            channel = conversation["id"]
            is_dm = bool(conversation.get("is_im"))
            name = conversation.get("name") or ""
            for message in messages:
                payload = {
                    **message,
                    "channel": channel,
                    "channel_type": "im" if is_dm else "channel",
                    "channel_name": name,
                }
                event = (
                    direct_message_to_raw_event(payload, identity=identity)
                    if is_dm
                    else channel_message_to_raw_event(payload, identity=identity)
                )
                if event is not None:
                    found.append(event)
        return found

    def _conversations(self) -> list[dict[str, Any]]:
        try:
            data = self._execute(
                "SLACK_LIST_CONVERSATIONS",
                {
                    "types": "im,mpim,public_channel,private_channel",
                    "exclude_archived": True,
                    "limit": MAX_CONVERSATIONS,
                },
            )
        except Exception:
            log.warning("could not list Slack conversations", exc_info=True)
            return []
        channels = data.get("channels") or data.get("conversations") or []
        return channels[:MAX_CONVERSATIONS]

    def _history(self, channel: str, oldest: float) -> list[dict[str, Any]]:
        try:
            data = self._execute(
                "SLACK_FETCH_CONVERSATION_HISTORY",
                {
                    "channel": channel,
                    "oldest": str(oldest),
                    "limit": MAX_PER_CONVERSATION,
                },
            )
        except Exception:
            # One unreadable conversation must not lose the others.
            log.info("could not read history for %s", channel, exc_info=True)
            return []
        return data.get("messages") or []

    def channel_summary(self, now: datetime | None = None) -> dict[str, Any]:
        """Message volume over 30 days, per conversation. Live, never stored.

        Bounded to a handful of conversations and fetched in parallel, because
        counting every message in every channel would be both slow and useless:
        what matters is where the traffic is, not the exact total.
        """
        now = now or datetime.now(timezone.utc)
        oldest = (now - BACKFILL).timestamp()
        conversations = self._conversations()[:MAX_CONVERSATIONS]

        def one(conversation: dict[str, Any]) -> dict[str, Any]:
            channel = conversation.get("id")
            messages = self._history(channel, oldest) if channel else []
            is_dm = bool(conversation.get("is_im"))
            label = "Direct message" if is_dm else f"#{conversation.get('name') or channel}"
            return {
                "label": label,
                "count": len(messages),
                "is_dm": is_dm,
                "url": f"https://app.slack.com/client/-/{channel}",
            }

        with ThreadPoolExecutor(max_workers=min(8, len(conversations) or 1)) as pool:
            rows = list(pool.map(one, conversations))
        return {
            "channels": sum(1 for r in rows if not r["is_dm"]),
            "dms": sum(1 for r in rows if r["is_dm"]),
            "messages": sum(r["count"] for r in rows),
            "rows": [r for r in rows if r["count"] > 0],
        }

    def resolve_identity(self) -> Identity:
        """Section 3.10: mention detection is impossible without this, and it
        is resolved once at connection time rather than per message."""
        data = self._execute("SLACK_TEST_AUTH", {})
        return Identity(slack_user_id=data.get("user_id") or data.get("user_id_str"))
