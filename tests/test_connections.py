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
from backend.services.connections import DefaultConnectionService


class FakeComposioAccounts:
    def __init__(self, rows=None, error: Exception | None = None):
        self._rows = rows or []
        self._error = error

    def list(self, **kwargs):
        if self._error:
            raise self._error
        return type("R", (), {"items": self._rows})()


def account(toolkit: str, status: str = "ACTIVE", ident: str = "ca_1"):
    return {"toolkit": {"slug": toolkit}, "status": status, "id": ident}


def build(rows=None, error=None):
    composio = type(
        "C", (), {"connected_accounts": FakeComposioAccounts(rows, error)}
    )()
    return DefaultConnectionService(composio=composio, composio_user_id="u1")


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
