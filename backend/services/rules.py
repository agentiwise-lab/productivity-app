"""Deterministic classification: RawEvent -> (tier, tag, needs_llm, signal).

The rules do two small jobs and nothing else. First, ``_canonical_reason``
normalises a RawEvent — whose urgency signal may live in a coarse ``reason``, a
boolean flag, a ``review_state``, or a check conclusion — into one canonical
``signal`` string. Second, that signal is looked up in ``TIER_BANDS`` (the whole
triage policy, one table). There is no precedence ladder of tier decisions: the
only ordering left is in ``_canonical_reason``, which decides *what the event
is*, not how urgent it is. Urgency policy lives entirely in the band table, and
the model's rating is confined to the band at read time by ``clamp``.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from backend.models.events import RawEvent
from backend.models.identity import Identity
from backend.models.tiers import Tier, TypeTag, clamp
from backend.services.tier_bands import Banded, Deterministic, policy_for


class RuleVerdict(BaseModel):
    """What the rules alone can say about an item.

    ``tier`` is the tier to render immediately (the band default, or a label's
    verdict). ``signal`` is the canonical reason, stored on the row so the band
    — and thus the floor/ceiling the model is clamped to — can be recovered at
    read time. ``ephemeral`` marks a settled-noise item that should be dropped
    rather than kept as a visible "later" row.
    """

    tier: Tier
    type_tag: TypeTag
    needs_llm: bool = False
    signal: str = "manual"
    ephemeral: bool = True


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


class DefaultRuleClassifier:
    def classify(self, event: RawEvent, *, identity: Identity) -> RuleVerdict:
        signal = self._canonical_reason(event, identity)
        policy = policy_for(signal)
        labels = {label.strip().lower() for label in event.labels}

        if isinstance(policy, Banded):
            # A structured label states its own urgency, so it settles the tier
            # without the model — an urgent label pins to the ceiling, a low one
            # to the floor, and neither is ever held for classification.
            if labels & _URGENT_LABELS:
                tier = clamp(Tier.URGENT, policy.floor, policy.ceiling)
                return RuleVerdict(
                    tier=tier, type_tag=policy.type_tag, signal=signal, ephemeral=False
                )
            if labels & _LOW_LABELS:
                return RuleVerdict(
                    tier=policy.floor,
                    type_tag=policy.type_tag,
                    signal=signal,
                    ephemeral=False,
                )
            # The model rates it. The stored ``rule_tier`` is only a placeholder:
            # the item is held off-screen until the model lands (or shown at the
            # ceiling if the attempt fails), so this value is never displayed.
            return RuleVerdict(
                tier=policy.floor,
                type_tag=policy.type_tag,
                needs_llm=True,
                signal=signal,
                ephemeral=policy.ephemeral,
            )

        # Deterministic: a fixed tier, or a read-time function owns it. When a
        # function owns it (Linear, calendar) the stored tier is a can_wait
        # placeholder — never noise, so ingest does not drop a live task — and
        # the real tier is computed on every read.
        tier = policy.tier if policy.tier is not None else Tier.CAN_WAIT
        return RuleVerdict(
            tier=tier,
            type_tag=policy.type_tag,
            signal=signal,
            ephemeral=policy.ephemeral,
        )

    @staticmethod
    def _canonical_reason(event: RawEvent, identity: Identity) -> str:
        """Collapse the event's several urgency channels into one signal.

        The order here is the old precedence ladder, but it only decides *which
        thing the event is* when several facts are true at once (a PR can be
        review-requested and failing CI in the same notification, and the card
        carries one tag). It sets no tiers; the band table does that.
        """
        if event.reason == "security_alert":
            return "security_alert"
        if event.check_conclusion == "failure":
            return (
                "ci_failure_mine"
                if identity.is_me_on_github(event.subject_author)
                else "ci_failure_other"
            )
        if event.check_conclusion == "success" or event.reason == "ci_activity":
            return "ci_ok"
        if event.reason == "approval_requested" or event.approval_requested:
            return "approval_requested"
        if event.reason == "review_requested" or event.review_requested:
            return "review_requested"
        if event.review_state == "changes_requested" and identity.is_me_on_github(
            event.subject_author
        ):
            return "changes_requested_mine"
        return event.reason
