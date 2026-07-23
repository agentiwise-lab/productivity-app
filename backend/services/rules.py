"""Deterministic classification: RawEvent -> (tier, type tag, needs_llm).

This is section 3 of the MVP plan in code. A rule fires whenever the source
states both the *type* of the thing and an unambiguous *urgency*. Where urgency
lives only in human language, the rule stops at a floor tier and hands the item
to the model, which may promote or demote from there.

The order of the checks in ``classify`` is the precedence ladder of 3.7 and is
load-bearing: one item can match several rules, and exactly one tag reaches the
card. Do not reorder without changing the plan.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from backend.models.events import RawEvent
from backend.models.identity import Identity
from backend.models.tiers import Tier, TypeTag


class RuleVerdict(BaseModel):
    """What the rules alone can say about an item.

    ``tier`` is final when ``needs_llm`` is False, and a floor to move from when
    it is True. Storing both is what lets the feed render instantly on rule
    tiers and re-rank later when classification lands (4.4).
    """

    tier: Tier
    type_tag: TypeTag
    needs_llm: bool = False


class RuleClassifier(Protocol):
    def classify(self, event: RawEvent, *, identity: Identity) -> RuleVerdict:
        ...


# Labels that state their own urgency. Structured data, so no model needed.
_URGENT_LABELS = {
    "p0",
    "blocker",
    "critical",
    "urgent",
    "sev1",
    "sev-1",
    "production",
    "incident",
}
_LOW_LABELS = {"low priority", "p3", "nice to have", "someday", "backlog", "wontfix"}

# Reasons whose urgency is stated by the source itself.
_TERMINAL: dict[str, tuple[Tier, TypeTag]] = {
    "invitation": (Tier.TODAY, TypeTag.DECIDE),
    "state_change": (Tier.NOISE, TypeTag.FYI),
    "subscribed": (Tier.NOISE, TypeTag.FYI),
    "author": (Tier.NOISE, TypeTag.FYI),
    "manual": (Tier.NOISE, TypeTag.FYI),
}

# Reasons whose urgency lives in human language. The tag and the floor are
# known; only the tier is open.
_DEFERRED: dict[str, tuple[Tier, TypeTag]] = {
    "assign": (Tier.TODAY, TypeTag.ASSIGNED),
    "mention": (Tier.TODAY, TypeTag.REPLY),
    "team_mention": (Tier.CAN_WAIT, TypeTag.REPLY),
    "comment": (Tier.CAN_WAIT, TypeTag.COMMENT),
    "review_request_removed": (Tier.NOISE, TypeTag.FYI),
}


class DefaultRuleClassifier:
    def classify(self, event: RawEvent, *, identity: Identity) -> RuleVerdict:
        # 1. Security alert.
        if event.reason == "security_alert":
            return RuleVerdict(tier=Tier.URGENT, type_tag=TypeTag.ALERT)

        # 2. CI failure, but only on the user's own PR. Someone else's red build
        #    is not this user's emergency.
        if event.check_conclusion == "failure":
            if identity.is_me_on_github(event.subject_author):
                return RuleVerdict(tier=Tier.URGENT, type_tag=TypeTag.ALERT)
            return RuleVerdict(tier=Tier.NOISE, type_tag=TypeTag.FYI)
        if event.reason == "ci_activity":
            return RuleVerdict(tier=Tier.NOISE, type_tag=TypeTag.FYI)

        # 3. A gate is waiting on this user.
        if event.reason == "approval_requested" or event.approval_requested:
            return RuleVerdict(tier=Tier.URGENT, type_tag=TypeTag.APPROVE)

        # 4. Someone explicitly asked for a review.
        if event.reason == "review_requested" or event.review_requested:
            return RuleVerdict(tier=Tier.URGENT, type_tag=TypeTag.REVIEW)

        # 5. Changes requested on the user's own PR: the ball is back with them.
        if event.review_state == "changes_requested" and identity.is_me_on_github(
            event.subject_author
        ):
            return RuleVerdict(tier=Tier.TODAY, type_tag=TypeTag.DECIDE)

        # 6-7. Mentions, assignments and comments: type known, urgency is prose.
        deferred = _DEFERRED.get(event.reason)
        if deferred is not None:
            floor, tag = deferred
            labelled = self._tier_from_labels(event)
            if labelled is not None:
                return RuleVerdict(tier=labelled, type_tag=tag)
            return RuleVerdict(tier=floor, type_tag=tag, needs_llm=True)

        terminal = _TERMINAL.get(event.reason)
        if terminal is not None:
            tier, tag = terminal
            return RuleVerdict(tier=tier, type_tag=tag)

        # 8. Everything else. Unknown reasons are noise, never urgent: an
        #    unrecognised signal must not be able to shout.
        return RuleVerdict(tier=Tier.NOISE, type_tag=TypeTag.FYI)

    @staticmethod
    def _tier_from_labels(event: RawEvent) -> Tier | None:
        labels = {label.strip().lower() for label in event.labels}
        if labels & _URGENT_LABELS:
            return Tier.URGENT
        if labels & _LOW_LABELS:
            return Tier.CAN_WAIT
        return None
