"""GitHub via Composio.

Satisfies the same ``GitHubService`` contract as a direct GitHub App client, so
nothing downstream (classification, scoring, feed, API) knows the difference.
Using Composio's managed auth means no GitHub App registration is required.

Swapping to your own OAuth credentials later is a Composio auth-config change,
not a change to this file.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.integrations.github import Comment, PRRef, PullRequest
from backend.models.events import RawEvent
from backend.models.feed import Actor

# GitHub caps notification pages at 50.
_PAGE_SIZE = 50

# Composio requires an explicit toolkit version for manual execution, and
# refuses "latest". Pinning is the better behaviour anyway: an upstream tool
# revision cannot silently change the payload shape our mappers depend on.
# Bumping it is a deliberate change with the fixtures re-checked.
GITHUB_TOOLKIT_VERSION = "20260721_00"

# Reasons that mean another person is waiting on this user to act.
_BLOCKING_REASONS = {"review_requested", "approval_requested", "assign"}

# subject.type -> the path segment github.com uses for that object.
_SUBJECT_PATH = {"PullRequest": "pull", "Issue": "issues"}


_REASON_TEXT = {
    "review_requested": "Your review was requested on this pull request.",
    "approval_requested": "Your approval is required before this can proceed.",
    "assign": "This was assigned to you.",
    "mention": "You were mentioned here.",
    "team_mention": "A team you belong to was mentioned here.",
    "comment": "There is a new comment on a thread you are part of.",
    "author": "You opened this, and there has been activity on it.",
    "subscribed": "You are watching this repository.",
    "state_change": "This was opened, closed or merged.",
    "ci_activity": "A workflow run finished.",
    "security_alert": "A security alert was raised on this repository.",
    "invitation": "You were invited to this repository.",
}


def _days_ago(days: int) -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def _describe(reason: str, subject_type: str, repo: str, number: int | None) -> str:
    what = _REASON_TEXT.get(reason, f"GitHub notification ({reason or 'unknown'}).")
    where = f"{subject_type or 'Item'}"
    if number is not None:
        where += f" #{number}"
    return f"{what}\n\n{where} in {repo}."


def _parse_time(value: str | None) -> datetime | None:
    """GitHub's own timestamp for the thread.

    Without it, ingest falls back to the clock and every polled item claims to
    have happened just now: the card reads "now" for a three-day-old review
    request, and age pressure ranks it as if it had only just arrived.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_number(subject_url: str | None) -> int | None:
    """Pull the object number off an api.github.com subject URL."""
    if not subject_url:
        return None
    tail = subject_url.rstrip("/").rsplit("/", 1)[-1]
    return int(tail) if tail.isdigit() else None


def notification_to_raw_event(notification: dict[str, Any]) -> RawEvent:
    """Map one GitHub notification thread onto our source-agnostic RawEvent.

    ``subject.url`` is an API URL, so the browser URL the feed links to is
    rebuilt from the repo and object number.
    """
    repo = (notification.get("repository") or {}).get("full_name", "")
    subject = notification.get("subject") or {}
    number = _extract_number(subject.get("url"))
    path = _SUBJECT_PATH.get(subject.get("type") or "")

    if number is not None:
        source_ref = f"{repo}#{number}"
        url = (
            f"https://github.com/{repo}/{path}/{number}"
            if path
            else f"https://github.com/{repo}"
        )
    else:
        # Releases, discussions and similar have no numeric subject URL.
        source_ref = f"{repo}@{notification.get('id', '')}"
        url = f"https://github.com/{repo}"

    reason = notification.get("reason") or ""
    return RawEvent(
        # GitHub's notification API returns no message body at all, so a row
        # would otherwise show a repository name and nothing else. This says
        # what the notification actually is, in GitHub's own vocabulary.
        body=_describe(reason, subject.get("type") or "", repo, number),
        occurred_at=_parse_time(notification.get("updated_at")),
        source="github",
        source_ref=source_ref,
        reason=reason,
        subject_type=subject.get("type") or "",
        title=subject.get("title") or "",
        url=url,
        repo=repo,
        is_blocking=reason in _BLOCKING_REASONS,
        raw=notification,
    )


class ComposioGitHubService:
    """GitHubService implementation backed by Composio tool calls."""

    def __init__(
        self, composio: Any, user_id: str, version: str = GITHUB_TOOLKIT_VERSION
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

    def list_notifications(self, since: datetime | None = None) -> list[RawEvent]:
        arguments: dict[str, Any] = {"per_page": _PAGE_SIZE}
        if since is not None:
            # Verified against the live API: `all` without `since` returns zero
            # results, so the two always travel together.
            arguments["all"] = True
            arguments["since"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")

        data = self._execute("GITHUB_LIST_NOTIFICATIONS", arguments)
        return [
            notification_to_raw_event(n) for n in (data.get("notifications") or [])
        ]

    def get_pull_request(self, ref: PRRef) -> PullRequest:
        owner, _, name = ref.repo.partition("/")
        data = self._execute(
            "GITHUB_GET_A_PULL_REQUEST",
            {"owner": owner, "repo": name, "pull_number": ref.number},
        )
        return PullRequest(
            ref=ref,
            title=data.get("title") or "",
            url=data.get("html_url") or "",
            author=Actor(login=(data.get("user") or {}).get("login", "")),
            requested_reviewers=[
                Actor(login=(r or {}).get("login", ""))
                for r in (data.get("requested_reviewers") or [])
            ],
            mergeable=data.get("mergeable"),
        )

    def comment_on_pull_request(self, ref: PRRef, body: str) -> Comment:
        # PR discussion comments go through GitHub's issue-comment surface, so
        # issue_number here is the pull request number.
        owner, _, name = ref.repo.partition("/")
        data = self._execute(
            "GITHUB_CREATE_AN_ISSUE_COMMENT",
            {"owner": owner, "repo": name, "issue_number": ref.number, "body": body},
        )
        return Comment(
            id=str(data.get("id", "")), url=data.get("html_url") or "", body=body
        )

    def repositories(self, limit: int = 8) -> list[dict[str, Any]]:
        """The user's repositories, most recently pushed first."""
        data = self._execute(
            "GITHUB_LIST_REPOSITORIES_FOR_THE_AUTHENTICATED_USER",
            {"per_page": 30, "sort": "pushed"},
        )
        repos = data.get("repositories") or data.get("items") or []
        if isinstance(data, list):
            repos = data
        return repos[:limit]

    def repo_activity(self, logins: set[str]) -> list[dict[str, Any]]:
        """Per repository: commits by this user and open PRs, last 30 days.

        Bounded to the most recently pushed repos and fetched in parallel: one
        commit call per repo in series would make the page crawl.
        """
        repos = self.repositories(limit=8)
        since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )

        def one(repo: dict[str, Any]) -> dict[str, Any]:
            full = repo.get("full_name") or ""
            owner, _, name = full.partition("/")
            commits = 0
            try:
                data = self._execute(
                    "GITHUB_LIST_COMMITS",
                    {"owner": owner, "repo": name, "since": since, "per_page": 100},
                )
                items = data.get("commits") or data.get("items") or []
                commits = sum(
                    1
                    for cm in items
                    if ((cm.get("author") or {}).get("login") or "").lower()
                    in {a.lower() for a in logins}
                )
            except Exception:
                pass
            merged = self._search_count(f"repo:{full} is:pr is:merged author:@me")
            open_prs = self._search_count(f"repo:{full} is:pr is:open author:@me")
            return {
                "full_name": full,
                "url": repo.get("html_url") or f"https://github.com/{full}",
                "commits": commits,
                "merged_prs": merged,
                "open_prs": open_prs,
                "pushed_at": repo.get("pushed_at"),
            }

        with ThreadPoolExecutor(max_workers=min(8, len(repos) or 1)) as pool:
            return list(pool.map(one, repos))

    def activity_summary(self) -> dict[str, int]:
        """Cheap counts for the dashboard: PRs open and merged recently. Each is
        one search call."""
        return {
            "open_prs": self._search_count("is:pr is:open author:@me"),
            "merged_prs": self._search_count(
                "is:pr is:merged author:@me merged:>=" + _days_ago(30)
            ),
        }

    def _search_count(self, query: str) -> int:
        data = self._execute("GITHUB_FIND_PULL_REQUESTS", {"query": query})
        total = data.get("total_count")
        if isinstance(total, int):
            return total
        return len(data.get("items") or data.get("pull_requests") or [])

    def open_pull_request_count(self) -> int | None:
        """Pull requests this user has open, across every repository."""
        data = self._execute(
            "GITHUB_FIND_PULL_REQUESTS", {"state": "open", "query": "is:pr author:@me"}
        )
        items = data.get("items") or data.get("pull_requests") or []
        total = data.get("total_count")
        return int(total) if isinstance(total, int) else len(items)

    def approve_pull_request(self, ref: PRRef, body: str = "") -> None:
        owner, _, name = ref.repo.partition("/")
        self._execute(
            "GITHUB_CREATE_A_REVIEW_FOR_A_PULL_REQUEST",
            {
                "owner": owner,
                "repo": name,
                "pull_number": ref.number,
                "event": "APPROVE",
                "body": body,
            },
        )
