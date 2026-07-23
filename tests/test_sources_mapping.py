"""Calendar, Linear and Gmail: sections 3.3, 3.5 and 3.6.

These are the fixture suites for the four sources that previously had no
mappers at all, which is why nothing from them could ever reach the feed no
matter what the user connected.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.integrations.calendar import event_to_meeting, event_to_raw_event
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


def test_a_meeting_starting_within_fifteen_minutes_is_urgent():
    """The only thing in the feed that genuinely cannot be done later."""
    soon = event(start={"dateTime": at(10, 10)}, end={"dateTime": at(11)})
    verdict = classify(event_to_raw_event(soon, now=NOW))
    assert verdict.tier is Tier.URGENT


def test_an_invite_awaiting_your_answer_is_today_and_tagged_rsvp():
    invite = event(attendees=[{"self": True, "responseStatus": "needsAction"}])
    raw = event_to_raw_event(invite, now=NOW)
    verdict = classify(raw)
    assert verdict.tier is Tier.TODAY
    assert verdict.type_tag is TypeTag.RSVP
    assert raw.is_blocking is True


def test_an_accepted_meeting_hours_away_is_not_a_feed_item():
    """It is context, not an action, and it belongs on the ruler. Putting every
    meeting in the feed is how the feed stops meaning "needs you"."""
    assert event_to_raw_event(event(), now=NOW) is None


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


def test_linear_priority_high_is_today():
    assert classify(issue_to_raw_event(issue(priority=2))).tier is Tier.TODAY


def test_a_due_date_is_carried_so_ranking_can_use_it():
    raw = issue_to_raw_event(issue(dueDate="2026-07-23"))
    assert classify(raw).tier is Tier.TODAY
    assert raw.deadline is not None


def test_a_due_date_means_end_of_that_day_not_midnight():
    """Midnight would make everything due today read as overdue from 00:01, and
    the whole day would open Urgent."""
    raw = issue_to_raw_event(issue(dueDate="2026-07-23"))
    assert raw.deadline.hour == 23 and raw.deadline.minute == 59


def test_an_issue_with_no_priority_and_no_due_date_goes_to_the_model():
    verdict = classify(issue_to_raw_event(issue()))
    assert verdict.needs_llm is True
    assert verdict.tier is Tier.TODAY  # never can_wait by default (3.1)


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


def test_the_sender_name_is_split_from_the_address():
    raw = message_to_raw_event(message())
    assert raw.actor.display_name == "Priya Sharma"
    assert raw.actor.login == "priya@agentiwise.com"


def test_the_subject_becomes_the_title_and_the_snippet_the_body():
    raw = message_to_raw_event(message())
    assert raw.title == "Board deck numbers"
    assert "board call" in raw.body
