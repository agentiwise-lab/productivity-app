"""Webhook ingest: turning a Composio envelope into a feed item.

The tests that matter most here are the routing ones. An event carries the id of
the user it belongs to, and getting that wrong does not produce a bug report, it
produces one person reading another person's messages. So every path that cannot
name its user must drop the event rather than guess.
"""

from __future__ import annotations

import pytest

from backend.models.tiers import Tier, TypeTag
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.ingest import WebhookIngestService
from tests.fakes import FakeConnectionRepository, FakeGitHubService, build_feed_service

USER = "8f1c2c1e-0000-4000-8000-000000000001"


def envelope(trigger: str, data: dict, user_id: str | None = USER, **metadata) -> dict:
    meta = {"trigger_slug": trigger, "connected_account_id": "ca_1", **metadata}
    if user_id is not None:
        meta["user_id"] = user_id
    return {
        "id": "msg_1",
        "type": "composio.trigger.message",
        "timestamp": "2026-07-23T12:00:00Z",
        "data": data,
        "metadata": meta,
    }


NOTIFICATION = {
    "id": "24512080855",
    "reason": "review_requested",
    "repository": {"full_name": "octo/repo"},
    "subject": {
        "type": "PullRequest",
        "title": "Add rate limiting",
        "url": "https://api.github.com/repos/octo/repo/pulls/42",
    },
    "updated_at": "2026-07-23T11:00:00Z",
}


@pytest.fixture
def ingest():
    repo = InMemoryFeedRepository()
    connections = FakeConnectionRepository()
    service = WebhookIngestService(
        feed=build_feed_service(repo=repo, github=FakeGitHubService()),
        connections=connections,
    )
    return service, repo, connections


# --- routing ---------------------------------------------------------------


def test_an_event_lands_in_the_feed_of_the_user_it_names(ingest):
    service, repo, _ = ingest
    result = service.handle(
        envelope("GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER", NOTIFICATION)
    )

    assert result.handled is True
    items = repo.list_by_user(USER)
    assert len(items) == 1
    assert items[0].source_ref == "octo/repo#42"
    assert items[0].rule_tier is Tier.URGENT
    assert items[0].type_tag is TypeTag.REVIEW


def test_an_event_with_no_user_is_dropped(ingest):
    """The user id lives in metadata, never in data: `data` is the provider's
    payload, whose own `user` field is the *sender*. Falling back to it would
    file events into the wrong account."""
    service, repo, _ = ingest
    result = service.handle(
        envelope(
            "GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER",
            NOTIFICATION | {"user": {"id": "someone-else"}},
            user_id=None,
        )
    )

    assert result.handled is False
    assert repo.list_by_user(USER) == []
    assert repo.list_by_user("someone-else") == []


def test_two_users_events_do_not_cross(ingest):
    service, repo, _ = ingest
    other = "8f1c2c1e-0000-4000-8000-000000000002"
    service.handle(envelope("GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER", NOTIFICATION))
    service.handle(
        envelope(
            "GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER",
            NOTIFICATION,
            user_id=other,
        )
    )

    assert len(repo.list_by_user(USER)) == 1
    assert len(repo.list_by_user(other)) == 1
    assert repo.list_by_user(USER)[0].id != repo.list_by_user(other)[0].id


# --- trigger coverage ------------------------------------------------------


def test_an_assigned_issue_becomes_an_assigned_item(ingest):
    service, repo, _ = ingest
    service.handle(
        envelope(
            "GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER",
            {
                "number": 7,
                "title": "Checkout returns 500",
                "html_url": "https://github.com/octo/repo/issues/7",
                "body": "production is down",
                "labels": [{"name": "P0"}],
                "repository": {"full_name": "octo/repo"},
                "user": {"login": "priya"},
                "updated_at": "2026-07-23T11:30:00Z",
            },
        )
    )

    item = repo.list_by_user(USER)[0]
    assert item.source_ref == "octo/repo#7"
    assert item.type_tag is TypeTag.ASSIGNED
    assert item.sender_handle == "priya"
    # A P0 label is structured urgency, so the rules settle it without a model.
    assert item.rule_tier is Tier.URGENT
    assert item.needs_llm is False


def test_an_unknown_trigger_is_ignored_without_erroring(ingest):
    """A webhook that fails is retried by Composio, so an unmapped trigger must
    not look like a failure or it will be redelivered forever."""
    service, repo, _ = ingest
    result = service.handle(envelope("SOME_TRIGGER_WE_HAVE_NOT_MAPPED_YET", {}))

    assert result.handled is False
    assert result.reason == "unmapped_trigger"
    assert repo.list_by_user(USER) == []


def test_a_malformed_payload_is_dropped_not_raised(ingest):
    service, repo, _ = ingest
    result = service.handle(
        envelope("GITHUB_REPOSITORY_NOTIFICATION_RECEIVED_TRIGGER", {})
    )
    assert result.handled is False
    assert repo.list_by_user(USER) == []


# --- connection lifecycle --------------------------------------------------


def test_an_expired_connection_is_recorded_rather_than_ignored(ingest):
    """Without this the feed for that source just goes quiet, which reads as
    'nothing needs me' when it means 'we lost access' (plan 6.4)."""
    service, repo, connections = ingest
    result = service.handle(
        {
            "id": "msg_2",
            "type": "composio.connected_account.expired",
            "timestamp": "2026-07-23T12:00:00Z",
            "data": {
                "id": "ca_1",
                "user_id": USER,
                "status": "EXPIRED",
                "toolkit": {"slug": "github"},
            },
            "metadata": {"project_id": "p", "org_id": "o"},
        }
    )

    assert result.handled is True
    assert connections.statuses[(USER, "github")] == "expired"
    assert repo.list_by_user(USER) == []
