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


class _DocsTools:
    def execute(self, slug, user_id=None, arguments=None, version=None):
        assert slug == "GOOGLEDOCS_SEARCH_DOCUMENTS"
        return {
            "data": {
                "files": [
                    {
                        "name": "Roadmap",
                        "webViewLink": "https://docs.google.com/document/d/1",
                        "modifiedTime": "2026-07-20T10:00:00Z",
                    },
                    {"name": "(untitled)"},  # missing fields tolerated
                ]
            }
        }


class _DocsComposio:
    def __init__(self):
        self.tools = _DocsTools()


def test_documents_lists_recent_docs_from_the_docs_account():
    svc = ComposioGoogleDocsService(_DocsComposio(), user_id="u")
    docs = svc.documents()
    assert docs[0]["name"] == "Roadmap"
    assert docs[0]["url"].endswith("/1")
    assert docs[0]["modified"] is not None
    assert docs[1]["name"] == "(untitled)"  # tolerated


def test_the_activity_board_shows_documents_and_mention_counts():
    from datetime import datetime, timezone

    from backend.models.sources import Source
    from backend.services.stats import SourceStatsService

    class _FakeDocs:
        def documents(self, limit=25):
            return [
                {
                    "name": "Roadmap",
                    "url": "https://docs.google.com/document/d/1",
                    "modified": datetime(2026, 7, 24, tzinfo=timezone.utc),
                }
            ]

        def mentions(self, limit=50):
            return [
                docs_notification_to_raw_event(
                    _message('"P (Google Docs)" <comments-noreply@docs.google.com>')
                )
            ]

    class _Ints:
        def google_docs(self, user_id):
            return _FakeDocs()

    now = datetime(2026, 7, 26, tzinfo=timezone.utc)
    svc = SourceStatsService(integrations=_Ints(), clock=lambda: now)
    board = svc.dashboard("u", Source.GOOGLE_DOCS, items=[], now=now)

    labels = [s.label for s in board.headline]
    assert "Documents" in labels
    assert "Mentions" in labels
    assert board.breakdown[0].label == "Roadmap"
    assert "edited" in (board.breakdown[0].value_label or "")
