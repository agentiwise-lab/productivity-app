"""The connections service: what the user has actually connected.

The bug these tests exist to prevent: the app used to derive its connection list
from whatever sources appeared in the feed, so a source with nothing to say was
indistinguishable from a source that was never connected, and four live
integrations were invisible. Sources is a menu, so every entry is always
present and only its status changes.
"""

from __future__ import annotations

import pytest

from backend.models.feed import FeedItem
from backend.models.sources import CATALOGUE, ConnectionStatus, Source
from backend.models.tiers import Tier, TypeTag
from backend.repositories.connections import InMemoryConnectionRepository
from backend.services.connections import DefaultConnectionService, MissingAuthConfig
from backend.services.triggers import DefaultTriggerProvisioner

AUTH_CONFIGS = {source: f"ac_{source.value}" for source, _, _ in CATALOGUE}


class FakeConnectedAccounts:
    def __init__(self, rows=None, error: Exception | None = None):
        self._rows = rows or []
        self._error = error
        self.linked: list = []
        self.deleted: list = []

    def list(self, **kwargs):
        if self._error:
            raise self._error
        toolkits = kwargs.get("toolkit_slugs")
        rows = self._rows
        if toolkits:
            rows = [
                row
                for row in rows
                if (row.get("toolkit") or {}).get("slug") in toolkits
            ]
        return type("R", (), {"items": rows})()

    def link(self, user_id, auth_config_id, callback_url=None):
        self.linked.append((user_id, auth_config_id, callback_url))
        return type(
            "Req",
            (),
            {"redirect_url": f"https://composio/oauth/{auth_config_id}", "id": "req_1"},
        )()

    def delete(self, account_id):
        self.deleted.append(account_id)


class FakeTools:
    def __init__(self, identity=None):
        self._identity = identity or {}

    def execute(self, slug, user_id=None, arguments=None, version=None):
        return {"data": self._identity.get(slug, {})}


class FakeTriggers:
    """Enough of the triggers API for the real provisioner to run against."""

    def __init__(self):
        self.created: list = []

    def list_active(self, connected_account_ids=None, **kwargs):
        return type("R", (), {"items": []})()

    def create(self, slug, user_id=None, connected_account_id=None, trigger_config=None):
        self.created.append((slug, user_id, connected_account_id))
        return type("T", (), {"id": "ti_1"})()


class FakeComposio:
    def __init__(self, rows=None, error=None, identity=None):
        self.connected_accounts = FakeConnectedAccounts(rows, error)
        self.tools = FakeTools(identity)
        self.triggers = FakeTriggers()


def account(toolkit: str, status: str = "ACTIVE", ident: str = "ca_1"):
    return {"toolkit": {"slug": toolkit}, "status": status, "id": ident}


def make(rows=None, error=None, identity=None, repo=None):
    """Returns (service, composio, repo) so tests can inspect side effects."""
    composio = FakeComposio(rows, error, identity)
    repo = repo or InMemoryConnectionRepository()
    service = DefaultConnectionService(
        composio,
        auth_config_ids=AUTH_CONFIGS,
        repo=repo,
        provisioner=DefaultTriggerProvisioner(composio),
        callback_url="https://cb",
    )
    return service, composio, repo


def build(rows=None, error=None):
    return make(rows, error)[0]


def item(source: str, tier: Tier = Tier.TODAY) -> FeedItem:
    return FeedItem(
        id=f"i-{source}-{tier.value}",
        user_id="u1",
        source=source,
        source_ref=f"{source}:1",
        rule_tier=tier,
        type_tag=TypeTag.FYI,
        title="x",
        url="https://example.com",
    )


# --- the catalogue is always complete ---------------------------------------


def test_every_supported_source_is_listed_even_with_nothing_connected():
    sources = build().list_sources("u1", items=[])
    assert [s.source for s in sources] == [row[0] for row in CATALOGUE]
    assert all(s.status is ConnectionStatus.DISCONNECTED for s in sources)


def test_the_order_is_fixed_and_does_not_follow_the_data():
    """A list that reorders itself as counts change is unusable: the thing you
    reached for is somewhere else by the time you look again."""
    busy = [item("linear") for _ in range(9)]
    sources = build().list_sources("u1", items=busy)
    assert [s.source for s in sources] == [row[0] for row in CATALOGUE]


def test_a_connected_toolkit_is_marked_connected():
    service = build([account("googlecalendar"), account("linear")])
    by_source = {s.source: s for s in service.list_sources("u1", items=[])}

    assert by_source[Source.CALENDAR].status is ConnectionStatus.CONNECTED
    assert by_source[Source.LINEAR].status is ConnectionStatus.CONNECTED
    assert by_source[Source.GMAIL].status is ConnectionStatus.DISCONNECTED


def test_an_active_record_wins_over_an_abandoned_one_for_the_same_toolkit():
    """Composio keeps a row per authorisation attempt, so one toolkit can hold
    both a dead attempt and a working connection. Reporting the dead one would
    tell the user Calendar is broken while it is quietly working."""
    service = build(
        [
            account("googlecalendar", "EXPIRED", "ca_dead"),
            account("googlecalendar", "ACTIVE", "ca_live"),
        ]
    )
    calendar = next(
        s for s in service.list_sources("u1", items=[]) if s.source is Source.CALENDAR
    )

    assert calendar.status is ConnectionStatus.CONNECTED
    assert calendar.connected_account_id == "ca_live"


def test_an_expired_connection_with_no_replacement_is_reported_expired():
    service = build([account("github", "EXPIRED")])
    github = next(
        s for s in service.list_sources("u1", items=[]) if s.source is Source.GITHUB
    )
    assert github.status is ConnectionStatus.EXPIRED


@pytest.mark.parametrize("status", ["INITIATED", "INITIALIZING"])
def test_a_half_finished_authorisation_is_not_a_connection(status):
    service = build([account("slack", status)])
    slack = next(
        s for s in service.list_sources("u1", items=[]) if s.source is Source.SLACK
    )
    assert slack.status is ConnectionStatus.DISCONNECTED


# --- counts -----------------------------------------------------------------


def test_counts_come_from_the_live_feed_and_exclude_noise():
    service = build([account("github")])
    items = [
        item("github", Tier.URGENT),
        item("github", Tier.TODAY),
        item("github", Tier.NOISE),
    ]
    github = next(
        s for s in service.list_sources("u1", items=items) if s.source is Source.GITHUB
    )
    assert (github.count, github.urgent) == (2, 1)


# --- failure ----------------------------------------------------------------


def test_composio_being_down_still_returns_the_full_catalogue():
    """Sources must render its skeleton even when status cannot be fetched. An
    empty screen would say "you have connected nothing", which is a lie."""
    sources = build(error=RuntimeError("composio down")).list_sources("u1", items=[])
    assert len(sources) == len(CATALOGUE)
    assert all(s.status is ConnectionStatus.ERROR for s in sources)


# --- link / status / disconnect ---------------------------------------------


def test_link_url_uses_the_right_auth_config_and_app_user():
    service, composio, _ = make()
    url = service.link_url("u1", Source.GITHUB)
    assert composio.connected_accounts.linked == [("u1", "ac_github", "https://cb")]
    assert url == "https://composio/oauth/ac_github"


def test_link_url_without_an_auth_config_is_refused():
    composio = FakeComposio()
    service = DefaultConnectionService(
        composio,
        auth_config_ids={},
        repo=InMemoryConnectionRepository(),
        provisioner=DefaultTriggerProvisioner(composio),
    )
    with pytest.raises(MissingAuthConfig):
        service.link_url("u1", Source.GITHUB)


def test_status_on_active_persists_the_row_with_identity():
    service, _, repo = make(
        rows=[account("github", "ACTIVE", "ca_live")],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    info = service.status("u1", Source.GITHUB)
    assert info.status is ConnectionStatus.CONNECTED
    row = repo.get("u1", "github")
    assert row.composio_connected_account_id == "ca_live"
    assert row.provider_login == "octocat"
    assert repo.identity_for("u1", "github").github_login == "octocat"


def test_status_while_still_pending_writes_nothing():
    service, _, repo = make(rows=[account("github", "INITIATED")])
    info = service.status("u1", Source.GITHUB)
    assert info.status is ConnectionStatus.DISCONNECTED
    assert repo.get("u1", "github") is None


def test_disconnect_deletes_the_account_and_clears_the_row():
    repo = InMemoryConnectionRepository()
    repo.mark_active("u1", "github", composio_connected_account_id="ca_live")
    service, composio, _ = make(repo=repo)
    service.disconnect("u1", Source.GITHUB)
    assert composio.connected_accounts.deleted == ["ca_live"]
    assert repo.get("u1", "github") is None


# --- finalize: the reconcile that closes the event loop ----------------------


def test_finalize_on_active_provisions_the_source_triggers():
    """The whole point of the fix: a source going active must create its
    triggers, or the feed never fills. This is the step the app used to skip."""
    service, composio, _ = make(
        rows=[account("github", "ACTIVE", "ca_live")],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    info = service.finalize("u1", Source.GITHUB)

    assert info.status is ConnectionStatus.CONNECTED
    created = [(slug, account_id) for slug, _uid, account_id in composio.triggers.created]
    assert created == [("GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER", "ca_live")]


def test_finalize_writes_the_row_before_provisioning():
    service, _, repo = make(
        rows=[account("github", "ACTIVE", "ca_live")],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    service.finalize("u1", Source.GITHUB)
    row = repo.get("u1", "github")
    assert row is not None
    assert row.composio_connected_account_id == "ca_live"
    assert repo.identity_for("u1", "github").github_login == "octocat"


def test_finalize_is_idempotent():
    """Called on every poll, so a second run must not duplicate the row or the
    trigger create."""
    service, composio, repo = make(
        rows=[account("github", "ACTIVE", "ca_live")],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    # After the first finalize, list_active reports the trigger as present.
    created_slugs: list[str] = []
    original = composio.triggers.create

    def recording(slug, **kwargs):
        created_slugs.append(slug)
        return original(slug, **kwargs)

    def list_active(connected_account_ids=None, **kwargs):
        items = [{"trigger_name": s} for s in created_slugs]
        return type("R", (), {"items": items})()

    composio.triggers.create = recording
    composio.triggers.list_active = list_active

    service.finalize("u1", Source.GITHUB)
    service.finalize("u1", Source.GITHUB)

    assert created_slugs == ["GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER"]
    assert len(repo.list("u1")) == 1


def test_finalize_discards_stale_half_finished_attempts():
    """Composio keeps a row per authorisation attempt. Once a live one exists,
    the abandoned INITIATED/INITIALIZING attempts for the same toolkit are
    deleted so they cannot accumulate (BUG-11)."""
    service, composio, _ = make(
        rows=[
            account("github", "INITIATED", "ca_stale1"),
            account("github", "ACTIVE", "ca_live"),
            account("github", "INITIALIZING", "ca_stale2"),
        ],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    service.finalize("u1", Source.GITHUB)
    assert set(composio.connected_accounts.deleted) == {"ca_stale1", "ca_stale2"}


def test_finalize_does_not_delete_a_broken_prior_connection():
    """An EXPIRED account is meaningful history, not a half-finished attempt, so
    dedupe leaves it alone even when a live one exists."""
    service, composio, _ = make(
        rows=[
            account("github", "EXPIRED", "ca_old"),
            account("github", "ACTIVE", "ca_live"),
        ],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    service.finalize("u1", Source.GITHUB)
    assert composio.connected_accounts.deleted == []


def test_finalize_defers_provisioning_to_the_background_runner():
    """The status poll flips to connected as soon as the row is written; trigger
    provisioning and stale cleanup run off the critical path so the UI is not held
    up by several more Composio calls."""
    deferred: list = []
    composio = FakeComposio(
        rows=[account("github", "ACTIVE", "ca_live")],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    repo = InMemoryConnectionRepository()
    service = DefaultConnectionService(
        composio,
        auth_config_ids=AUTH_CONFIGS,
        repo=repo,
        provisioner=DefaultTriggerProvisioner(composio),
        background=deferred.append,
    )

    info = service.finalize("u1", Source.GITHUB)

    # Connected and the row is written immediately...
    assert info.status is ConnectionStatus.CONNECTED
    assert repo.get("u1", "github") is not None
    # ...but the triggers have NOT been created yet — that work is queued.
    assert composio.triggers.created == []
    assert len(deferred) == 1

    # Running the queued work provisions the trigger.
    deferred[0]()
    assert [c[0] for c in composio.triggers.created] == [
        "GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER"
    ]


def test_finalize_while_still_pending_writes_and_provisions_nothing():
    service, composio, repo = make(rows=[account("github", "INITIATED")])
    info = service.finalize("u1", Source.GITHUB)
    assert info.status is ConnectionStatus.DISCONNECTED
    assert repo.get("u1", "github") is None
    assert composio.triggers.created == []


def test_status_delegates_to_finalize():
    """The status poll and list-sources heal share one reconcile, so a poll
    provisions exactly like finalize does."""
    service, composio, repo = make(
        rows=[account("github", "ACTIVE", "ca_live")],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    service.status("u1", Source.GITHUB)
    assert repo.get("u1", "github") is not None
    assert composio.triggers.created


def test_list_sources_heals_a_connected_source_missing_its_row():
    """RC-2: if the poll missed the moment the account went active, the row and
    triggers were never written. Listing sources reconciles it, so the feed is
    not left broken just because of timing."""
    service, composio, repo = make(
        rows=[account("github", "ACTIVE", "ca_live")],
        identity={"GITHUB_GET_THE_AUTHENTICATED_USER": {"login": "octocat"}},
    )
    assert repo.get("u1", "github") is None  # nothing persisted yet

    sources = service.list_sources("u1", items=[])

    github = next(s for s in sources if s.source is Source.GITHUB)
    assert github.status is ConnectionStatus.CONNECTED
    assert repo.get("u1", "github") is not None  # healed
    assert composio.triggers.created  # and provisioned


def test_list_sources_does_not_re_finalize_an_already_healed_source():
    """Once the row exists, feed loads must not keep re-resolving identity and
    re-provisioning on every call."""
    repo = InMemoryConnectionRepository()
    repo.mark_active(
        "u1", "github", composio_connected_account_id="ca_live", provider_login="octocat"
    )
    service, composio, _ = make(
        rows=[account("github", "ACTIVE", "ca_live")], repo=repo
    )
    service.list_sources("u1", items=[])
    assert composio.triggers.created == []
