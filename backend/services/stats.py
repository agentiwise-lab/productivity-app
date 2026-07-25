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
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from backend.models.feed import FeedItem
from backend.models.identity import Identity
from backend.models.sources import LABELS, Source
from backend.models.tiers import Tier

log = logging.getLogger(__name__)

WINDOW = timedelta(days=30)


class StatLine(BaseModel):
    label: str
    value: int
    detail: str | None = None
    value_label: str | None = None
    url: str | None = None


class SourceDashboard(BaseModel):
    source: Source
    label: str
    #: **``headline[0]`` is the hero**, drawn at 34pt above the rest of the
    #: board; everything after it becomes the summary grid. A convention rather
    #: than a `hero` field, because a convention costs nothing and can be
    #: reversed without a migration. Anything that inserts a stat at position 0
    #: is therefore choosing the headline number for the whole screen.
    headline: list[StatLine] = []
    breakdown: list[StatLine] = []
    breakdown_title: str = "Breakdown"
    unavailable: list[str] = []


def _recent(items: list[FeedItem], now: datetime) -> list[FeedItem]:
    """The same rule the feed's retention uses, and for the same reason.

    An open item carrying a deadline never ages out, so "Needs you" agrees with
    what Home actually shows. Filtering on age alone made the tile read 2 while
    the feed listed 9, because seven of them were overdue since June.
    """
    cutoff = now - WINDOW
    return [
        i
        for i in items
        if (i.occurred_at or i.created_at or now) >= cutoff or i.deadline is not None
    ]


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


#: How long a built board stays good enough to serve again.
#:
#: These are 30-day counts, so a minute of staleness is invisible. What it buys
#: is not just speed: Slack's search endpoint has a workspace-wide budget of
#: roughly twenty calls a minute and one board costs thirty-five, so a user
#: tapping back into Slack was guaranteed to exhaust it. Over budget, calls come
#: back 429 and the counting code reads that as zero, which quietly understated
#: the workspace total by hundreds of messages. Serving the cached board is the
#: difference between a right answer and a wrong one, not merely a fast one.
CACHE_TTL = timedelta(seconds=60)


class SourceStatsService:
    def __init__(
        self,
        integrations: Any | None = None,
        identity_for: Any | None = None,
        clock: Any | None = None,
    ) -> None:
        self._integrations = integrations
        self._identity_for = identity_for or (lambda user, provider: Identity())
        self._now_fn = clock or (lambda: datetime.now(timezone.utc))
        # Keyed by (user_id, source), never source alone: a board cached for one
        # user must never be served to another. That single-key cache was a
        # cross-tenant leak waiting to happen.
        self._cache: dict[tuple[str, Source], tuple[datetime, SourceDashboard]] = {}

    def dashboard(
        self,
        user_id: str,
        source: Source,
        items: list[FeedItem],
        now: datetime | None = None,
    ) -> SourceDashboard:
        now = now or self._now_fn()

        key = (user_id, source)
        cached = self._cache.get(key)
        if cached is not None and now - cached[0] < CACHE_TTL:
            return cached[1]

        board = self._build(user_id, source, items, now)
        self._cache[key] = (now, board)
        return board

    def _build(
        self, user_id: str, source: Source, items: list[FeedItem], now: datetime
    ) -> SourceDashboard:
        mine = _recent([i for i in items if i.source == source.value], now)
        board = SourceDashboard(source=source, label=LABELS[source])
        resolve = (
            (lambda attr: getattr(self._integrations, attr)(user_id))
            if self._integrations is not None
            else (lambda attr: None)
        )

        try:
            if source is Source.GITHUB:
                login = self._identity_for(user_id, "github").github_login
                logins = {login} if login else set()
                self._github_board(board, mine, resolve("github"), logins)
            elif source is Source.LINEAR:
                self._linear_board(board, mine, resolve("linear"))
            elif source is Source.CALENDAR:
                self._calendar_board(board, now, resolve("calendar"))
            elif source is Source.GMAIL:
                self._gmail_board(board, mine, resolve("gmail"))
            elif source is Source.SLACK:
                self._slack_board(board, mine, now, resolve("slack"))
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

    def _github_board(
        self,
        board: SourceDashboard,
        items: list[FeedItem],
        github: Any | None,
        logins: set[str],
    ) -> None:
        board.breakdown_title = "Repositories"
        if github is None:
            repos = Counter(i.repo for i in items if i.repo)
            board.breakdown = [
                StatLine(label=r.split("/")[-1], value=c, detail="notifications")
                for r, c in repos.most_common(10)
            ]
            return

        # The two halves are independent, so they run together. In series the
        # board paid for both round trips, and the second is itself two deep.
        with ThreadPoolExecutor(max_workers=2) as pool:
            summary_f = pool.submit(github.activity_summary)
            repos_f = pool.submit(github.repo_activity, logins)

        try:
            activity = summary_f.result()
            board.headline += [
                StatLine(label="Open PRs", value=activity.get("open_prs", 0), detail="yours"),
                StatLine(label="Merged", value=activity.get("merged_prs", 0), detail="30 days"),
            ]
        except Exception:
            log.warning("github activity summary failed", exc_info=True)
            board.unavailable.append("pull request counts")

        try:
            repos = repos_f.result()
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

    def _linear_board(
        self, board: SourceDashboard, items: list[FeedItem], linear: Any | None
    ) -> None:
        board.breakdown_title = "Projects"
        if linear is None:
            board.unavailable.append("linear")
            return

        try:
            stats = linear.issue_stats()
        except Exception:
            log.warning("linear issue stats failed", exc_info=True)
            board.unavailable.append("issue counts")
            stats = {}

        # Every figure covers only issues assigned to this user. Linear holds a
        # lot of work nobody is assigned to, and counting it told the user they
        # had finished nothing in a month they had worked all the way through.
        # The details spell out how the tiles relate, because six bare numbers
        # that partly contain each other read as arithmetic that does not add
        # up. Remaining is the whole open set; Backlog, Overdue and Due this
        # week are all slices of it, not additions to it.
        remaining = stats.get("remaining", 0)
        backlog = stats.get("backlog", 0)
        board.headline += [
            StatLine(
                label="Completed",
                value=stats.get("completed_30d", 0),
                detail="you closed, last 30 days",
            ),
            StatLine(label="Open", value=remaining, detail="assigned to you"),
            StatLine(
                label="Backlog",
                value=backlog,
                detail=f"of the {remaining} open, not started",
            ),
            StatLine(
                label="Overdue",
                value=stats.get("overdue", 0),
                detail=f"of the {remaining} open, past due",
            ),
            StatLine(
                label="Due this week",
                value=stats.get("due_this_week", 0),
                detail=f"of the {remaining} open, next 7 days",
            ),
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

    def _calendar_board(
        self, board: SourceDashboard, now: datetime, calendar: Any | None
    ) -> None:
        board.breakdown_title = "Most frequent, last 30 days"
        if calendar is None:
            board.unavailable.append("calendar")
            return

        meetings_today = calendar.today(now=now)
        booked_today = sum((m.end - m.start).total_seconds() / 3600 for m in meetings_today)
        board.headline += [
            StatLine(label="Today", value=len(meetings_today), detail="meetings"),
            StatLine(label="Booked", value=round(booked_today), detail="hours today"),
        ]

        try:
            window = calendar.window_meetings(now=now)
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

    def _gmail_board(
        self, board: SourceDashboard, items: list[FeedItem], gmail: Any | None
    ) -> None:
        board.breakdown_title = "Senders"
        if gmail is None:
            board.unavailable.append("gmail")
            return

        try:
            summary = gmail.inbox_summary()
        except Exception:
            log.warning("gmail inbox summary failed", exc_info=True)
            board.unavailable.append("unread mail")
            return

        senders_map = summary["senders"]
        unread = summary["unread"]
        sampled = summary["sampled"]

        # Counted at Gmail, not in the feed. The feed holds only what needs a
        # reply, so counting it said "3 emails" to a mailbox with two hundred
        # unread. "Set aside" is gone: it named an internal tier, not anything
        # the user had asked about.
        board.headline += [
            StatLine(label="Unread", value=unread, detail="in the last 30 days"),
            StatLine(label="Senders", value=len(senders_map), detail="wrote to you"),
        ]
        if sampled < unread:
            board.breakdown_title = f"Senders, most recent {sampled}"
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
            )[:25]
        ]

    # --------------------------------------------------------------- Slack

    def _slack_board(
        self,
        board: SourceDashboard,
        items: list[FeedItem],
        now: datetime,
        slack: Any | None,
    ) -> None:
        board.breakdown_title = "Where the traffic is"
        if slack is None:
            board.unavailable.append("slack")
            return
        try:
            summary = slack.channel_summary(now=now)
        except Exception:
            log.warning("slack summary failed", exc_info=True)
            board.unavailable.append("message volume")
            return

        board.headline += [
            StatLine(label="Messages", value=summary["messages"], detail="30 days"),
            StatLine(label="Channels", value=summary["channels"], detail="active"),
            StatLine(label="DMs", value=summary["dms"], detail="one to one"),
        ]
        # Channels and DMs together, every one counted, so the rows add up to
        # the Messages tile above them. A conversation Slack refused to count
        # says so rather than showing a zero it did not earn.
        uncounted = summary.get("uncounted") or 0
        if uncounted:
            board.unavailable.append(
                f"message counts for {uncounted} conversation"
                + ("s" if uncounted != 1 else "")
            )
        board.breakdown = [
            StatLine(
                label=row["label"] if row.get("is_dm") is False else f"@{row['label']}",
                value=row.get("count", 0),
                value_label=(
                    f"{row['count']} message" + ("s" if row["count"] != 1 else "")
                    if row.get("counted", True)
                    else "not counted"
                ),
                detail=None,
                url=row.get("url"),
            )
            for row in summary["rows"]
        ]
