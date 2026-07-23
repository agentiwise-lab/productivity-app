"""Read-time tier and score. Sections 3.8 and 3.9 of the MVP plan.

Nothing in here is stored. Both functions take an explicit ``now`` rather than
reading the clock themselves, which is what makes "the same row says something
different an hour later" a testable claim instead of a hope.

The card feed and the grouped list both call ``score``, so their order can never
disagree.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from backend.models.feed import FeedItem, UserPreferences
from backend.models.tiers import Tier, at_least

# Tier dominates. The gaps are wide enough that no stack of bonuses on a lower
# tier can outrank the tier above it.
_TIER_WEIGHT: dict[Tier, float] = {
    Tier.URGENT: 1000.0,
    Tier.TODAY: 100.0,
    Tier.CAN_WAIT: 10.0,
    Tier.NOISE: 0.0,
}

# Large enough to sink an item below every live one regardless of its bonuses.
_SUPPRESSED = -10_000.0

_URGENT_STALE_AFTER = timedelta(hours=24)


def effective_tier(item: FeedItem, *, now: datetime) -> Tier:
    """What tier this item is *right now*.

    Starts from the stored judgement (the model's if it has landed, the rules'
    otherwise), then applies the time-dependent corrections that a stored tier
    could never keep up with.
    """
    tier = item.llm_tier or item.rule_tier

    overdue = item.deadline is not None and item.deadline <= now
    if overdue:
        return Tier.URGENT
    if item.deadline is not None and item.deadline - now <= timedelta(hours=3):
        tier = at_least(tier, Tier.TODAY)

    # An urgent item nobody chased for a day was not urgent. Without this the
    # top tier silts up and stops carrying information.
    if tier is Tier.URGENT and item.handled_at is None:
        since = item.occurred_at or item.created_at
        if since is not None and now - since > _URGENT_STALE_AFTER:
            return Tier.TODAY

    return tier


def score(item: FeedItem, prefs: UserPreferences, *, now: datetime) -> float:
    """Rank within and across tiers. Higher sorts first."""
    if item.repo and item.repo in prefs.muted_repos:
        return _SUPPRESSED
    if item.context_chip and item.context_chip in prefs.muted_channels:
        return _SUPPRESSED
    if item.snoozed_until is not None and item.snoozed_until > now:
        return _SUPPRESSED

    total = _TIER_WEIGHT[effective_tier(item, now=now)]
    if item.is_blocking:
        total += 300.0
    total += _deadline_pressure(item.deadline, now)
    if item.sender_handle and item.sender_handle in prefs.vip_actors:
        total += 80.0
    total += _age_pressure(item, now)
    return round(total, 3)


def age_minutes(item: FeedItem, now: datetime) -> float:
    since = item.occurred_at or item.created_at
    if since is None:
        return 0.0
    return max(0.0, (now - since).total_seconds() / 60)


def _deadline_pressure(deadline: datetime | None, now: datetime) -> float:
    if deadline is None:
        return 0.0
    hours = (deadline - now).total_seconds() / 3600
    if hours <= 0:
        return 200.0
    if hours < 3:
        return 120.0
    if hours < 24:
        return 60.0
    return 0.0


def _age_pressure(item: FeedItem, now: datetime) -> float:
    """A nudge, never a lever. Capped so that waiting long enough can reorder
    items inside a tier but can never lift one out of it."""
    return min(60.0, age_minutes(item, now) / 10)
