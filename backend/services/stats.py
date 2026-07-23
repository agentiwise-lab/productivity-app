"""Per-source dashboards.

Each source answers "what has been going on here", which is a different question
from the feed's "what needs me now". The feed is deliberately short; this is
where the volume and the history live.

Everything is computed live from the provider and returned, never stored. These
are counts over the last 30 days, and persisting them would mean keeping a copy
of the user's mail and messages to produce numbers a single call already gives.

Rows carry an optional ``url`` so a breakdown line can open the thing itself,
and a ``value_label`` for figures that are not plain counts. What is and is not
tappable is deliberate: a repository opens on GitHub and a sender opens that
Gmail search, but a Calendar frequency line is a summary and opens nothing.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from backend.models.feed import FeedItem
from backend.models.sources import LABELS, Source
from backend.models.tiers import Tier

log = logging.getLogger(__name__)

WINDOW = timedelta(days=30)

# Commits are authored under either of the user's GitHub identities.
_GITHUB_LOGINS = {"vicky81125", "vicky99105"}


class StatLine(BaseModel):
    label: str
    value: int
    detail: str | None = None
    value_label: str | None = None
    url: str | None = None


class SourceDashboard(BaseModel):
    source: Source
    label: str
    headline: list[StatLine] = []
    breakdown: list[StatLine] = []
    breakdown_title: str = "Breakdown"
    unavailable: list[str] = []


def _recent(items: list[FeedItem], now: datetime) -> list[FeedItem]:
    cutoff = now - WINDOW
    return [i for i in items if (i.occurred_at or i.created_at or now) >= cutoff]


def _tier_of(item: FeedItem) -> Tier:
    return item.llm_tier or item.rule_tier


def _github_row_label(repo: dict) -> str:
    parts = []
    if repo.get("commits"):
        parts.append(f"{repo['commits']} commit" + ("s" if repo["commits"] != 1 else ""))
    if repo.get("merged_prs"):
        parts.append(f"{repo['merged_prs']} merged")
    if repo.get("open_prs"):
        parts.append(f"{repo['open_prs']} open")
    return " · ".join(parts) if parts else "no recent activity"


def _minutes_label(minutes: float) -> str:
    if minutes >= 60:
        hours = minutes / 60
        return f"{hours:.0f}h" if hours == int(hours) else f"{hours:.1f}h"
    return f"{round(minutes)}m"


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
        self._gmail = gmail
        self._slack = slack

    def dashboard(
        self, source: Source, items: list[FeedItem], now: datetime | None = None
    ) -> SourceDashboard:
        now = now or datetime.now(timezone.utc)
        mine = _recent([i for i in items if i.source == source.value], now)
        board = SourceDashboard(source=source, label=LABELS[source])

        try:
            if source is Source.GITHUB:
                self._github_board(board, mine)
            elif source is Source.LINEAR:
                self._linear_board(board, mine)
            elif source is Source.CALENDAR:
                self._calendar_board(board, now)
            elif source is Source.GMAIL:
                self._gmail_board(board, mine)
            elif source is Source.SLACK:
                self._slack_board(board, mine, now)
        except Exception:
            log.warning("dashboard build failed for %s", source.value, exc_info=True)
            board.unavailable.append("live activity")

        board.headline.insert(
            0,
            StatLine(
                label="Needs you",
                value=sum(1 for i in mine if _tier_of(i) is not Tier.NOISE),
                detail="right now",
            ),
        )
        return board

    # --------------------------------------------------------------- GitHub

    def _github_board(self, board: SourceDashboard, items: list[FeedItem]) -> None:
        board.breakdown_title = "Repositories"
        if self._github is None:
            repos = Counter(i.repo for i in items if i.repo)
            board.breakdown = [
                StatLine(label=r.split("/")[-1], value=c, detail="notifications")
                for r, c in repos.most_common(10)
            ]
            return

        try:
            activity = self._github.activity_summary()
            board.headline += [
                StatLine(label="Open PRs", value=activity.get("open_prs", 0), detail="yours"),
                StatLine(label="Merged", value=activity.get("merged_prs", 0), detail="30 days"),
            ]
        except Exception:
            log.warning("github activity summary failed", exc_info=True)
            board.unavailable.append("pull request counts")

        try:
            repos = self._github.repo_activity(_GITHUB_LOGINS)
            total_commits = sum(r["commits"] for r in repos)
            board.headline.insert(
                1, StatLine(label="Commits", value=total_commits, detail="yours")
            )
            board.headline.insert(
                1, StatLine(label="Repos", value=len(repos), detail="active")
            )
            # Each row is richer than any single headline number: commits, then
            # PRs merged and open, so the list is not just the "Commits" tile
            # spread across rows.
            board.breakdown = [
                StatLine(
                    label=repo["full_name"].split("/")[-1],
                    value=repo["commits"],
                    value_label=_github_row_label(repo),
                    detail=None,
                    url=repo["url"],
                )
                for repo in sorted(
                    repos,
                    key=lambda r: (r["commits"], r["merged_prs"], r["open_prs"]),
                    reverse=True,
                )
            ]
        except Exception:
            log.warning("github repo activity failed", exc_info=True)
            board.unavailable.append("per-repository activity")

    # --------------------------------------------------------------- Linear

    def _linear_board(self, board: SourceDashboard, items: list[FeedItem]) -> None:
        board.breakdown_title = "Projects"
        if self._linear is None:
            board.unavailable.append("linear")
            return

        try:
            stats = self._linear.issue_stats()
        except Exception:
            log.warning("linear issue stats failed", exc_info=True)
            board.unavailable.append("issue counts")
            stats = {}

        board.headline += [
            StatLine(label="Completed", value=stats.get("completed_30d", 0), detail="this month"),
            StatLine(label="Remaining", value=stats.get("remaining", 0), detail="open"),
            StatLine(label="Backlog", value=stats.get("backlog", 0), detail="not started"),
            StatLine(label="Overdue", value=stats.get("overdue", 0), detail="past due"),
        ]

        # Per project: how much is done and how much is left, the two numbers
        # that actually say where the work stands. Sorted by what remains.
        projects = stats.get("projects") or {}
        board.breakdown = [
            StatLine(
                label=name,
                value=counts["remaining"],
                value_label=f"{counts['done']} done · {counts['remaining']} left",
                detail=None,
            )
            for name, counts in sorted(
                projects.items(),
                key=lambda kv: (kv[1]["remaining"], kv[1]["done"]),
                reverse=True,
            )
        ]

    # ------------------------------------------------------------- Calendar

    def _calendar_board(self, board: SourceDashboard, now: datetime) -> None:
        board.breakdown_title = "Most frequent, last 30 days"
        if self._calendar is None:
            board.unavailable.append("calendar")
            return

        meetings_today = self._calendar.today(now=now)
        booked_today = sum((m.end - m.start).total_seconds() / 3600 for m in meetings_today)
        board.headline += [
            StatLine(label="Today", value=len(meetings_today), detail="meetings"),
            StatLine(label="Booked", value=round(booked_today), detail="hours today"),
        ]

        try:
            window = self._calendar.window_meetings(now=now)
        except Exception:
            log.warning("calendar window failed", exc_info=True)
            board.unavailable.append("30-day meetings")
            return

        board.headline.append(
            StatLine(
                label="Last 30 days",
                value=len(window),
                detail=f"{round(sum(m['minutes'] for m in window) / 60)}h total",
            )
        )
        grouped: dict[str, list[int]] = defaultdict(list)
        for meeting in window:
            grouped[meeting["title"]].append(meeting["minutes"])
        board.breakdown = [
            StatLine(
                label=title,
                value=len(durations),
                value_label=f"{len(durations)}x · {_minutes_label(sum(durations))}",
                detail="total time",
            )
            for title, durations in sorted(
                grouped.items(), key=lambda kv: sum(kv[1]), reverse=True
            )[:12]
        ]

    # --------------------------------------------------------------- Gmail

    def _gmail_board(self, board: SourceDashboard, items: list[FeedItem]) -> None:
        board.breakdown_title = "Senders"
        noise = sum(1 for i in items if _tier_of(i) is Tier.NOISE)
        senders_map: dict[tuple[str, str], int] = defaultdict(int)
        for i in items:
            senders_map[(i.sender_name or i.sender_handle or "unknown", i.sender_handle or "")] += 1

        board.headline += [
            StatLine(label="Unread", value=len(items), detail="30 days"),
            StatLine(label="Senders", value=len(senders_map), detail="distinct"),
            StatLine(label="Filtered", value=noise, detail="bulk and lists"),
        ]
        # Grouped by sender with the email count, like the GitHub repo rows.
        # Tapping opens that sender's unread mail in Gmail, not one arbitrary
        # message.
        board.breakdown = [
            StatLine(
                label=name,
                value=count,
                value_label=f"{count} email" + ("s" if count != 1 else ""),
                detail=None,
                url=(
                    f"https://mail.google.com/mail/u/0/#search/from:{handle}+is:unread"
                    if handle
                    else None
                ),
            )
            for (name, handle), count in sorted(
                senders_map.items(), key=lambda kv: kv[1], reverse=True
            )[:15]
        ]

    # --------------------------------------------------------------- Slack

    def _slack_board(
        self, board: SourceDashboard, items: list[FeedItem], now: datetime
    ) -> None:
        board.breakdown_title = "Where the traffic is"
        if self._slack is None:
            board.unavailable.append("slack")
            return
        try:
            summary = self._slack.channel_summary(now=now)
        except Exception:
            log.warning("slack summary failed", exc_info=True)
            board.unavailable.append("message volume")
            return

        board.headline += [
            StatLine(label="Messages", value=summary["messages"], detail="30 days"),
            StatLine(label="Channels", value=summary["channels"], detail="active"),
            StatLine(label="DMs", value=summary["dms"], detail="one to one"),
        ]
        # The channels the user is in, tappable to open. Per-channel message
        # counts are deliberately not fetched: that is a history call each and
        # Slack throttles it. The workspace total is in the headline instead.
        board.breakdown = [
            StatLine(
                label=row["label"],
                value=row.get("count", 0),
                value_label=(
                    f"{row['count']} message" + ("s" if row["count"] != 1 else "")
                    if row.get("count")
                    else "—"
                ),
                detail=None,
                url=row.get("url"),
            )
            for row in summary["rows"][:20]
        ]
