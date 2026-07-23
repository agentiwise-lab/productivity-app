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

_DONE_STATES = {"completed", "canceled", "cancelled", "done"}


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

    state = issue.get("state") or {}
    state_type = str(state.get("type") or "").lower()
    if state_type in _DONE_STATES:
        return None

    # Linear's list tool accepts an assignee_id argument and ignores it, so the
    # filter has to happen here. Verified against the live workspace: the
    # filtered and unfiltered calls returned identical sets, and the feed filled
    # with other people's issues. An unassigned issue is nobody's action.
    assignee = issue.get("assignee") or {}
    if assignee_id is not None and assignee.get("id") != assignee_id:
        return None

    priority = issue.get("priority")
    due = _parse(issue.get("dueDate"))
    team = (issue.get("team") or {}).get("key") or ""
    creator = (issue.get("creator") or {}).get("displayName") or ""

    if priority == PRIORITY_URGENT:
        reason = "linear_urgent"
    elif priority == PRIORITY_HIGH:
        reason = "linear_high"
    elif due is not None:
        reason = "linear_due"
    else:
        reason = "linear_assigned"

    return RawEvent(
        source="linear",
        source_ref=f"linear:{identifier}",
        reason=reason,
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
        """Cached: it never changes, and every refresh would otherwise pay for
        it again."""
        if self._me is _UNSET:
            try:
                data = self._execute("LINEAR_GET_CURRENT_USER", {})
                user = data.get("user") or data.get("viewer") or data
                self._me = user.get("id")
            except Exception:
                log.warning("could not resolve the Linear user", exc_info=True)
                self._me = None
        return self._me

    def assigned_to_me(self) -> list[RawEvent]:
        """Only this user's issues.

        Without ``assignee_id`` Linear returns the whole workspace, and the feed
        fills with other people's work: fifty issues arrived this way, seven of
        them Urgent, none of them necessarily this user's. A feed that shows
        everyone's tasks is not a feed, it is a backlog.
        """
        assignee = self.current_user_id()
        if not assignee:
            # Better to show nothing from Linear than to show everybody's.
            log.warning("skipping Linear: no assignee id to filter by")
            return []

        data = self._execute("LINEAR_LIST_LINEAR_ISSUES", {"first": 100})
        issues = data.get("issues") or data.get("nodes") or []
        if isinstance(issues, dict):
            issues = issues.get("nodes") or []
        found = [
            issue_to_raw_event(issue, assignee_id=assignee) for issue in issues
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

    def issue_stats(self) -> dict[str, int]:
        """Assigned, completed in 30 days, and overdue, for the dashboard."""
        assignee = self.current_user_id()
        data = self._execute("LINEAR_LIST_LINEAR_ISSUES", {"first": 100})
        issues = data.get("issues") or data.get("nodes") or []
        if isinstance(issues, dict):
            issues = issues.get("nodes") or []
        mine = [
            i for i in issues if (i.get("assignee") or {}).get("id") == assignee
        ]

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        now = datetime.now(timezone.utc)
        completed = 0
        overdue = 0
        open_count = 0
        for issue in mine:
            state = str((issue.get("state") or {}).get("type") or "").lower()
            if state in _DONE_STATES:
                done_at = _parse(issue.get("completedAt") or issue.get("updatedAt"))
                if done_at and done_at >= cutoff:
                    completed += 1
                continue
            open_count += 1
            due = _parse(issue.get("dueDate"))
            if due is not None and _end_of_day(due) < now:
                overdue += 1
        return {
            "assigned_open": open_count,
            "completed_30d": completed,
            "overdue": overdue,
        }

    def comment(self, source_ref: str, body: str) -> None:
        issue_id = source_ref.split(":", 1)[1] if ":" in source_ref else source_ref
        self._execute(
            "LINEAR_CREATE_LINEAR_COMMENT", {"issue_id": issue_id, "body": body}
        )
