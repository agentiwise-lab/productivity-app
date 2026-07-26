"""Calendar, Linear and Gmail: sections 3.3, 3.5 and 3.6.

These are the fixture suites for the four sources that previously had no
mappers at all, which is why nothing from them could ever reach the feed no
matter what the user connected.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.integrations.calendar import (
    event_to_meeting,
    event_to_raw_event,
    starting_soon_to_raw_event,
)
from backend.integrations.gmail import message_to_raw_event
from backend.integrations.linear import issue_to_raw_event
from backend.models.identity import Identity
from backend.models.tiers import Tier, TypeTag
from backend.services.rules import DefaultRuleClassifier

NOW = datetime(2026, 7, 23, 10, 0, tzinfo=timezone.utc)
ME = Identity()


def classify(event):
    return DefaultRuleClassifier().classify(event, identity=ME)


def at(hour: int, minute: int = 0) -> str:
    return datetime(2026, 7, 23, hour, minute, tzinfo=timezone.utc).isoformat()


# --- Calendar (3.3) --------------------------------------------------------


def event(**overrides):
    base = {
        "id": "evt1",
        "summary": "Design review",
        "start": {"dateTime": at(14)},
        "end": {"dateTime": at(15)},
        "htmlLink": "https://calendar.google.com/e/1",
        "organizer": {"email": "priya@agentiwise.com"},
        "attendees": [{"self": True, "responseStatus": "accepted"}],
    }
    base.update(overrides)
    return base


def test_a_meeting_on_your_day_becomes_a_feed_item():
    """Today's meetings belong on the feed; the read-time tier (ranking) decides
    urgent-within-the-hour vs by-EOD. The mapper carries the end as the deadline
    (so a passed meeting can be dropped) and the start as occurred_at."""
    soon = event(start={"dateTime": at(10, 10)}, end={"dateTime": at(11)})
    raw = event_to_raw_event(soon, now=NOW)
    assert raw is not None
    assert raw.reason == "calendar_meeting"
    assert raw.deadline.hour == 11  # end
    assert raw.occurred_at.hour == 10  # start


def test_an_invite_awaiting_your_answer_is_tagged_rsvp():
    invite = event(attendees=[{"self": True, "responseStatus": "needsAction"}])
    raw = event_to_raw_event(invite, now=NOW)
    verdict = classify(raw)
    assert raw.reason == "calendar_invite"
    assert verdict.type_tag is TypeTag.RSVP
    assert raw.is_blocking is True


def test_a_meeting_that_has_already_ended_is_not_a_feed_item():
    """A passed meeting is over: nothing to do about it, so it never reaches the
    feed. NOW is 10:00; this one ran 08:00-09:00."""
    over = event(start={"dateTime": at(8)}, end={"dateTime": at(9)})
    assert event_to_raw_event(over, now=NOW) is None


def test_a_meeting_more_than_a_day_out_is_not_a_feed_item():
    """It is context on the ruler, not an action, until the day of."""
    far = event(
        start={"dateTime": (NOW + timedelta(days=2)).isoformat()},
        end={"dateTime": (NOW + timedelta(days=2, hours=1)).isoformat()},
    )
    assert event_to_raw_event(far, now=NOW) is None


def test_a_cancelled_event_never_reaches_the_feed():
    assert event_to_raw_event(event(status="cancelled"), now=NOW) is None


def test_the_ruler_reads_start_and_end_times():
    meeting = event_to_meeting(event())
    assert meeting.start.hour == 14 and meeting.end.hour == 15
    assert meeting.title == "Design review"


def test_an_all_day_event_still_parses():
    """All-day events carry a date rather than a dateTime and would otherwise
    be dropped from the ruler entirely."""
    meeting = event_to_meeting(
        event(start={"date": "2026-07-23"}, end={"date": "2026-07-24"})
    )
    assert meeting is not None


# --- Linear (3.5) ----------------------------------------------------------


def issue(**overrides):
    base = {
        "id": "iss1",
        "identifier": "AGE-214",
        "title": "Doorstead billing edge case",
        "url": "https://linear.app/x/AGE-214",
        "state": {"type": "started"},
        "team": {"key": "AGE"},
        "creator": {"displayName": "Priya"},
        "updatedAt": "2026-07-23T09:00:00Z",
    }
    base.update(overrides)
    return base


def test_linear_priority_urgent_needs_no_model():
    """Linear states urgency in a field, so paying a model to infer it would be
    the most expensive way to learn nothing."""
    verdict = classify(issue_to_raw_event(issue(priority=1)))
    assert verdict.tier is Tier.URGENT
    assert verdict.needs_llm is False


def test_linear_priority_high_with_no_date_can_wait_until_the_model_lifts_it():
    """A stated priority but no due date sits at Can wait by default; the model
    can lift it within the band (ceiling urgent), but it is not by-UD work until
    a date says so."""
    verdict = classify(issue_to_raw_event(issue(priority=2)))
    assert verdict.tier is Tier.CAN_WAIT
    assert verdict.needs_llm is True


def test_a_due_date_is_carried_so_ranking_can_use_it():
    raw = issue_to_raw_event(issue(dueDate="2026-07-23"))
    assert classify(raw).tier is Tier.TODAY
    assert raw.deadline is not None


def test_a_due_date_means_end_of_that_day_not_midnight():
    """Midnight would make everything due today read as overdue from 00:01, and
    the whole day would open Urgent."""
    raw = issue_to_raw_event(issue(dueDate="2026-07-23"))
    assert raw.deadline.hour == 23 and raw.deadline.minute == 59


def test_an_issue_with_no_priority_and_no_due_date_settles_as_later():
    """No priority and no date: the user's own backlog task that nobody is
    waiting on. It settles to Later (noise) without paying the model, and is
    kept as a visible later row rather than dropped."""
    verdict = classify(issue_to_raw_event(issue()))
    assert verdict.needs_llm is False
    assert verdict.tier is Tier.NOISE
    assert verdict.ephemeral is False


def test_a_completed_issue_is_not_in_the_feed():
    assert issue_to_raw_event(issue(state={"type": "completed"})) is None


def test_the_title_carries_the_identifier_people_actually_use():
    raw = issue_to_raw_event(issue())
    assert raw.title.startswith("AGE-214")
    assert raw.context_chip == "AGE"


# --- Gmail (3.6) -----------------------------------------------------------


def message(**overrides):
    base = {
        "id": "m1",
        "threadId": "t1",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "Can you confirm the numbers before the board call?",
        "internalDate": "1784800000000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Board deck numbers"},
                {"name": "From", "value": "Priya Sharma <priya@agentiwise.com>"},
            ]
        },
    }
    base.update(overrides)
    return base


def test_an_unread_personal_email_goes_to_the_model():
    verdict = classify(message_to_raw_event(message()))
    assert verdict.needs_llm is True
    assert verdict.type_tag is TypeTag.REPLY


def test_read_mail_is_not_a_feed_item():
    """The user already dealt with it, by their own action."""
    assert message_to_raw_event(message(labelIds=["INBOX"])) is None


@pytest.mark.parametrize(
    "label", ["CATEGORY_PROMOTIONS", "CATEGORY_SOCIAL", "CATEGORY_FORUMS", "SPAM"]
)
def test_bulk_mail_is_filtered_before_the_model(label):
    """Gmail already sorted these. Classifying them would be paying to be told
    what the label said."""
    verdict = classify(message_to_raw_event(message(labelIds=["UNREAD", label])))
    assert verdict.tier is Tier.NOISE
    assert verdict.needs_llm is False


def test_a_mailing_list_header_outweighs_the_inbox_tab():
    """Gmail files plenty of transactional bulk mail under Primary."""
    bulk = message()
    bulk["payload"]["headers"].append(
        {"name": "List-Unsubscribe", "value": "<https://x.com/u>"}
    )
    assert classify(message_to_raw_event(bulk)).tier is Tier.NOISE


# --- Google Docs, delivered via Gmail notifications ------------------------


def test_a_docs_comment_mention_email_becomes_a_google_docs_item():
    """Google emails a mention from comments-noreply@docs.google.com. It must
    surface as a Google Docs card, not a generic email, and land at the
    docs_mention band (can_wait floor, the model may lift) rather than noise."""
    raw = message_to_raw_event(
        message(
            payload={
                "headers": [
                    {"name": "Subject", "value": "Priya mentioned you in Q3 plan"},
                    {
                        "name": "From",
                        "value": "Priya (Google Docs) <comments-noreply@docs.google.com>",
                    },
                ]
            }
        )
    )
    assert raw is not None
    assert raw.source == "google_docs"
    assert raw.reason == "docs_mention"
    verdict = classify(raw)
    assert verdict.tier is Tier.CAN_WAIT
    assert verdict.needs_llm is True


def test_a_drive_share_email_becomes_a_docs_share_item():
    raw = message_to_raw_event(
        message(
            payload={
                "headers": [
                    {"name": "Subject", "value": "Priya shared a document with you"},
                    {
                        "name": "From",
                        "value": "Priya <drive-shares-noreply@google.com>",
                    },
                ]
            }
        )
    )
    assert raw.source == "google_docs"
    assert raw.reason == "docs_share"


def test_a_docs_notification_is_surfaced_even_without_the_unread_label():
    """Docs mail is exempt from the unread gate: the notification is worth
    showing whether or not Gmail marked it unread."""
    raw = message_to_raw_event(
        message(
            labelIds=["INBOX"],  # no UNREAD
            payload={
                "headers": [
                    {"name": "Subject", "value": "mentioned you"},
                    {"name": "From", "value": "<comments-noreply@docs.google.com>"},
                ]
            },
        )
    )
    assert raw is not None
    assert raw.source == "google_docs"


# --- Calendar starting-soon trigger ----------------------------------------


def test_the_starting_soon_trigger_maps_to_a_calendar_item():
    """GOOGLECALENDAR_EVENT_STARTING_SOON_TRIGGER has a flatter payload than the
    events list; its own mapper turns it into an urgent, imminent meeting."""
    raw = starting_soon_to_raw_event(
        {
            "event_id": "ev1",
            "summary": "Standup",
            "start_timestamp": at(10, 30),
            "html_link": "https://calendar.google.com/event?eid=ev1",
            "hangout_link": "https://meet.google.com/abc",
        }
    )
    assert raw is not None
    assert raw.source == "calendar"
    assert raw.reason == "calendar_starting"
    assert raw.url == "https://calendar.google.com/event?eid=ev1"
    verdict = classify(raw)
    assert verdict.tier is Tier.URGENT
    assert verdict.needs_llm is False


def test_the_sender_name_is_split_from_the_address():
    raw = message_to_raw_event(message())
    assert raw.actor.display_name == "Priya Sharma"
    assert raw.actor.login == "priya@agentiwise.com"


def test_the_subject_becomes_the_title_and_the_snippet_the_body():
    raw = message_to_raw_event(message())
    assert raw.title == "Board deck numbers"
    assert "board call" in raw.body


def test_a_compact_gmail_message_keeps_its_real_date():
    """The compact fetch has no ``internalDate``; it carries an ISO
    ``messageTimestamp``. Reading only the epoch field left every email with no
    date at all, so the feed stamped them "now" and a week-old invitation
    looked like it had just arrived."""
    from backend.integrations.gmail import message_to_raw_event

    event = message_to_raw_event(
        {
            "messageId": "m1",
            "labelIds": ["UNREAD"],
            "subject": "Invitation: Update Call",
            "sender": "Loganathan A <log@x.com>",
            "messageTimestamp": "2026-07-17T11:00:00Z",
        }
    )
    assert event is not None
    assert event.occurred_at == datetime(2026, 7, 17, 11, 0, tzinfo=timezone.utc)


def test_the_epoch_form_still_works():
    """The verbose fetch and the webhooks still send internalDate."""
    from backend.integrations.gmail import message_to_raw_event

    event = message_to_raw_event(
        {
            "id": "m2",
            "labelIds": ["UNREAD"],
            "subject": "Hi",
            "sender": "a@b.com",
            "internalDate": "1784800000000",
        }
    )
    assert event.occurred_at is not None


def test_ingest_asks_gmail_to_exclude_the_bulk_categories():
    """The rules throw newsletters away anyway, so fetching them is pure cost:
    361 messages over three pages, 37 seconds, to find the dozen addressed to a
    person. Gmail can filter its own category tabs, which returns 15 in one
    page in 4 seconds."""

    class _Tools:
        def __init__(self):
            self.queries = []

        def execute(self, slug, user_id=None, arguments=None, version=None):
            self.queries.append((arguments or {}).get("query", ""))
            return {"data": {"messages": []}}

    class _Composio:
        def __init__(self):
            self.tools = _Tools()

    from backend.integrations.gmail import ComposioGmailService

    client = _Composio()
    ComposioGmailService(client, user_id="u").actionable()

    query = client.tools.queries[0]
    assert "is:unread" in query
    assert "newer_than:30d" in query
    for tab in ("promotions", "social", "forums", "updates"):
        assert f"-category:{tab}" in query


def test_later_still_asks_for_everything():
    """Later shows what arrived and did not need you, so its query must stay
    broad. Narrowing both would hide the newsletters entirely."""

    class _Tools:
        def __init__(self):
            self.queries = []

        def execute(self, slug, user_id=None, arguments=None, version=None):
            self.queries.append((arguments or {}).get("query", ""))
            return {"data": {"messages": []}}

    class _Composio:
        def __init__(self):
            self.tools = _Tools()

    from backend.integrations.gmail import ComposioGmailService

    client = _Composio()
    ComposioGmailService(client, user_id="u").unread()

    assert "-category:" not in client.tools.queries[0]
