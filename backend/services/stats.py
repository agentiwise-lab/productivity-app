"""Per-source dashboards.

Each source gets a page answering "what has been going on here", which is a
different question from the feed's "what needs me now". The feed is deliberately
short; this is where the volume lives.

Everything is computed live and returned, never stored. These are counts about
the last 30 days, and persisting them would mean keeping a copy of the user's
mail and messages to produce numbers that a single call already gives us.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from backend.models.feed import FeedItem
from backend.models.sources import LABELS, Source
from backend.models.tiers import Tier

log = logging.getLogger(__name__)

WINDOW = timedelta(days=30)


class StatLine(BaseModel):
    """One row of the breakdown: a label, a number, and optional context."""

    label: str
    value: int
    detail: str | None = None


class SourceDashboard(BaseModel):
    source: Source
    label: str
    #: The two or three figures that headline the page.
    headline: list[StatLine] = []
    #: The breakdown underneath, whatever that means for this source.
    breakdown: list[StatLine] = []
    #: Named so the page can say what it could not load, rather than showing a
    #: confident zero.
    unavailable: list[str] = []


def _recent(items: list[FeedItem], now: datetime) -> list[FeedItem]:
    cutoff = now - WINDOW
    return [
        item
        for item in items
        if (item.occurred_at or item.created_at or now) >= cutoff
    ]


def _tier_of(item: FeedItem) -> Tier:
    return item.llm_tier or item.rule_tier


class SourceStatsService:
    def __init__(
        self,
        github: Any | None = None,
        linear: Any | None = None,
        calendar: Any | None = None,
        gmail: Any | None = None,
        slack: Any | None = None,
    ) -> None:
        self._github = github
        self._linear = linear
        self._calendar = calendar

    def dashboard(
        self, source: Source, items: list[FeedItem], now: datetime | None = None
    ) -> SourceDashboard:
        now = now or datetime.now(timezone.utc)
        mine = _recent([i for i in items if i.source == source.value], now)
        board = SourceDashboard(source=source, label=LABELS[source])

        if source is Source.GITHUB:
            self._github_board(board, mine, now)
        elif source is Source.LINEAR:
            self._linear_board(board, mine)
        elif source is Source.CALENDAR:
            self._calendar_board(board, now)
        elif source is Source.GMAIL:
            self._gmail_board(board, mine)
        elif source is Source.SLACK:
            self._slack_board(board, mine)

        board.headline.insert(
            0,
            StatLine(
                label="Needs you",
                value=sum(1 for i in mine if _tier_of(i) is not Tier.NOISE),
                detail="right now",
            ),
        )
        return board

    # ------------------------------------------------------------ per source

    def _github_board(
        self, board: SourceDashboard, items: list[FeedItem], now: datetime
    ) -> None:
        repos = Counter(item.repo for item in items if item.repo)
        board.headline += [
            StatLine(label="Repositories", value=len(repos), detail="active"),
            StatLine(
                label="Review requests",
                value=sum(1 for i in items if i.type_tag.value == "review"),
                detail="last 30 days",
            ),
        ]
        board.breakdown = [
            StatLine(label=repo, value=count, detail="notifications")
            for repo, count in repos.most_common(10)
        ]

        # Open pull requests the user raised, per repo. One call, and it is the
        # figure that actually answers "what have I got in flight".
        if self._github is not None:
            try:
                open_prs = self._github.open_pull_request_count()
                if open_prs is not None:
                    board.headline.append(
                        StatLine(label="Open PRs", value=open_prs, detail="yours")
                    )
            except Exception:
                log.warning("could not count pull requests", exc_info=True)
                board.unavailable.append("open pull requests")

    def _linear_board(self, board: SourceDashboard, items: list[FeedItem]) -> None:
        due = sum(1 for i in items if i.deadline is not None)
        board.headline += [
            StatLine(label="Assigned", value=len(items), detail="to you"),
            StatLine(label="With a due date", value=due),
        ]
        teams = Counter(item.context_chip or "Linear" for item in items)
        board.breakdown = [
            StatLine(label=team, value=count, detail="issues")
            for team, count in teams.most_common(10)
        ]

    def _calendar_board(self, board: SourceDashboard, now: datetime) -> None:
        if self._calendar is None:
            board.unavailable.append("calendar")
            return
        try:
            meetings = self._calendar.today(now=now)
        except Exception:
            log.warning("could not read the calendar", exc_info=True)
            board.unavailable.append("today's meetings")
            return

        booked = sum(
            (m.end - m.start).total_seconds() / 3600 for m in meetings
        )
        board.headline += [
            StatLine(label="Meetings today", value=len(meetings)),
            StatLine(label="Hours booked", value=round(booked), detail="today"),
        ]
        board.breakdown = [
            StatLine(
                label=m.title,
                value=round((m.end - m.start).total_seconds() / 60),
                detail=m.start.strftime("%H:%M"),
            )
            for m in meetings
        ]

    def _gmail_board(self, board: SourceDashboard, items: list[FeedItem]) -> None:
        noise = sum(1 for i in items if _tier_of(i) is Tier.NOISE)
        board.headline += [
            StatLine(label="Unread", value=len(items), detail="last 30 days"),
            StatLine(label="Filtered out", value=noise, detail="bulk and lists"),
        ]
        senders = Counter(
            item.sender_name or item.sender_handle or "unknown" for item in items
        )
        board.breakdown = [
            StatLine(label=sender, value=count, detail="unread")
            for sender, count in senders.most_common(10)
        ]

    def _slack_board(self, board: SourceDashboard, items: list[FeedItem]) -> None:
        dms = sum(1 for i in items if i.context_chip == "DM")
        board.headline += [
            StatLine(label="Messages", value=len(items), detail="last 30 days"),
            StatLine(label="Direct", value=dms, detail="one to one"),
        ]
        channels = Counter(item.context_chip or "?" for item in items)
        board.breakdown = [
            StatLine(label=channel, value=count, detail="messages")
            for channel, count in channels.most_common(10)
        ]
