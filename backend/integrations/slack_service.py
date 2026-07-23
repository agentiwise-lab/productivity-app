"""Acting on Slack, and reading it, through Composio.

Contract first: callers import ``SlackService`` and never this implementation.

Two things shaped this file. Writes are visible to other people, so parsing is
strict: a ``source_ref`` that cannot be read raises rather than falling back to
a default channel, because the failure of guessing is a private reply posted
somewhere public. And Slack rate-limits ``conversations.history`` hard, so the
dashboard never fans out a history call per channel; it lists conversations and
asks ``search.messages`` once for the total.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol

from pydantic import BaseModel

from backend.integrations.slack import (
    SLACK_TOOLKIT_VERSION,
    channel_message_to_raw_event,
    direct_message_to_raw_event,
)
from backend.models.events import RawEvent
from backend.models.identity import Identity

log = logging.getLogger(__name__)

#: How far back the unread backfill reaches. Matches the feed's retention, so
#: the app never surfaces something it would immediately drop.
BACKFILL = timedelta(days=30)
MAX_PER_CONVERSATION = 20
#: Channels whose message volume the dashboard counts. Search is rate-limited,
#: so only the first N are sampled; the rest still list, without a count.
SLACK_CHANNEL_SAMPLE = 12


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

    def unread(self, identity: Identity, now: datetime | None = None) -> list[RawEvent]:
        ...

    def channel_summary(self, now: datetime | None = None) -> dict[str, Any]:
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
                slug, user_id=self._user_id, arguments=arguments, version=self._version
            )
        )

    # -------------------------------------------------------------- writes

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

    # --------------------------------------------------------------- reads

    def unread(self, identity: Identity, now: datetime | None = None) -> list[RawEvent]:
        """Backfill unread direct messages from the last 30 days.

        Direct messages only. Channel mentions arrive on the live trigger while
        we run; backfilling every channel's history fans out into dozens of
        rate-limited calls and times the refresh out. DMs are the high-value
        backfill and there are few of them. Fetched live, never archived.
        """
        now = now or datetime.now(timezone.utc)
        oldest = (now - BACKFILL).timestamp()
        dms = [d for d in self._list("im") if d.get("id")]
        if not dms:
            return []

        with ThreadPoolExecutor(max_workers=min(6, len(dms))) as pool:
            histories = list(
                pool.map(lambda d: (d, self._history(d["id"], oldest)), dms)
            )

        found: list[RawEvent] = []
        for conversation, messages in histories:
            for message in messages:
                payload = {
                    **message,
                    "channel": conversation["id"],
                    "channel_type": "im",
                }
                event = direct_message_to_raw_event(payload, identity=identity)
                if event is not None:
                    found.append(event)
        return found

    def channel_summary(self, now: datetime | None = None) -> dict[str, Any]:
        """Conversations the user is in, plus a real 30-day message total.

        Channels and DMs are listed as two separate typed calls: a single
        mixed-type ``conversations.list`` came back inconsistently through
        Composio, a second call in the same window returning only DMs so the
        channels silently vanished. One ``search.messages`` gives the volume
        without a history fetch per channel. Live, never stored.
        """
        now = now or datetime.now(timezone.utc)
        channels_raw = self._list("public_channel,private_channel")
        dms_raw = self._list("im")

        rows = [
            {
                "label": f"#{c.get('name') or c.get('id')}",
                "name": c.get("name") or "",
                "is_dm": False,
                "channel": c.get("id"),
                "url": f"https://app.slack.com/client/-/{c.get('id')}",
                "count": 0,
            }
            for c in channels_raw
            if c.get("id")
        ]
        dm_count = sum(1 for d in dms_raw if d.get("id"))

        after = (now - BACKFILL).strftime("%Y-%m-%d")

        total = 0
        try:
            data = self._execute(
                "SLACK_SEARCH_MESSAGES", {"query": f"after:{after}", "count": 1}
            )
            total = (data.get("messages") or {}).get("total") or 0
        except Exception:
            log.info("slack message search failed", exc_info=True)

        # Per-channel volume, so a row can say how busy it is. One search each,
        # capped and run together: search is rate-limited too, so this is
        # best-effort and a throttled channel simply shows nothing.
        sample = [r for r in rows if r["name"]][:SLACK_CHANNEL_SAMPLE]

        def count(row: dict) -> int:
            try:
                data = self._execute(
                    "SLACK_SEARCH_MESSAGES",
                    {"query": f"in:#{row['name']} after:{after}", "count": 1},
                )
                return (data.get("messages") or {}).get("total") or 0
            except Exception:
                return 0

        with ThreadPoolExecutor(max_workers=min(5, len(sample) or 1)) as pool:
            for row, c in zip(sample, pool.map(count, sample)):
                row["count"] = c

        rows.sort(key=lambda r: r["count"], reverse=True)
        return {
            "channels": len(rows),
            "dms": dm_count,
            "messages": total,
            "rows": rows,
        }

    def resolve_identity(self) -> Identity:
        """Section 3.10: mention detection is impossible without the user id,
        and it is resolved once at connection time rather than per message."""
        data = self._execute("SLACK_TEST_AUTH", {})
        return Identity(slack_user_id=data.get("user_id") or data.get("user_id_str"))

    # ----------------------------------------------------------- internal

    def _list(self, types: str) -> list[dict[str, Any]]:
        try:
            data = self._execute(
                "SLACK_LIST_CONVERSATIONS",
                {"types": types, "exclude_archived": True, "limit": 200},
            )
        except Exception:
            log.warning("could not list Slack %s", types, exc_info=True)
            return []
        return data.get("channels") or data.get("conversations") or []

    def _history(self, channel: str, oldest: float) -> list[dict[str, Any]]:
        try:
            data = self._execute(
                "SLACK_FETCH_CONVERSATION_HISTORY",
                {"channel": channel, "oldest": str(oldest), "limit": MAX_PER_CONVERSATION},
            )
        except Exception:
            log.info("could not read history for %s", channel, exc_info=True)
            return []
        return data.get("messages") or []
