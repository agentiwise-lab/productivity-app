"""Connection repository contract.

Run against the in-memory store and the Supabase store (through the postgrest
fake), so the two cannot drift. The cross-user case is the one that matters: a
connection stored for one user must never be returned for another, because a
connection is what lets code read that account.
"""

from __future__ import annotations

import pytest

from backend.repositories.connections import InMemoryConnectionRepository
from backend.repositories.supabase_client import SupabaseClientProvider
from backend.repositories.supabase_connections_repository import (
    SupabaseConnectionRepository,
)
from tests.fake_supabase import FakeSupabaseClient


@pytest.fixture(params=["memory", "supabase"])
def repo(request):
    if request.param == "memory":
        return InMemoryConnectionRepository()
    fake = FakeSupabaseClient()
    return SupabaseConnectionRepository(SupabaseClientProvider(lambda: fake))


def test_mark_active_then_get(repo):
    repo.mark_active(
        "u1", "github", composio_connected_account_id="ca_1", provider_login="octocat"
    )
    row = repo.get("u1", "github")
    assert row is not None
    assert row.composio_connected_account_id == "ca_1"
    assert row.status == "active"
    assert row.provider_login == "octocat"
    assert row.composio_user_id == "u1"


def test_get_is_none_when_absent(repo):
    assert repo.get("u1", "github") is None


def test_mark_active_is_idempotent_per_user_provider(repo):
    repo.mark_active("u1", "github", composio_connected_account_id="ca_old")
    repo.mark_active(
        "u1", "github", composio_connected_account_id="ca_new", provider_login="octo"
    )
    rows = repo.list("u1")
    assert len(rows) == 1
    assert rows[0].composio_connected_account_id == "ca_new"
    assert rows[0].provider_login == "octo"


def test_mark_status_updates_health(repo):
    repo.mark_active("u1", "github", composio_connected_account_id="ca_1")
    repo.mark_status("u1", "github", "expired")
    assert repo.get("u1", "github").status == "expired"


def test_delete_removes_the_row(repo):
    repo.mark_active("u1", "github", composio_connected_account_id="ca_1")
    repo.delete("u1", "github")
    assert repo.get("u1", "github") is None


def test_list_is_scoped_to_the_user(repo):
    repo.mark_active("u1", "github", composio_connected_account_id="ca_a")
    repo.mark_active("u2", "github", composio_connected_account_id="ca_b")
    assert [r.user_id for r in repo.list("u1")] == ["u1"]
    assert repo.get("u2", "github").composio_connected_account_id == "ca_b"
    assert repo.get("u1", "github").composio_connected_account_id == "ca_a"


def test_identity_for_github_reads_the_stored_login(repo):
    repo.mark_active(
        "u1", "github", composio_connected_account_id="ca_1", provider_login="octocat"
    )
    assert repo.identity_for("u1", "github").github_login == "octocat"


def test_identity_for_slack_reads_the_stored_user_id(repo):
    repo.mark_active(
        "u1", "slack", composio_connected_account_id="ca_1", provider_user_id="U123"
    )
    assert repo.identity_for("u1", "slack").slack_user_id == "U123"


def test_identity_for_absent_is_empty(repo):
    ident = repo.identity_for("u1", "github")
    assert ident.github_login is None


def test_identity_for_degrades_to_empty_when_the_store_raises():
    """A webhook can name a user_id that is not a valid uuid; the query then
    raises 22P02. identity_for must return an empty Identity rather than let that
    tear down ingest — the event still processes, just without provider identity
    (BUG-3)."""

    class RaisingClient:
        def table(self, *args, **kwargs):
            raise RuntimeError("invalid input syntax for type uuid: 'pg-test'")

    repo = SupabaseConnectionRepository(SupabaseClientProvider(RaisingClient))
    ident = repo.identity_for("pg-test-not-a-uuid", "github")
    assert ident.github_login is None
    assert ident.slack_user_id is None
