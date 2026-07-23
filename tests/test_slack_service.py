"""Slack write-back through Composio.

Acting on an item is the point where a mistake is visible to other people: a
reply in the wrong channel, or a thread reply posted as a new channel message.
Both are tested here because neither is recoverable by us once sent.
"""

from __future__ import annotations

import pytest

from backend.integrations.slack_service import ComposioSlackService
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
