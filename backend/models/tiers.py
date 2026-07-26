"""Urgency tiers and card type tags.

The tier is the product's whole opinion: it answers "does this need me now".
It is ordered, so rules and the model can be combined by taking a floor or a
ceiling rather than by overwriting each other.
"""

from __future__ import annotations

from enum import Enum


class Tier(str, Enum):
    URGENT = "urgent"
    TODAY = "today"
    CAN_WAIT = "can_wait"
    NOISE = "noise"


class TypeTag(str, Enum):
    """The mono chip on the card. Exactly one per item, set by the winning rule
    in the precedence ladder, so a card is never labelled two things."""

    REVIEW = "review"
    APPROVE = "approve"
    REPLY = "reply"
    ASSIGNED = "assigned"
    COMMENT = "comment"
    DECIDE = "decide"
    RSVP = "rsvp"
    ALERT = "alert"
    FYI = "fyi"


_ORDER: dict[Tier, int] = {
    Tier.NOISE: 0,
    Tier.CAN_WAIT: 1,
    Tier.TODAY: 2,
    Tier.URGENT: 3,
}


def rank(tier: Tier) -> int:
    return _ORDER[tier]


def at_least(tier: Tier, floor: Tier) -> Tier:
    """Raise ``tier`` to ``floor`` if it sits below it. Never lowers."""
    return tier if _ORDER[tier] >= _ORDER[floor] else floor


def clamp(tier: Tier, floor: Tier, ceiling: Tier) -> Tier:
    """Confine ``tier`` to the ``[floor, ceiling]`` band.

    The whole triage policy reduces to this: a source/reason fixes a band, the
    model rates urgency freely, and the rating is confined to the band. It is
    what stops the model demoting an item below the floor its source guarantees
    (the "review requested but the model filed it as can_wait" bug) without
    hard-coding a branch per case. ``floor`` must not sit above ``ceiling``; the
    band table is the single place that invariant is set.
    """
    if _ORDER[tier] < _ORDER[floor]:
        return floor
    if _ORDER[tier] > _ORDER[ceiling]:
        return ceiling
    return tier
