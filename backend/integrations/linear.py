"""Linear.

The one source that needs almost no model. Linear has a native priority field
and a real due date, so urgency is stated rather than implied, and section 3.5
can settle nearly every issue with a rule. Only an issue with neither priority
nor a due date is genuinely ambiguous.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.models.events import RawEvent
from backend.models.feed import Actor

LINEAR_TOOLKIT_VERSION = "20260721_00"

#: Linear's own scale. 0 means "no priority", not "lowest".
PRIORITY_URGENT = 1
PRIORITY_HIGH = 2

log = logging.getLogger(__name__)

_UNSET = object()

#: Matched against ``state.name``. The list payload has no ``state.type``: the
#: ``state`` object it returns carries exactly one key, ``name``. Reading the
#: absent field meant the Done check never fired.
_DONE_STATES = {"completed", "canceled", "cancelled", "done"}

#: An issue due this many days out is close enough to belong on the Home feed.
DUE_SOON = timedelta(days=7)


def _is_done(issue: dict[str, Any]) -> bool:
    """True when Linear considers this issue finished.

    Both fields are checked because the two endpoints disagree: the issue
    *list* returns a ``state`` carrying only ``name``, while a single-issue
    fetch and the webhooks also carry ``type``. Reading ``type`` alone meant the
    check never fired on anything the list produced.
    """
    state = issue.get("state") or {}
    return any(
        str(state.get(field) or "").strip().lower() in _DONE_STATES
        for field in ("name", "type")
    )


def _parse(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _end_of_day(value: datetime) -> datetime:
    """Linear due dates are days, not instants.

    Treating a due date as midnight would make everything due today look
    overdue from one minute past midnight, and the whole day would open Urgent.
    """
    return value.replace(hour=23, minute=59, second=59, microsecond=0)


def issue_to_raw_event(
    issue: dict[str, Any], *, assignee_id: str | None = None
) -> RawEvent | None:
    identifier = issue.get("identifier") or issue.get("id")
    if not identifier:
        return None

    if _is_done(issue):
        return None

    # The fetch filters by assignee server-side now, but a webhook delivers
    # whatever it likes, so the guard stays. An unassigned issue is nobody's
    # action.
    assignee = issue.get("assignee") or {}
    if assignee_id is not None and assignee.get("id") != assignee_id:
        return None

    due = _parse(issue.get("dueDate"))
    team = (issue.get("team") or {}).get("key") or ""
    creator = (issue.get("creator") or {}).get("displayName") or ""

    # Priority is deliberately not read. Urgency is the due date alone: a task
    # due today or overdue is urgent, everything else can wait (decided at read
    # time in ``tier_bands._linear_tier``, so it flips on the day it comes due).
    # One signal covers every open assigned issue; the model never runs here.
    return RawEvent(
        source="linear",
        source_ref=f"linear:{identifier}",
        reason="linear",
        subject_type="Issue",
        title=f"{identifier} {issue.get('title') or ''}".strip(),
        body=issue.get("description"),
        url=issue.get("url") or "",
        repo="",
        context_chip=team or "Linear",
        actor=Actor(login=creator, display_name=creator or None),
        deadline=_end_of_day(due) if due else None,
        occurred_at=_parse(issue.get("updatedAt")) or _parse(issue.get("createdAt")),
        labels=[
            label.get("name", "")
            for label in ((issue.get("labels") or {}).get("nodes") or [])
            if isinstance(label, dict)
        ],
        # Assigned by name, but by a system rather than a person waiting in a
        # thread, so it is not treated as somebody being blocked on a reply.
        is_blocking=False,
        raw=issue,
    )


def comment_event_to_raw_event(
    data: dict[str, Any], *, identity: Any | None = None
) -> RawEvent | None:
    """A LINEAR_COMMENT_EVENT_TRIGGER payload: someone commented on an issue.

    The trigger is team-scoped, so it fires for every comment in the team. Two
    things are filtered here: a comment the user wrote themselves is not a thing
    that needs them, and a payload with no issue is unusable. Everything else is
    prose asking something, so it is LLM-in-a-band (``linear_comment``), like a
    Slack mention — the model rates it inside Can wait .. Urgent."""
    issue = data.get("issue") or {}
    identifier = issue.get("identifier") or issue.get("id")
    comment_id = data.get("id")
    if not identifier or not comment_id:
        return None

    author_id = data.get("userId") or (data.get("user") or {}).get("id")
    my_id = getattr(identity, "linear_user_id", None) if identity else None
    if my_id and author_id == my_id:
        return None  # the user's own comment never comes back as needing them

    author = (data.get("user") or {}).get("name") or ""
    team = (issue.get("team") or {}).get("key") or ""
    return RawEvent(
        source="linear",
        # Keyed on the comment, not the issue, so several comments on one issue
        # are distinct rows and none collides with the issue's own feed item.
        source_ref=f"linear:comment:{comment_id}",
        reason="linear_comment",
        subject_type="Comment",
        title=f"{identifier} {issue.get('title') or ''}".strip(),
        body=data.get("body"),
        url=data.get("url") or issue.get("url") or "",
        repo="",
        context_chip=team or "Linear",
        actor=Actor(login=author, display_name=author or None),
        occurred_at=_parse(data.get("createdAt")),
        is_blocking=True,  # a person wrote it and is waiting on a reply
        raw=data,
    )


def issue_stats_from_issues(
    issues: list[dict[str, Any]], *, now: datetime | None = None
) -> dict[str, Any]:
    """Counts by state, plus per-project done/remaining.

    Pure, so the arithmetic can be tested without a workspace. Every figure here
    covers only the issues passed in, which are only ever this user's: crediting
    the user with issues Linear does not attribute to them was how "completed
    this month" ended up describing somebody else's work.

    State is read from ``state.name``. The list payload carries no
    ``state.type``, and reading the absent field is why backlog was invisible.
    """
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    horizon = now + DUE_SOON

    done = backlog = todo = in_progress = 0
    overdue = due_this_week = completed_30d = 0
    projects: dict[str, dict[str, int]] = {}

    for issue in issues:
        name = str((issue.get("state") or {}).get("name") or "").strip().lower()
        project = (issue.get("project") or {}).get("name") or "No project"
        bucket = projects.setdefault(project, {"done": 0, "remaining": 0})

        if name in _DONE_STATES:
            done += 1
            bucket["done"] += 1
            # completedAt only exists when the fetch asked for transitions.
            # Falling back to updatedAt counts a title edit as a completion.
            finished = _parse(issue.get("completedAt"))
            if finished is not None and finished >= cutoff:
                completed_30d += 1
            continue

        bucket["remaining"] += 1
        if "backlog" in name:
            backlog += 1
        elif "progress" in name or "started" in name:
            in_progress += 1
        else:
            todo += 1

        due = _parse(issue.get("dueDate"))
        if due is not None:
            deadline = _end_of_day(due)
            if deadline < now:
                overdue += 1
            elif deadline <= horizon:
                due_this_week += 1

    return {
        "assigned": len(issues),
        "remaining": backlog + todo + in_progress,
        "completed_30d": completed_30d,
        "backlog": backlog,
        "in_progress": in_progress,
        "todo": todo,
        "overdue": overdue,
        "due_this_week": due_this_week,
        "projects": projects,
    }


class ComposioLinearService:
    def __init__(
        self, composio: Any, user_id: str, version: str = LINEAR_TOOLKIT_VERSION
    ) -> None:
        self._composio = composio
        self._user_id = user_id
        self._version = version
        self._me: Any = _UNSET

    def _execute(self, slug: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._composio.tools.execute(
            slug, user_id=self._user_id, arguments=arguments, version=self._version
        )
        if isinstance(result, dict):
            return result.get("data") or {}
        return getattr(result, "data", {}) or {}

    def current_user_id(self) -> str | None:
        """Resolved once and cached, but only on success.

        Caching a *failure* is what poisoned this service for the life of the
        process: the app fires a refresh on every launch, so the first one runs
        before Linear is connected, ``LINEAR_GET_CURRENT_USER`` throws
        ``ConnectedAccountNotFound``, and freezing ``self._me`` to ``None`` meant
        Composio was never asked again even after the account went active. Linear
        stayed empty until a restart. So a failed or empty resolution is left
        unresolved (``_UNSET``) and the next refresh retries; only a real id is
        remembered.
        """
        if self._me is not _UNSET:
            return self._me
        try:
            data = self._execute("LINEAR_GET_CURRENT_USER", {})
            user = data.get("user") or data.get("viewer") or data
            resolved = user.get("id")
        except Exception:
            log.warning("could not resolve the Linear user", exc_info=True)
            return None
        if resolved:
            self._me = resolved
        return resolved

    def assigned_to_me(self) -> list[RawEvent]:
        """Only this user's issues, filtered by Linear rather than by us.

        This filter has to happen server-side. Asking for ``first: 100`` of a
        183-issue workspace and narrowing afterwards returned **none** of the
        user's 31 issues, because all of them sat past position 100 in Linear's
        default order. Linear contributed nothing to the feed at all, which read
        as "no Linear tasks today" rather than as a broken fetch.
        """
        assignee = self.current_user_id()
        if not assignee:
            # Better to show nothing from Linear than to show everybody's.
            log.warning("skipping Linear: no assignee id to filter by")
            return []

        found = [
            issue_to_raw_event(issue, assignee_id=assignee)
            for issue in self.my_issues()
        ]
        return [event for event in found if event is not None]

    def projects(self, limit: int = 20) -> list[dict[str, Any]]:
        try:
            data = self._execute("LINEAR_LIST_LINEAR_PROJECTS", {"first": limit})
        except Exception:
            log.warning("could not list Linear projects", exc_info=True)
            return []
        proj = data.get("projects") or data.get("nodes") or []
        if isinstance(proj, dict):
            proj = proj.get("nodes") or []
        return proj

    def my_issues(self) -> list[dict[str, Any]]:
        """Every issue assigned to this user, filtered by Linear itself.

        ``include_transitions`` is what makes "completed this month" mean
        anything: the plain list payload has no ``completedAt`` at all, so the
        only completion signal available was ``updatedAt``, which moves whenever
        the title or a label changes. The flag caps ``first`` at 25, hence the
        paging loop.
        """
        assignee = self.current_user_id()
        if not assignee:
            return []

        issues: list[dict[str, Any]] = []
        cursor: str | None = None
        # Bounded: the cap is a runaway guard, not an expected page count.
        for _ in range(20):
            arguments: dict[str, Any] = {
                "first": 25,
                "assignee_id": assignee,
                "include_transitions": True,
            }
            if cursor:
                arguments["after"] = cursor
            data = self._execute("LINEAR_LIST_LINEAR_ISSUES", arguments)
            page = data.get("issues") or data.get("nodes") or []
            if isinstance(page, dict):
                page = page.get("nodes") or []
            issues.extend(page)

            info = data.get("page_info") or data.get("pageInfo") or {}
            if not info.get("hasNextPage"):
                break
            cursor = info.get("endCursor")
            if not cursor:
                break
        return issues

    def issue_stats(self) -> dict[str, Any]:
        return issue_stats_from_issues(self.my_issues())

    def comment(self, source_ref: str, body: str) -> None:
        issue_id = source_ref.split(":", 1)[1] if ":" in source_ref else source_ref
        self._execute(
            "LINEAR_CREATE_LINEAR_COMMENT", {"issue_id": issue_id, "body": body}
        )
