"""Google Docs as its own source, backfilled from its Gmail notifications.

Composio has no Docs comment/mention event, and Google delivers each one as an
email. These tests pin the two things that matter: a notification from a known
Docs/Drive sender becomes a Google Docs item (not a Gmail one), and anything else
the query returns is ignored rather than mis-filed.
"""

from __future__ import annotations

from backend.integrations.google_docs import (
    ComposioGoogleDocsService,
    docs_notification_to_raw_event,
)
from backend.models.identity import Identity
from backend.services.rules import DefaultRuleClassifier


def _message(sender: str, subject: str = "a doc", **overrides) -> dict:
    base = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX", "CATEGORY_UPDATES"],
        "payload": {
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
            ]
        },
    }
    base.update(overrides)
    return base


def test_a_comment_mention_notification_becomes_a_docs_mention():
    raw = docs_notification_to_raw_event(
        _message(
            '"Priya (Google Docs)" <comments-noreply@docs.google.com>',
            "Q3 plan - @vicky you around?",
        )
    )
    assert raw is not None
    assert raw.source == "google_docs"
    assert raw.reason == "docs_mention"
    assert raw.is_blocking is True
    # It lands at the docs_mention band: can_wait floor, the model may lift it.
    verdict = DefaultRuleClassifier().classify(raw, identity=Identity())
    assert verdict.tier.value == "can_wait"
    assert verdict.needs_llm is True


def test_a_drive_share_notification_becomes_a_docs_share():
    raw = docs_notification_to_raw_event(
        _message('"Priya" <drive-shares-noreply@google.com>', "shared a doc")
    )
    assert raw.source == "google_docs"
    assert raw.reason == "docs_share"


def test_mail_from_any_other_sender_is_ignored():
    """The Gmail query is broad; a stray non-Docs message must not be mis-filed
    as a Google Docs item."""
    assert (
        docs_notification_to_raw_event(_message("Priya <priya@agentiwise.com>"))
        is None
    )


class _FakeTools:
    def __init__(self, messages):
        self._messages = messages
        self.calls: list = []

    def execute(self, slug, user_id=None, arguments=None, version=None):
        self.calls.append((slug, arguments))
        return {"data": {"messages": self._messages}}


class _FakeComposio:
    def __init__(self, messages):
        self.tools = _FakeTools(messages)


def test_mentions_reads_gmail_and_keeps_only_docs_notifications():
    client = _FakeComposio(
        [
            _message('"P (Google Docs)" <comments-noreply@docs.google.com>'),
            _message("Someone <someone@example.com>"),  # dropped
        ]
    )
    service = ComposioGoogleDocsService(client, user_id="u")
    events = service.mentions()
    assert [e.source for e in events] == ["google_docs"]
    # It searched Gmail for the Docs notification senders.
    slug, args = client.tools.calls[0]
    assert slug == "GMAIL_FETCH_EMAILS"
    assert "comments-noreply@docs.google.com" in args["query"]
