"""The trigger provisioner: the step that was simply missing.

The app linked OAuth accounts but never created the Composio trigger instances
that drive the feed, so "connect GitHub → assign an issue → see it" had nothing
polling on the other end. These tests pin the one job of this module: when a
source goes active, create exactly the triggers whose slugs ingest already knows
how to map, once, and never a duplicate.
"""

from __future__ import annotations

import pytest

from backend.models.sources import Source
from backend.services.ingest import _MAPPERS
from backend.services.triggers import (
    _LINEAR_TEAM_TRIGGERS,
    _TRIGGERS,
    DefaultTriggerProvisioner,
)


class FakeTriggers:
    """Records create calls and answers list_active from a fixed set of
    already-active slugs, so a test can assert both "created the right slug" and
    "skipped one that already existed"."""

    def __init__(self, existing: list[str] | None = None, list_error: Exception | None = None):
        self.existing = existing or []
        self.created: list[tuple[str, str | None, str | None, dict | None]] = []
        self._list_error = list_error

    def list_active(self, connected_account_ids=None, **kwargs):
        if self._list_error:
            raise self._list_error
        account_id = (connected_account_ids or [None])[0]
        items = [
            {"trigger_name": name, "connected_account_id": account_id}
            for name in self.existing
        ]
        return type("R", (), {"items": items})()

    def create(self, slug, user_id=None, connected_account_id=None, trigger_config=None):
        self.created.append((slug, user_id, connected_account_id, trigger_config))
        return type("T", (), {"id": "ti_1"})()


class FakeTools:
    """Answers LINEAR_LIST_LINEAR_TEAMS so the Linear provisioning path can run."""

    def __init__(self, teams: list[str]):
        self._teams = teams

    def execute(self, slug, user_id=None, arguments=None, version=None):
        if slug == "LINEAR_LIST_LINEAR_TEAMS":
            return {"data": {"teams": [{"id": t} for t in self._teams]}}
        return {"data": {}}


class FakeComposio:
    def __init__(
        self, triggers: FakeTriggers | None = None, teams: list[str] | None = None
    ):
        self.triggers = triggers or FakeTriggers()
        self.tools = FakeTools(teams or [])


# --- the map is honest -------------------------------------------------------


def test_every_provisioned_slug_has_an_ingest_mapper():
    """A trigger we create but cannot map would deliver events that get received,
    verified, and silently dropped. Provisioning and ingest must agree."""
    for slugs in _TRIGGERS.values():
        for slug, _config in slugs:
            assert slug in _MAPPERS, f"{slug} is provisioned but has no ingest mapper"
    # The dynamic (per-team) Linear triggers are held to the same contract.
    for slug in _LINEAR_TEAM_TRIGGERS:
        assert slug in _MAPPERS, f"{slug} is provisioned but has no ingest mapper"


# --- creates the right triggers ---------------------------------------------


def test_github_provisions_the_assigned_issue_trigger():
    fake = FakeComposio()
    DefaultTriggerProvisioner(fake).provision("u1", Source.GITHUB, "ca_live")

    created_slugs = [c[0] for c in fake.triggers.created]
    assert created_slugs == ["GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER"]
    slug, user_id, account_id, config = fake.triggers.created[0]
    # user_id is required because the project has 2FA; the account is pinned.
    assert (user_id, account_id) == ("u1", "ca_live")


def test_slack_provisions_both_message_triggers():
    fake = FakeComposio()
    DefaultTriggerProvisioner(fake).provision("u1", Source.SLACK, "ca_slack")

    assert {c[0] for c in fake.triggers.created} == {
        "SLACK_DIRECT_MESSAGE_RECEIVED",
        "SLACK_CHANNEL_MESSAGE_RECEIVED",
    }


def test_a_source_with_no_triggers_is_a_no_op():
    fake = FakeComposio()
    DefaultTriggerProvisioner(fake).provision("u1", Source.GOOGLE_DOCS, "ca_docs")
    assert fake.triggers.created == []


def test_linear_provisions_both_triggers_per_team():
    """Linear's triggers are team-scoped: resolve the user's teams and create an
    issue-created + comment trigger for each, with the team_id in the config."""
    fake = FakeComposio(teams=["team_a", "team_b"])
    DefaultTriggerProvisioner(fake).provision("u1", Source.LINEAR, "ca_linear")

    created = {(slug, cfg["team_id"]) for slug, _u, _a, cfg in fake.triggers.created}
    assert created == {
        ("LINEAR_ISSUE_CREATED_TRIGGER", "team_a"),
        ("LINEAR_COMMENT_EVENT_TRIGGER", "team_a"),
        ("LINEAR_ISSUE_CREATED_TRIGGER", "team_b"),
        ("LINEAR_COMMENT_EVENT_TRIGGER", "team_b"),
    }


def test_linear_with_no_teams_creates_nothing():
    """No teams resolved (a failed or empty lookup) provisions nothing rather
    than creating a trigger with no team_id, which Linear would reject."""
    fake = FakeComposio(teams=[])
    DefaultTriggerProvisioner(fake).provision("u1", Source.LINEAR, "ca_linear")
    assert fake.triggers.created == []


# --- idempotency -------------------------------------------------------------


def test_a_slug_already_active_is_not_recreated():
    """The connect flow reconciles on every poll, so provision runs repeatedly.
    An already-active trigger must be left alone rather than piled on."""
    fake = FakeComposio(
        FakeTriggers(existing=["GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER"])
    )
    DefaultTriggerProvisioner(fake).provision("u1", Source.GITHUB, "ca_live")
    assert fake.triggers.created == []


def test_provision_is_idempotent_across_repeated_calls():
    """Second provision sees the first one's trigger as already active."""
    triggers = FakeTriggers()
    # Make each create feed back into what list_active reports next time, the way
    # the real API would once the instance exists.
    original_create = triggers.create

    def recording_create(slug, **kwargs):
        triggers.existing.append(slug)
        return original_create(slug, **kwargs)

    triggers.create = recording_create
    provisioner = DefaultTriggerProvisioner(FakeComposio(triggers))

    provisioner.provision("u1", Source.SLACK, "ca_slack")
    first_round = len(triggers.created)
    provisioner.provision("u1", Source.SLACK, "ca_slack")

    assert first_round == 2
    assert len(triggers.created) == 2  # nothing new the second time


# --- resilience --------------------------------------------------------------


def test_one_failed_create_does_not_stop_the_others():
    triggers = FakeTriggers()
    calls: list[str] = []

    def flaky_create(slug, **kwargs):
        calls.append(slug)
        if slug == "SLACK_DIRECT_MESSAGE_RECEIVED":
            raise RuntimeError("composio said no")
        return type("T", (), {"id": "ti"})()

    triggers.create = flaky_create
    DefaultTriggerProvisioner(FakeComposio(triggers)).provision(
        "u1", Source.SLACK, "ca_slack"
    )
    # Both were attempted; the channel one still went through.
    assert set(calls) == {
        "SLACK_DIRECT_MESSAGE_RECEIVED",
        "SLACK_CHANNEL_MESSAGE_RECEIVED",
    }


def test_a_failed_list_active_falls_back_to_creating():
    """If we cannot read current triggers we still provision (create is an
    upsert), rather than skip and leave the feed dead."""
    fake = FakeComposio(FakeTriggers(list_error=RuntimeError("list down")))
    DefaultTriggerProvisioner(fake).provision("u1", Source.GITHUB, "ca_live")
    assert [c[0] for c in fake.triggers.created] == [
        "GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER"
    ]
