"""Read-time tier and score. Sections 3.8 and 3.9 of the MVP plan.

Nothing in here is stored. Both functions take an explicit ``now`` rather than
reading the clock themselves, which is what makes "the same row says something
different an hour later" a testable claim instead of a hope.

The card feed and the grouped list both call ``score``, so their order can never
disagree.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo

from backend.models.feed import FeedItem, UserPreferences
from backend.models.tiers import Tier, at_least, clamp
from backend.services.tier_bands import Banded, Deterministic, linear_reason, policy_for

# Tier dominates. The gaps (10_000) are wide enough that no stack of source
# weight plus bonuses on a lower tier can outrank the tier above it.
_TIER_WEIGHT: dict[Tier, float] = {
    Tier.URGENT: 30_000.0,
    Tier.TODAY: 20_000.0,
    Tier.CAN_WAIT: 10_000.0,
    Tier.NOISE: 0.0,
}

# Within a tier, order by platform. A deliberately simple first cut: a fixed
# source priority, spaced (1_000) well above the tie-break bonuses below (max
# ~640) so the platform decides the order and the bonuses only break ties within
# one platform, yet small enough (max 6_000) never to cross a tier. A smarter
# per-item ordering can replace this later without touching the tier math.
_SOURCE_WEIGHT: dict[str, float] = {
    "github": 6_000.0,
    "linear": 5_000.0,
    "calendar": 4_000.0,
    "slack": 3_000.0,
    "gmail": 2_000.0,
    "google_docs": 1_000.0,
}

# Large enough to sink an item below every live one regardless of its weight.
_SUPPRESSED = -1_000_000.0

_URGENT_STALE_AFTER = timedelta(hours=24)


def effective_tier(
    item: FeedItem, *, now: datetime, tz: tzinfo = timezone.utc
) -> Tier:
    """What tier this item is *right now*.

    One branch per policy shape (``tier_bands.Policy``):

    - ``Deterministic`` with a read-time function (calendar, Linear) hands the
      whole judgement to that function, which owns its own clock and due-date
      logic — a passed meeting is not pinned Urgent, an overdue Linear task is
      not demoted by the generic stale rule.
    - ``Deterministic`` with a fixed tier returns it.
    - ``Banded`` confines the model's rating to ``[floor, ceiling]``. A failed
      attempt (attempted, no ``llm_tier``) surfaces at the ceiling; an item with
      no model verdict and no attempt (a label-pinned or legacy row) falls back
      to its stored ``rule_tier``. Deadline pressure can lift within the band.

    ``tz`` is the user's timezone, used only where "today" is a calendar day
    rather than a duration (a Linear due date). Everything else is duration math
    and needs no zone.
    """
    policy = policy_for(item.signal)

    if isinstance(policy, Deterministic):
        if policy.tier_fn is not None:
            return policy.tier_fn(item, now, tz)
        return policy.tier  # a fixed deterministic tier

    # Banded: the model's territory. A model that was attempted and gave up
    # surfaces at the ceiling (Decision B); a genuinely held item is filtered out
    # in list_feed before it reaches this. Everything else uses the model's
    # rating if it landed, otherwise the stored rule tier (a label-pinned or
    # legacy row), and either way stays subject to the deadline corrections below.
    if item.needs_llm and item.llm_tier is None and item.llm_attempted_at is not None:
        return policy.ceiling

    tier = clamp(item.llm_tier or item.rule_tier, policy.floor, policy.ceiling)

    overdue = item.deadline is not None and item.deadline <= now
    if overdue:
        return clamp(Tier.URGENT, policy.floor, policy.ceiling)
    if item.deadline is not None and item.deadline - now <= timedelta(hours=3):
        tier = clamp(at_least(tier, Tier.TODAY), policy.floor, policy.ceiling)

    # An urgent item nobody chased for a day was not urgent. Without this the
    # top tier silts up and stops carrying information.
    if tier is Tier.URGENT and item.handled_at is None:
        since = item.occurred_at or item.created_at
        if since is not None and now - since > _URGENT_STALE_AFTER:
            return Tier.TODAY

    return tier


def read_time_reason(
    item: FeedItem, *, now: datetime, tz: tzinfo = timezone.utc
) -> str | None:
    """A deterministic reason computed on read, or None to use the stored one.

    Only Linear's due-date line is worth showing deterministically; every other
    deterministic card would just restate its tag. The model's reason (on Banded
    rows) is untouched."""
    return linear_reason(item, now, tz)


def score(
    item: FeedItem, prefs: UserPreferences, *, now: datetime, tz: tzinfo = timezone.utc
) -> float:
    """Rank within and across tiers. Higher sorts first."""
    if item.repo and item.repo in prefs.muted_repos:
        return _SUPPRESSED
    if item.context_chip and item.context_chip in prefs.muted_channels:
        return _SUPPRESSED
    if item.snoozed_until is not None and item.snoozed_until > now:
        return _SUPPRESSED

    total = _TIER_WEIGHT[effective_tier(item, now=now, tz=tz)]
    total += _SOURCE_WEIGHT.get(item.source, 0.0)
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
