"""Slack mapping and rules: section 3.2 of the MVP plan.

A Slack message has no type, only text, so almost everything here ends in "ask
the model". The rules' whole job is the opposite one: filtering out the traffic
that obviously needs nobody, before we pay to classify it. Getting that filter
wrong in the permissive direction costs money on every channel message in the
workspace; getting it wrong in the strict direction silently drops real asks.
Both directions are tested.
"""

from __future__ import annotations

import pytest

from backend.integrations.slack import (
    channel_message_to_raw_event,
    direct_message_to_raw_event,
)
from backend.models.identity import Identity
from backend.models.tiers import Tier, TypeTag
from backend.services.rules import DefaultRuleClassifier

ME = Identity(slack_user_id="U_ME")

DM = {
    "channel": "D01ABC",
    "channel_type": "im",
    "user": "U_PRIYA",
    "text": "can you unblock the staging deploy?",
    "ts": "1784812011.000100",
    "team": "T01",
}

CHANNEL_MESSAGE = {
    "channel": "C01ENG",
    "channel_type": "channel",
    "channel_name": "eng-releases",
    "user": "U_PRIYA",
    "text": "shipped the fix, thanks all",
    "ts": "1784812011.000200",
    "team": "T01",
}


def classify(event):
    return DefaultRuleClassifier().classify(event, identity=ME)


# --- direct messages -------------------------------------------------------


def test_a_dm_always_goes_to_the_model():
    """A DM has no type and no structured urgency. There is nothing for a rule
    to decide, so every one of them is a judgement call."""
    event = direct_message_to_raw_event(DM, identity=ME)
    verdict = classify(event)
    assert verdict.needs_llm is True
    assert verdict.type_tag is TypeTag.REPLY


def test_a_dm_is_blocking_because_it_was_sent_to_you_personally():
    event = direct_message_to_raw_event(DM, identity=ME)
    assert event.is_blocking is True
    assert event.actor.login == "U_PRIYA"


def test_a_dm_carries_its_text_for_the_model_to_read():
    event = direct_message_to_raw_event(DM, identity=ME)
    assert event.body == "can you unblock the staging deploy?"


def test_a_dm_context_chip_says_dm():
    assert direct_message_to_raw_event(DM, identity=ME).context_chip == "DM"


def test_your_own_reply_in_someone_elses_dm_is_not_a_notification():
    """The trigger fires on every message in the conversation, including the
    ones you send. Without this, replying to Priya would file your own reply
    back into your feed as something needing your attention."""
    own = {**DM, "user": "U_ME"}
    assert direct_message_to_raw_event(own, identity=ME) is None


def test_a_note_to_yourself_is_kept():
    """A self-DM is Slack's save-for-later, and the sender being you is the
    whole point of it. It is indistinguishable from your own reply by sender
    alone, so the self-DM channel id is what separates them."""
    me_with_channel = Identity(slack_user_id="U_ME", slack_dm_channel="D_SELF")
    note = {**DM, "user": "U_ME", "channel": "D_SELF"}

    event = direct_message_to_raw_event(note, identity=me_with_channel)

    assert event is not None
    assert event.context_chip == "Note to self"
    assert event.is_blocking is False  # nobody else is waiting on it


def test_your_own_reply_is_still_dropped_when_the_self_channel_is_known():
    me_with_channel = Identity(slack_user_id="U_ME", slack_dm_channel="D_SELF")
    reply = {**DM, "user": "U_ME", "channel": "D01ABC"}
    assert direct_message_to_raw_event(reply, identity=me_with_channel) is None


# --- channel messages ------------------------------------------------------


def test_a_channel_message_that_does_not_mention_you_is_dropped_before_the_model():
    """This is the cost filter. Every message in every channel the user is in
    arrives here, and classifying them all would be the single largest expense
    in the product for no user value."""
    assert channel_message_to_raw_event(CHANNEL_MESSAGE, identity=ME) is None


def test_a_channel_message_that_mentions_you_reaches_the_model():
    mentioned = {**CHANNEL_MESSAGE, "text": "<@U_ME> can you review this before 5?"}
    event = channel_message_to_raw_event(mentioned, identity=ME)
    assert event is not None
    assert classify(event).needs_llm is True


def test_a_mention_of_someone_else_is_not_a_mention_of_you():
    other = {**CHANNEL_MESSAGE, "text": "<@U_SAM> can you take this?"}
    assert channel_message_to_raw_event(other, identity=ME) is None


def test_a_partial_id_match_is_not_a_mention():
    """`U_ME` must not match `U_MEREDITH`. A substring check here would file
    other people's mentions into this user's feed."""
    lookalike = {**CHANNEL_MESSAGE, "text": "<@U_MEREDITH> please look"}
    assert channel_message_to_raw_event(lookalike, identity=ME) is None


@pytest.mark.parametrize("token", ["<!channel>", "<!here>", "<!everyone>"])
def test_broadcast_mentions_do_not_count_as_addressing_you(token):
    """@channel is addressed to a room, not to a person. Treating it as a
    direct ask is how the urgent tier fills up with things nobody meant for
    this user."""
    broadcast = {**CHANNEL_MESSAGE, "text": f"{token} standup in 5"}
    assert channel_message_to_raw_event(broadcast, identity=ME) is None


def test_a_channel_message_keeps_its_channel_as_the_context_chip():
    mentioned = {**CHANNEL_MESSAGE, "text": "<@U_ME> ping"}
    event = channel_message_to_raw_event(mentioned, identity=ME)
    assert event.context_chip == "#eng-releases"


def test_a_thread_reply_you_are_part_of_reaches_the_model():
    reply = {
        **CHANNEL_MESSAGE,
        "text": "any update on this?",
        "thread_ts": "1784812000.000100",
    }
    event = channel_message_to_raw_event(
        reply, identity=ME, my_threads={"1784812000.000100"}
    )
    assert event is not None
    assert classify(event).needs_llm is True


def test_a_thread_reply_you_are_not_part_of_is_dropped():
    reply = {**CHANNEL_MESSAGE, "text": "any update?", "thread_ts": "9999.0001"}
    assert channel_message_to_raw_event(reply, identity=ME, my_threads=set()) is None


# --- bots and noise --------------------------------------------------------


def test_a_bot_message_is_noise():
    bot = {**CHANNEL_MESSAGE, "text": "<@U_ME> deploy finished", "bot_id": "B01"}
    event = channel_message_to_raw_event(bot, identity=ME)
    assert classify(event).tier is Tier.NOISE
    assert classify(event).needs_llm is False


def test_a_bot_message_reporting_a_failure_still_reaches_the_model():
    """The one exception in 3.2: automation telling you your own work broke is
    the whole reason a bot message would ever matter."""
    bot = {
        **CHANNEL_MESSAGE,
        "text": "<@U_ME> Build failed on main: 3 tests failing",
        "bot_id": "B01",
    }
    event = channel_message_to_raw_event(bot, identity=ME)
    assert classify(event).needs_llm is True


def test_a_message_with_no_text_is_dropped():
    """Reactions, joins and file-only events arrive on the same trigger."""
    assert channel_message_to_raw_event({**CHANNEL_MESSAGE, "text": ""}, identity=ME) is None


def test_message_subtypes_that_are_not_messages_are_dropped():
    joined = {**CHANNEL_MESSAGE, "subtype": "channel_join", "text": "<@U_ME> joined"}
    assert channel_message_to_raw_event(joined, identity=ME) is None


# --- identity --------------------------------------------------------------


def test_without_a_slack_identity_no_channel_message_can_be_matched():
    """Better to surface nothing than to guess. Mention detection is the only
    thing making channel messages tractable, and it needs the user's own id."""
    mentioned = {**CHANNEL_MESSAGE, "text": "<@U_ME> ping"}
    assert channel_message_to_raw_event(mentioned, identity=Identity()) is None


# --- source_ref ------------------------------------------------------------


def test_source_ref_identifies_the_message_uniquely():
    event = direct_message_to_raw_event(DM, identity=ME)
    assert event.source_ref == "slack:D01ABC:1784812011.000100"


def test_a_thread_reply_is_its_own_item_not_a_duplicate_of_the_parent():
    first = channel_message_to_raw_event(
        {**CHANNEL_MESSAGE, "text": "<@U_ME> one", "ts": "1.1"}, identity=ME
    )
    second = channel_message_to_raw_event(
        {**CHANNEL_MESSAGE, "text": "<@U_ME> two", "ts": "1.2"}, identity=ME
    )
    assert first.source_ref != second.source_ref
