"""Linear: what reaches the feed, and what the dashboard counts.

Two live findings drive every test here, both verified against the real
workspace on 2026-07-24:

1. ``LINEAR_LIST_LINEAR_ISSUES`` returns ``state`` with exactly one key,
   ``name``. There is no ``state.type``. Filtering Done by ``state.type`` never
   fires, so completed issues would reach the feed.
2. The list call is workspace-wide. Fetching ``first: 100`` of a 183-issue
   workspace and filtering client-side returned **zero** of the user's issues,
   because all 31 sat past position 100. Linear contributed nothing to the feed.
   Passing ``assignee_id`` to the tool does work, despite an older comment here
   claiming otherwise.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.integrations.linear import (
    ComposioLinearService,
    issue_stats_from_issues,
    issue_to_raw_event,
)

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _issue(**overrides):
    """A minimal issue in the shape the live list call actually returns."""
    issue = {
        "id": "uuid-1",
        "identifier": "AGE-52",
        "title": "Admin dashboard",
        "state": {"name": "Backlog"},
        "assignee": {"id": "me"},
        "project": {"name": "Doorstead"},
        "team": {"key": "AGE"},
        "dueDate": None,
        "priority": 0,
        "updatedAt": "2026-07-23T18:55:10.776Z",
        "createdAt": "2026-06-26T06:51:05.679Z",
        "url": "https://linear.app/x/issue/AGE-52",
    }
    issue.update(overrides)
    return issue


class _FakeTools:
    def __init__(self, payloads):
        self._payloads = payloads
        self.calls: list[tuple] = []

    def execute(self, slug, user_id=None, arguments=None, version=None):
        self.calls.append((slug, arguments))
        return {"data": self._payloads.get(slug, {})}


class _FakeComposio:
    def __init__(self, payloads):
        self.tools = _FakeTools(payloads)


# ------------------------------------------------------- the mapper (feed)


def test_done_issues_are_dropped_by_state_name():
    """``state.type`` does not exist in the list payload, so a Done issue read
    through it slips into the feed as live work."""
    assert issue_to_raw_event(_issue(state={"name": "Done"}), assignee_id="me") is None
    assert (
        issue_to_raw_event(_issue(state={"name": "Canceled"}), assignee_id="me") is None
    )


def test_an_open_issue_still_reaches_the_feed():
    event = issue_to_raw_event(_issue(), assignee_id="me")
    assert event is not None
    assert event.source_ref == "linear:AGE-52"


def test_backlog_with_no_due_date_is_noise_so_it_lands_in_later():
    """Home is what needs you now. An untouched backlog item with no date is
    real work, but it does not belong in front of the user today."""
    event = issue_to_raw_event(_issue(), assignee_id="me")
    assert event.reason == "linear_backlog"


def test_in_progress_reaches_home():
    event = issue_to_raw_event(_issue(state={"name": "In Progress"}), assignee_id="me")
    assert event.reason == "linear_in_progress"


def test_a_due_date_outranks_the_backlog_state():
    event = issue_to_raw_event(_issue(dueDate="2026-07-21"), assignee_id="me")
    assert event.reason == "linear_due"
    assert event.deadline == datetime(2026, 7, 21, 23, 59, 59, tzinfo=timezone.utc)


def test_another_persons_issue_never_reaches_this_feed():
    assert issue_to_raw_event(_issue(assignee={"id": "someone"}), assignee_id="me") is None


def test_an_unassigned_issue_is_nobodys_action():
    issue = _issue()
    del issue["assignee"]
    assert issue_to_raw_event(issue, assignee_id="me") is None


# --------------------------------------------------------- the fetch (scope)


def test_assigned_to_me_filters_server_side():
    """The whole Linear gap: filtering client-side after ``first: 100`` of a
    183-issue workspace returned none of the user's 31 issues."""
    client = _FakeComposio(
        {
            "LINEAR_GET_CURRENT_USER": {"user": {"id": "me"}},
            "LINEAR_LIST_LINEAR_ISSUES": {"issues": [_issue()]},
        }
    )
    service = ComposioLinearService(client, user_id="u")
    service.assigned_to_me()

    listed = [args for slug, args in client.tools.calls if slug == "LINEAR_LIST_LINEAR_ISSUES"]
    assert listed, "no issue list call was made"
    assert listed[0]["assignee_id"] == "me"


def test_the_issue_fetch_pages_until_linear_says_it_is_done():
    """``include_transitions`` caps a page at 25. Without paging, a user with
    more than 25 issues silently loses the rest."""

    class _PagingTools(_FakeTools):
        def execute(self, slug, user_id=None, arguments=None, version=None):
            self.calls.append((slug, arguments))
            if slug == "LINEAR_GET_CURRENT_USER":
                return {"data": {"user": {"id": "me"}}}
            first_page = "after" not in (arguments or {})
            return {
                "data": {
                    "issues": [_issue(identifier="AGE-1" if first_page else "AGE-2")],
                    "page_info": {
                        "hasNextPage": first_page,
                        "endCursor": "cursor-1",
                    },
                }
            }

    client = _FakeComposio({})
    client.tools = _PagingTools({})
    service = ComposioLinearService(client, user_id="u")

    issues = service.my_issues()
    assert [i["identifier"] for i in issues] == ["AGE-1", "AGE-2"]


def test_no_assignee_means_no_linear_rather_than_everybodys_work():
    client = _FakeComposio({"LINEAR_GET_CURRENT_USER": {}})
    service = ComposioLinearService(client, user_id="u")
    assert service.assigned_to_me() == []


# ------------------------------------------------------------ the dashboard


def test_stats_count_only_the_users_own_issues():
    """The user's July completions are unassigned in Linear. Counting them
    would credit them work the tool cannot attribute to them."""
    stats = issue_stats_from_issues(
        [
            _issue(state={"name": "Done"}, completedAt="2026-07-23T10:00:00Z"),
            _issue(state={"name": "Backlog"}),
        ],
        now=NOW,
    )
    assert stats["assigned"] == 2
    assert stats["completed_30d"] == 1
    assert stats["backlog"] == 1
    assert stats["remaining"] == 1


def test_completed_uses_the_completion_time_not_the_last_edit():
    """``updatedAt`` moves whenever anything on the issue changes, so a title
    fix on an issue finished in June would count as finished this month."""
    stats = issue_stats_from_issues(
        [
            _issue(
                state={"name": "Done"},
                completedAt="2026-06-10T20:26:05Z",
                updatedAt="2026-07-24T09:00:00Z",
            )
        ],
        now=NOW,
    )
    assert stats["completed_30d"] == 0


def test_due_this_week_counts_only_open_issues_due_within_seven_days():
    stats = issue_stats_from_issues(
        [
            _issue(dueDate="2026-07-27"),                        # in range
            _issue(dueDate="2026-08-20"),                        # too far
            _issue(dueDate="2026-07-21"),                        # already overdue
            _issue(state={"name": "Done"}, dueDate="2026-07-27"),  # finished
        ],
        now=NOW,
    )
    assert stats["due_this_week"] == 1
    assert stats["overdue"] == 1


def test_projects_only_cover_projects_the_user_has_issues_in():
    stats = issue_stats_from_issues(
        [
            _issue(project={"name": "Doorstead"}),
            _issue(state={"name": "Done"}, project={"name": "Glued"},
                   completedAt="2026-07-20T10:00:00Z"),
        ],
        now=NOW,
    )
    assert set(stats["projects"]) == {"Doorstead", "Glued"}
    assert stats["projects"]["Doorstead"] == {"done": 0, "remaining": 1}
    assert stats["projects"]["Glued"] == {"done": 1, "remaining": 0}
