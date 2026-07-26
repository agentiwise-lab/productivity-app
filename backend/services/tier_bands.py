"""The triage policy, as one table.

Every canonical ``signal`` maps to a ``Policy``, a tagged union of two shapes:

- ``Deterministic`` — the rules (or the clock) fix the tier with no model. It
  carries either a fixed ``tier`` or a read-time ``tier_fn(item, now, tz)`` for
  the sources whose tier moves with the clock (calendar proximity, a Linear due
  date crossing into today). Folding those functions into the table is what
  keeps ``ranking.effective_tier`` a single branch instead of a growing list of
  ``if source == ...`` special cases.
- ``Banded`` — the model rates urgency and the rating is confined to
  ``[floor, ceiling]``. Being ``Banded`` *is* "runs the model": there is no
  separate boolean. The item is held off-screen until the model has spoken; if
  the model is attempted and fails, it surfaces at the ``ceiling`` (Decision B).

``signal`` is the canonical reason a ``RawEvent`` is normalised to
(``rules._canonical_reason``). It is stored on the feed row so the policy can be
recovered at read time, which is where the tier is computed — so editing a row
here re-tiers existing items on the next read, no re-ingest.

Tiers, low to high: ``noise < can_wait < today < urgent``. ``noise`` is the
"later" bucket shown under that label; ``today`` is "by upcoming deadline".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from typing import TYPE_CHECKING, Callable, Union

from backend.models.tiers import Tier, TypeTag

if TYPE_CHECKING:  # avoid importing the model at module load; only types need it
    from backend.models.feed import FeedItem

U = Tier.URGENT
T = Tier.TODAY
C = Tier.CAN_WAIT
N = Tier.NOISE

# A meeting is urgent within this window before it starts (and while it runs).
STARTING_SOON = timedelta(hours=1)

TierFn = Callable[["FeedItem", datetime, tzinfo], Tier]


@dataclass(frozen=True)
class Deterministic:
    """The rules or the clock settle the tier; the model never runs.

    Exactly one of ``tier`` / ``tier_fn`` is set. ``tier_fn`` is consulted at
    read time with the current clock and the user's timezone, so a Linear task
    flips to urgent the day its due date arrives without being re-ingested.
    ``ephemeral`` marks settled-noise that is dropped at ingest rather than kept
    as a visible "later" row (a newsletter, not the user's own backlog).
    """

    type_tag: TypeTag
    tier: Tier | None = None
    tier_fn: TierFn | None = None
    ephemeral: bool = True

    runs_llm = False


@dataclass(frozen=True)
class Banded:
    """The model rates urgency; the rating is clamped to ``[floor, ceiling]``.

    Held off-screen until the model lands. On a failed attempt the item is shown
    at ``ceiling`` (Decision B): when the model cannot judge it, err toward
    surfacing rather than burying.
    """

    floor: Tier
    ceiling: Tier
    type_tag: TypeTag
    ephemeral: bool = True  # never a settled-noise item; kept for a uniform read

    runs_llm = True


Policy = Union[Deterministic, Banded]


# ---------------------------------------------------------------- read-time fns


def _calendar_tier(item: "FeedItem", now: datetime, tz: tzinfo) -> Tier:
    """A meeting is urgent within the hour before it starts (and while it runs);
    by-EOD if it is on the day but further out. ``occurred_at`` is the start.

    Purely a function of how close the start is, so it is timezone-independent
    (a duration, not a wall-clock date). Passed meetings are dropped before
    display in ``feed.list_feed``, so this never has to represent "over"."""
    start = item.occurred_at
    if start is None:
        return T
    if start - now <= STARTING_SOON:
        return U
    return T


def _linear_tier(item: "FeedItem", now: datetime, tz: tzinfo) -> Tier:
    """Linear urgency is stated by the due date alone; priority is ignored.

    Completed issues never reach here (dropped at ingest). No due date is a task
    nobody is waiting on, so it can wait. A due date that is today or already
    past is urgent — and "today" is the user's calendar day, not UTC's, so a
    task due the 24th is not urgent at 00:15 on the 24th in the user's own zone.
    A future due date can wait; on the day it is due it is By EOD; once the day
    has passed it is Urgent (Vicky's call 2026-07-26: due today -> By EOD, in the
    past -> Urgent, no matter the status)."""
    if item.deadline is None:
        return C
    due_date = item.deadline.date()
    today = now.astimezone(tz).date()
    if due_date < today:
        return U
    if due_date == today:
        return T
    return C


def linear_reason(item: "FeedItem", now: datetime, tz: tzinfo) -> str | None:
    """The one deterministic reason worth showing: a Linear task's date line.

    Every other deterministic card restates its own tag ("security alert",
    "meeting"), which the card already says. The due date is new information the
    card does not otherwise carry. Returns None for a future or absent date so
    the detail sheet simply omits the "why" box."""
    if item.deadline is None:
        return None
    due_date = item.deadline.date()
    today = now.astimezone(tz).date()
    if due_date < today:
        return f"Overdue since {item.deadline:%-d %b}"
    if due_date == today:
        return "Due today"
    return None


# One policy shared by every Linear signal (priority is not consulted).
_LINEAR = Deterministic(type_tag=TypeTag.ASSIGNED, tier_fn=_linear_tier, ephemeral=False)


def _calendar(tag: TypeTag) -> Deterministic:
    return Deterministic(type_tag=tag, tier_fn=_calendar_tier, ephemeral=False)


# The single source of truth. Keyed by canonical signal.
TIER_BANDS: dict[str, Policy] = {
    # --- GitHub: stated urgency, no model ---------------------------------
    "security_alert": Deterministic(type_tag=TypeTag.ALERT, tier=U),
    "ci_failure_mine": Deterministic(type_tag=TypeTag.ALERT, tier=U),
    # A broken build is worth surfacing even on a repo you only watch
    # (Vicky's call 2026-07-26): urgent, not buried noise.
    "ci_failure_other": Deterministic(type_tag=TypeTag.ALERT, tier=U),
    "ci_ok": Deterministic(type_tag=TypeTag.FYI, tier=N),
    "review_request_removed": Deterministic(type_tag=TypeTag.FYI, tier=N),
    # --- GitHub: a gate or a person is waiting; the model rates within band -
    "approval_requested": Banded(T, U, TypeTag.APPROVE),
    "review_requested": Banded(T, U, TypeTag.REVIEW),
    "changes_requested_mine": Banded(T, U, TypeTag.DECIDE),
    "assign": Banded(T, U, TypeTag.ASSIGNED),
    # A mention/comment is a can_wait floor: never later, never auto-urgent.
    "mention": Banded(C, U, TypeTag.REPLY),
    "team_mention": Banded(C, U, TypeTag.REPLY),
    "comment": Banded(C, U, TypeTag.COMMENT),
    # --- Slack ------------------------------------------------------------
    "slack_dm": Banded(C, U, TypeTag.REPLY),
    "slack_mention": Banded(C, U, TypeTag.REPLY),
    "slack_thread_reply": Banded(C, U, TypeTag.REPLY),
    "slack_bot_failure": Banded(C, U, TypeTag.ALERT),
    "slack_bot_noise": Deterministic(type_tag=TypeTag.FYI, tier=N),
    # --- Gmail: the only source that may sink to later --------------------
    # Personal inbox and the transactional slice (updates/forums/list mail) both
    # go to the model floored at later, so a payment/renewal notice is seen and
    # not buried; only true bulk (promotions/social/spam/trash) skips the model.
    "gmail_message": Banded(N, U, TypeTag.REPLY),
    "gmail_transactional": Banded(N, U, TypeTag.REPLY),
    "gmail_bulk": Deterministic(type_tag=TypeTag.FYI, tier=N),
    # --- Linear: due date is a stated field; the model never runs ----------
    "linear": _LINEAR,
    "linear_urgent": _LINEAR,
    "linear_due": _LINEAR,
    "linear_high": _LINEAR,
    "linear_in_progress": _LINEAR,
    "linear_assigned": _LINEAR,
    "linear_backlog": _LINEAR,
    # A comment on your issue is prose asking something: the model rates it,
    # like a Slack mention, inside Can wait .. Urgent.
    "linear_comment": Banded(C, U, TypeTag.REPLY),
    # --- Calendar: tier is set at read time from how close the start is -----
    "calendar_starting": _calendar(TypeTag.FYI),
    "calendar_meeting": _calendar(TypeTag.FYI),
    "calendar_invite": _calendar(TypeTag.RSVP),
    "calendar_changed": _calendar(TypeTag.FYI),
    "calendar_cancelled": Deterministic(type_tag=TypeTag.FYI, tier=N),
    # --- Google Docs (delivered via Gmail notifications) ------------------
    "docs_mention": Banded(C, U, TypeTag.COMMENT),
    "docs_comment": Banded(C, U, TypeTag.COMMENT),
    "docs_share": Banded(C, U, TypeTag.FYI),
    "docs_edited": Deterministic(type_tag=TypeTag.FYI, tier=N),
    # --- Generic / terminal -----------------------------------------------
    "invitation": Deterministic(type_tag=TypeTag.DECIDE, tier=T),
    "state_change": Deterministic(type_tag=TypeTag.FYI, tier=N),
    "subscribed": Deterministic(type_tag=TypeTag.FYI, tier=N),
    "author": Deterministic(type_tag=TypeTag.FYI, tier=N),
    "manual": Deterministic(type_tag=TypeTag.FYI, tier=N),
}

# An unrecognised or missing signal (a legacy row, or one whose signal has since
# left the table). Modelled as a wide band so a stored row renders at its own
# recorded tier rather than being force-collapsed: with ``llm_tier`` None and the
# item not marked as an attempted-and-failed model item, ``effective_tier`` falls
# back to the stored ``rule_tier`` clamped into ``[noise, urgent]`` — i.e. the
# pre-band behaviour.
UNKNOWN = Banded(N, U, TypeTag.FYI)


def policy_for(signal: str | None) -> Policy:
    """The policy a stored item is tiered by at read time. Unknown or missing
    signals fall back to the wide ``UNKNOWN`` band."""
    if signal is None:
        return UNKNOWN
    return TIER_BANDS.get(signal, UNKNOWN)
