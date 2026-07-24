"""Slack write-back through Composio.

Acting on an item is the point where a mistake is visible to other people: a
reply in the wrong channel, or a thread reply posted as a new channel message.
Both are tested here because neither is recoverable by us once sent.
"""

from __future__ import annotations

import pytest

from backend.integrations.slack_service import (
    ComposioSlackService,
    parse_source_ref,
)
from backend.integrations.slack import SLACK_TOOLKIT_VERSION


class _FakeTools:
    def __init__(self, payload=None):
        self.payload = payload or {"successful": True, "data": {"ts": "1.1", "ok": True}}
        self.calls: list[tuple] = []

    def execute(self, slug, user_id=None, arguments=None, version=None):
        self.calls.append((slug, user_id, arguments, version))
        return self.payload


class _FakeComposio:
    def __init__(self, payload=None):
        self.tools = _FakeTools(payload)


@pytest.fixture
def service():
    client = _FakeComposio()
    return ComposioSlackService(client, user_id="me"), client


def test_reply_to_a_dm_posts_into_that_channel(service):
    svc, client = service
    svc.reply("slack:D01ABC:1784812011.000100", "on it")

    slug, user_id, args, version = client.tools.calls[0]
    assert slug == "SLACK_SEND_MESSAGE"
    assert user_id == "me"
    assert args["channel"] == "D01ABC"
    assert args["text"] == "on it"
    assert version == SLACK_TOOLKIT_VERSION


def test_reply_to_a_thread_message_stays_in_the_thread(service):
    """Replying to a threaded message without thread_ts posts it to the whole
    channel instead, which is visible to everyone and cannot be undone."""
    svc, client = service
    svc.reply(
        "slack:C01ENG:1784812011.000200", "looking now", thread_ts="1784812000.000100"
    )

    _, _, args, _ = client.tools.calls[0]
    assert args["thread_ts"] == "1784812000.000100"


def test_marking_read_moves_the_cursor_to_that_message(service):
    svc, client = service
    svc.mark_read("slack:C01ENG:1784812011.000200")

    slug, _, args, _ = client.tools.calls[0]
    assert slug == "SLACK_SET_READ_CURSOR_IN_A_CONVERSATION"
    assert args == {"channel": "C01ENG", "ts": "1784812011.000200"}


def test_resolving_your_own_identity_reads_the_user_id(service):
    client = _FakeComposio({"successful": True, "data": {"user_id": "U_ME", "user": "vicky"}})
    svc = ComposioSlackService(client, user_id="me")

    identity = svc.resolve_identity()

    assert identity.slack_user_id == "U_ME"
    assert client.tools.calls[0][0] == "SLACK_TEST_AUTH"


def test_an_unparseable_source_ref_raises_rather_than_guessing(service):
    """Guessing a channel here means posting a private reply somewhere public."""
    svc, _ = service
    with pytest.raises(ValueError):
        svc.reply("not-a-slack-ref", "hello")


# --- the dashboard ---------------------------------------------------------


class _SummaryTools:
    """Enough of Slack to build a summary: two channels, one DM, and counts."""

    def __init__(self, failing: set[str] | None = None):
        self.failing = failing or set()
        self.calls: list[tuple] = []

    def execute(self, slug, user_id=None, arguments=None, version=None):
        self.calls.append((slug, arguments))
        if slug == "SLACK_LIST_ALL_USERS":
            return {"data": {"members": [
                {"id": "U_PRIYA", "profile": {"display_name": "Priya"}}
            ]}}
        if slug == "SLACK_LIST_CONVERSATIONS":
            if "im" in (arguments or {}).get("types", ""):
                return {"data": {"channels": [{"id": "D1", "user": "U_PRIYA"}]}}
            return {"data": {"channels": [
                {"id": "C1", "name": "eng"}, {"id": "C2", "name": "design"},
            ]}}
        if slug == "SLACK_SEARCH_MESSAGES":
            query = (arguments or {}).get("query", "")
            for token in self.failing:
                if token in query:
                    raise RuntimeError("ratelimited")
            total = {"#eng": 130, "#design": 47, "<@U_PRIYA>": 12}
            for token, value in total.items():
                if token in query:
                    return {"data": {"messages": {"total": value}}}
        return {"data": {}}


def _summary(failing=None):
    client = _FakeComposio()
    client.tools = _SummaryTools(failing)
    return ComposioSlackService(client, user_id="me").channel_summary()


def test_the_headline_total_is_the_sum_of_the_rows():
    """The old headline was a separate workspace-wide search, so it could never
    match the rows beneath it: 5932 above, a few hundred below."""
    summary = _summary()
    assert summary["messages"] == 130 + 47 + 12
    assert summary["messages"] == sum(r["count"] for r in summary["rows"])


def test_direct_messages_get_their_own_named_rows():
    """"27 DMs" with no breakdown could not say who was actually talking."""
    summary = _summary()
    dm_rows = [r for r in summary["rows"] if r["is_dm"]]
    assert [r["label"] for r in dm_rows] == ["Priya"]
    assert summary["dms"] == 1
    assert summary["channels"] == 2


def test_every_channel_is_counted_rather_than_the_first_twelve():
    summary = _summary()
    assert all(r["counted"] for r in summary["rows"])
    assert summary["uncounted"] == 0


def test_a_conversation_slack_would_not_count_says_so_instead_of_showing_zero():
    """A throttled search returning 0 is indistinguishable from a silent
    channel, and quietly makes the headline wrong."""
    summary = _summary(failing={"#design"})
    design = next(r for r in summary["rows"] if r["label"] == "#design")
    assert design["counted"] is False
    assert summary["uncounted"] == 1
    # The total only claims what was actually counted.
    assert summary["messages"] == 130 + 12


class _ExternalTools(_SummaryTools):
    """A workspace whose busiest channels are Slack Connect, so they never come
    back from ``conversations.list`` and only exist in the search index."""

    def execute(self, slug, user_id=None, arguments=None, version=None):
        if slug == "SLACK_SEARCH_MESSAGES":
            args = arguments or {}
            query = args.get("query", "")
            self.calls.append((slug, args))
            if args.get("count") == 100:  # a discovery page
                if args.get("page") != 1:
                    return {"data": {"messages": {"matches": []}}}
                return {"data": {"messages": {"matches": [
                    {"channel": {"id": "C9", "name": "cs-logistics", "is_im": False}},
                    {"channel": {"id": "D1", "name": "U_PRIYA", "is_im": True}},
                ]}}}
            if query.strip() == "after:2026-06-24" or "in:" not in query:
                return {"data": {"messages": {"total": 3000}}}
            if "#cs-logistics" in query:
                return {"data": {"messages": {"total": 2320}}}
        return super().execute(slug, user_id=user_id, arguments=arguments, version=version)


def _external_summary():
    client = _FakeComposio()
    client.tools = _ExternalTools()
    from datetime import datetime, timezone

    return ComposioSlackService(client, user_id="me").channel_summary(
        now=datetime(2026, 7, 24, tzinfo=timezone.utc)
    )


def test_slack_connect_channels_are_found_even_though_the_list_call_hides_them():
    """Eight external channels held 4504 of this workspace's 5932 messages,
    including the busiest one, and none appeared in conversations.list."""
    summary = _external_summary()
    labels = [r["label"] for r in summary["rows"]]
    assert "#cs-logistics" in labels
    busiest = next(r for r in summary["rows"] if r["label"] == "#cs-logistics")
    assert busiest["count"] == 2320


def test_a_direct_message_is_never_listed_as_a_channel():
    """In a search match a DM's channel name is the other user's id, which
    would render as a channel called U_PRIYA."""
    summary = _external_summary()
    assert "#U_PRIYA" not in [r["label"] for r in summary["rows"]]


def test_traffic_we_could_not_itemise_gets_its_own_row_rather_than_vanishing():
    summary = _external_summary()
    counted = sum(r["count"] for r in summary["rows"])
    assert summary["messages"] == 3000
    assert counted == 3000  # the residual row closes the gap exactly
    assert any(r["label"] == "Everywhere else" for r in summary["rows"])


# --- the direct message backfill -------------------------------------------


class _DMSearchTools(_SummaryTools):
    MATCH = {
        "channel": {"id": "D09N", "name": "U_PRIYA", "is_im": True},
        "user": "U_PRIYA",
        "username": "priya.s",
        "text": "can you look at <@U_ME> the deploy?",
        "ts": "1784834003.554529",
        "permalink": "https://x.slack.com/archives/D09N/p1784834003554529",
        "type": "im",
    }

    def execute(self, slug, user_id=None, arguments=None, version=None):
        if slug == "SLACK_SEARCH_MESSAGES" and "is:dm" in (arguments or {}).get("query", ""):
            self.calls.append((slug, arguments))
            return {"data": {"messages": {"total": 2, "matches": [
                self.MATCH,
                {**self.MATCH, "user": "U_ME", "text": "on it", "ts": "1784834100.1"},
            ]}}}
        return super().execute(slug, user_id=user_id, arguments=arguments, version=version)


def _backfill():
    from backend.models.identity import Identity

    client = _FakeComposio()
    client.tools = _DMSearchTools()
    service = ComposioSlackService(client, user_id="me")
    return service, client, service.unread(Identity(slack_user_id="U_ME"))


def test_the_backfill_is_one_search_not_a_call_per_conversation():
    """27 history calls against the endpoint Slack throttles hardest once
    returned nothing at all and timed the refresh out."""
    _, client, _ = _backfill()
    history_calls = [c for c in client.tools.calls if "HISTORY" in c[0]]
    assert history_calls == []


def test_the_backfill_names_the_sender_and_renders_the_mention():
    _, _, events = _backfill()
    assert events[0].actor.display_name == "Priya"
    assert "@" in events[0].title and "<@" not in events[0].title


def test_the_backfill_still_drops_your_own_messages():
    _, _, events = _backfill()
    assert [e.title for e in events] == ["can you look at @U_ME the deploy?"]


def test_the_backfill_keeps_the_conversation_id_so_a_reply_can_be_sent_back():
    _, _, events = _backfill()
    assert events[0].source_ref == "slack:D09N:1784834003.554529"
    assert parse_source_ref(events[0].source_ref).channel == "D09N"
