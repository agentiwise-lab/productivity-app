"""Acting on Slack, and reading it, through Composio.

Contract first: callers import ``SlackService`` and never this implementation.

Two things shaped this file. Writes are visible to other people, so parsing is
strict: a ``source_ref`` that cannot be read raises rather than falling back to
a default channel, because the failure of guessing is a private reply posted
somewhere public. And Slack rate-limits reads hard, so the dashboard counts with
``search.messages`` rather than pulling history per conversation, and reports
which conversations it could not count instead of showing them as zero.
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
from backend.models.feed import Actor
from backend.models.identity import Identity

log = logging.getLogger(__name__)

#: How far back the unread backfill reaches. Matches the feed's retention, so
#: the app never surfaces something it would immediately drop.
BACKFILL = timedelta(days=30)


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

    def recent(self, identity: Identity, now: datetime | None = None) -> list[RawEvent]:
        ...

    def user_names(self) -> dict[str, str]:
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
        self._names: dict[str, str] | None = None

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

    def user_names(self) -> dict[str, str]:
        """The workspace directory, id to display name, fetched once.

        Without it a card says "U8FAN1KSN" where a person's name belongs, and
        the message body keeps raw ``<@U…>`` tokens that the model is then paid
        to read. One paginated call per process covers every message.
        """
        if self._names is not None:
            return self._names

        names: dict[str, str] = {}
        cursor: str | None = None
        try:
            for _ in range(20):  # runaway guard, not an expected page count
                arguments: dict[str, Any] = {"limit": 200}
                if cursor:
                    arguments["cursor"] = cursor
                data = self._execute("SLACK_LIST_ALL_USERS", arguments)
                for member in data.get("members") or []:
                    profile = member.get("profile") or {}
                    label = (
                        profile.get("display_name")
                        or profile.get("real_name")
                        or member.get("real_name")
                        or member.get("name")
                    )
                    if member.get("id") and label:
                        names[member["id"]] = label
                # The cursor can carry whitespace, which reads as truthy and
                # loops forever on the same page.
                cursor = ((data.get("response_metadata") or {}).get("next_cursor") or "").strip()
                if not cursor:
                    break
        except Exception:
            # A card showing a raw id is worse than no card, but not by enough
            # to fail the whole refresh over. Crucially the partial map is NOT
            # cached: caching a directory built from a failed load froze empty
            # names for the life of the process, so the next refresh retries.
            log.warning("could not load the Slack user directory", exc_info=True)
            return names

        self._names = names
        return names

    def unread(self, identity: Identity, now: datetime | None = None) -> list[RawEvent]:
        """Backfill direct messages from the last 30 days, in one search.

        Direct messages only. Channel mentions arrive on the live trigger while
        we run; backfilling every channel's history fans out into dozens of
        calls. Fetched live, never archived.

        ``search.messages`` rather than a history call per conversation: 27 DMs
        meant 27 requests against the endpoint Slack throttles hardest, an
        entire pass once came back empty purely from 429s, and the refresh timed
        out. One search returns every DM in the window, and search did not rate
        limit once across ninety calls. It also omits joins and leaves, which
        the history path had to filter out afterwards.
        """
        now = now or datetime.now(timezone.utc)
        after = (now - BACKFILL).strftime("%Y-%m-%d")

        try:
            data = self._execute(
                "SLACK_SEARCH_MESSAGES",
                {"query": f"is:dm after:{after}", "count": 100},
            )
        except Exception:
            log.warning("could not search direct messages", exc_info=True)
            return []

        matches = (data.get("messages") or {}).get("matches") or []
        names = self.user_names()

        found: list[RawEvent] = []
        for match in matches:
            channel = match.get("channel") or {}
            payload = {
                **match,
                # A search match nests the conversation; the mapper wants the id.
                "channel": channel.get("id") or "",
                "channel_type": "im",
            }
            event = direct_message_to_raw_event(
                payload, identity=identity, names=names
            )
            if event is not None:
                found.append(event)
        return found

    def recent(
        self, identity: Identity, now: datetime | None = None
    ) -> list[RawEvent]:
        """The top 100 recent messages the user is involved in, for Later.

        Broader than ``unread`` (which stays DM-only so it does not over-elevate
        Home): a single ``search.messages`` over the last 30 days, so recent DMs
        *and* channel activity the user is part of populate Later rather than it
        reading empty (bible 3.3). The user's own messages are excluded, since a
        note-to-self never "needed" them. Later itself drops anything already on
        Home, so this is deliberately inclusive.
        """
        from backend.integrations.slack import _ts_to_datetime

        now = now or datetime.now(timezone.utc)
        after = (now - BACKFILL).strftime("%Y-%m-%d")
        try:
            data = self._execute(
                "SLACK_SEARCH_MESSAGES",
                {"query": f"after:{after}", "count": 100},
            )
        except Exception:
            log.warning("could not search recent Slack messages", exc_info=True)
            return []

        matches = (data.get("messages") or {}).get("matches") or []
        names = self.user_names()
        me = identity.slack_user_id

        found: list[RawEvent] = []
        for match in matches:
            author = match.get("user") or ""
            if me and author == me:
                continue  # the user's own messages never come back
            text = match.get("text") or ""
            if not text.strip():
                continue
            channel = match.get("channel") or {}
            channel_id = channel.get("id") or ""
            channel_name = channel.get("name")
            where = f"#{channel_name}" if channel_name else "Direct message"
            found.append(
                RawEvent(
                    source="slack",
                    # Same shape as the DM/channel mappers, so Later's on-home
                    # exclusion collapses a message that is also on Home.
                    source_ref=f"slack:{channel_id}:{match.get('ts', '')}",
                    reason="slack_later",
                    subject_type="Message",
                    title=names.get(author) or where,
                    body=text,
                    url=match.get("permalink") or "",
                    repo="",
                    context_chip=where,
                    actor=Actor(
                        login=author, display_name=names.get(author) or None
                    ),
                    occurred_at=_ts_to_datetime(match.get("ts")),
                    is_blocking=False,
                    raw=match,
                )
            )
        return found[:100]

    def channel_summary(self, now: datetime | None = None) -> dict[str, Any]:
        """Every conversation the user is in, each with its own 30-day count.

        The headline total is the **sum of the rows**, deliberately. It used to
        be a separate workspace-wide ``search.messages``, which counted channels
        and DMs and bots together while the rows below covered only the first
        twelve channels. The two could never agree, and a dashboard whose
        breakdown contradicts its own headline is not worth reading.

        Channels and DMs are listed as two separate typed calls: a single
        mixed-type ``conversations.list`` came back inconsistently through
        Composio, a second call in the same window returning only DMs so the
        channels silently vanished. Live, never stored.
        """
        now = now or datetime.now(timezone.utc)
        after = (now - BACKFILL).strftime("%Y-%m-%d")

        # Six independent reads, run together rather than one after another.
        # None of them needs any of the others; only the assembly below needs
        # all of them, and in series they were most of the dashboard's 19
        # seconds before the per-channel counting had even started.
        with ThreadPoolExecutor(max_workers=6) as pool:
            names_f = pool.submit(self.user_names)
            channels_f = pool.submit(self._list, "public_channel,private_channel")
            discovered_f = pool.submit(self._discover_channels, after)
            dms_f = pool.submit(self._list, "im")
            per_dm_f = pool.submit(self._direct_message_counts, after)
            total_f = pool.submit(self._workspace_total, after)

        names = names_f.result()
        discovered = discovered_f.result()
        dm_list = dms_f.result()
        per_dm = per_dm_f.result()

        listed = {
            c["name"]: c
            for c in channels_f.result()
            if c.get("id") and c.get("name")
        }
        # Slack Connect channels never come back from conversations.list, but
        # they are in the search index and they are the busy ones: eight of them
        # held 4504 of this workspace's 5932 messages, including the single
        # busiest channel. Listing only what conversations.list knows about
        # meant the dashboard missed three quarters of the traffic.
        for name, channel_id in discovered.items():
            listed.setdefault(name, {"id": channel_id, "name": name})

        rows: list[dict[str, Any]] = [
            {
                "label": f"#{name}",
                "query": f"in:#{name}",
                "is_dm": False,
                "channel": c.get("id"),
                "url": f"https://app.slack.com/client/-/{c.get('id')}",
                "count": 0,
            }
            for name, c in listed.items()
        ]
        channel_count = len(rows)

        # DMs get rows too. "27 DMs" with no breakdown could not say who was
        # actually talking to the user, which is the only interesting part.
        #
        # Counted from a single ``is:dm`` search tallied by conversation, not a
        # search per DM. Twenty-seven extra round trips took the dashboard past
        # thirty seconds, which is longer than the app was willing to wait, so
        # the screen gave up and bounced back to Sources.
        for dm in dm_list:
            user_id = dm.get("user")
            if not dm.get("id") or not user_id:
                continue
            rows.append(
                {
                    "label": names.get(user_id) or user_id,
                    "query": "",
                    "is_dm": True,
                    "channel": dm["id"],
                    "url": f"https://app.slack.com/client/-/{dm['id']}",
                    "count": per_dm.get(dm["id"], 0),
                    "counted": True,
                }
            )
        dm_count = len(rows) - channel_count

        def count(row: dict) -> int | None:
            """None means Slack would not tell us, which is not the same as 0."""
            try:
                data = self._execute(
                    "SLACK_SEARCH_MESSAGES",
                    {"query": f"{row['query']} after:{after}", "count": 1},
                )
                return (data.get("messages") or {}).get("total") or 0
            except Exception:
                log.info("count failed for %s", row["label"], exc_info=True)
                return None

        # Search is rate-limited, so this stays modest rather than fanning out
        # across fifty conversations at once and being throttled into zeros.
        throttled = 0
        pending = [r for r in rows if r["query"]]
        with ThreadPoolExecutor(max_workers=min(8, len(pending) or 1)) as pool:
            for row, value in zip(pending, pool.map(count, pending)):
                if value is None:
                    throttled += 1
                    row["counted"] = False
                else:
                    row["count"] = value
                    row["counted"] = True

        rows.sort(key=lambda r: r["count"], reverse=True)
        counted = sum(r["count"] for r in rows)

        # The true workspace figure, so the headline is not quietly capped by
        # whatever we managed to enumerate. Any gap becomes its own row rather
        # than a silent discrepancy between the total and the list under it.
        total = total_f.result()
        if total is None:
            total = counted
        elif total > counted:
            rows.append(
                {
                    "label": "Everywhere else",
                    "query": "",
                    "is_dm": False,
                    "channel": None,
                    "url": None,
                    "count": total - counted,
                    "counted": True,
                }
            )

        return {
            "channels": channel_count,
            "dms": dm_count,
            "messages": total,
            "uncounted": throttled,
            "rows": rows,
        }

    def _direct_message_counts(self, after: str) -> dict[str, int]:
        """Messages per DM conversation, from one search rather than N.

        Every direct message in the window comes back in a single call, and each
        match names its conversation, so tallying them here replaces one search
        per DM. On this workspace that is 27 calls saved and roughly twenty
        seconds off the dashboard.
        """
        counts: dict[str, int] = {}
        try:
            data = self._execute(
                "SLACK_SEARCH_MESSAGES",
                {"query": f"is:dm after:{after}", "count": 100},
            )
        except Exception:
            log.info("direct message counts failed", exc_info=True)
            return counts

        for match in (data.get("messages") or {}).get("matches") or []:
            channel_id = (match.get("channel") or {}).get("id")
            if channel_id:
                counts[channel_id] = counts.get(channel_id, 0) + 1
        return counts

    def _workspace_total(self, after: str) -> int | None:
        try:
            data = self._execute(
                "SLACK_SEARCH_MESSAGES", {"query": f"after:{after}", "count": 1}
            )
            return (data.get("messages") or {}).get("total")
        except Exception:
            log.info("workspace message total failed", exc_info=True)
            return None

    def _discover_channels(self, after: str) -> dict[str, str]:
        """Channel names visible to search but not to ``conversations.list``.

        Sampled across pages rather than read exhaustively: results are ordered
        by relevance, so a handful of pages surfaces the high-volume channels,
        which are exactly the ones worth naming.
        """
        def one_page(page: int) -> list[dict[str, Any]]:
            try:
                data = self._execute(
                    "SLACK_SEARCH_MESSAGES",
                    {"query": f"after:{after}", "count": 100, "page": page},
                )
            except Exception:
                log.info("channel discovery page %d failed", page, exc_info=True)
                return []
            return (data.get("messages") or {}).get("matches") or []

        # The four sample pages together rather than one after another: they are
        # independent, and in series they were four round trips of pure latency.
        found: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=4) as pool:
            pages = list(pool.map(one_page, (1, 5, 20, 40)))
        for matches in pages:
            for match in matches:
                channel = match.get("channel") or {}
                name, channel_id = channel.get("name"), channel.get("id")
                # Skip DMs: in a search match their "name" is the other user's
                # id, which would render as a channel called U081FAN1KSN.
                if name and channel_id and not channel.get("is_im"):
                    found.setdefault(name, channel_id)
        return found

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
