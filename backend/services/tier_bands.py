"""The triage policy, as one table.

Every ``(source, signal)`` maps to a band: a floor, a ceiling, the tier to show
before the model has spoken (``default``), whether the model runs at all, and
the card's tag. The model only ever *rates urgency*; the band decides how far
that rating is allowed to move (``clamp(rating, floor, ceiling)`` in
``ranking.effective_tier``). There is no precedence ladder and no per-case
branch: to change what a source does, edit its row here.

``signal`` is the canonical reason a ``RawEvent`` is normalised to
(``rules._canonical_reason``). It is stored on the feed row so the band can be
recovered at read time, which is where the clamp happens — so editing a row here
re-tiers existing items on the next read, no re-ingest.

Tiers, low to high: ``noise < can_wait < today < urgent``. ``noise`` is the
"later" bucket the app shows under that label; ``today`` is "by upcoming
deadline".
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.models.tiers import Tier, TypeTag, clamp

U = Tier.URGENT
T = Tier.TODAY
C = Tier.CAN_WAIT
N = Tier.NOISE


@dataclass(frozen=True)
class Band:
    default: Tier  # shown immediately, before the model has rated it
    floor: Tier  # the model can never sink an item below this
    ceiling: Tier  # nor lift it above this
    type_tag: TypeTag
    runs_llm: bool  # whether this item is queued for the model at all
    # Only consulted for a settled ``noise`` item: True drops it from the store
    # (newsletters, subscriptions — fetched live in Later, never archived);
    # False keeps it as a visible "later" row (the user's own untouched tasks).
    ephemeral: bool = True


# The single source of truth. Keyed by canonical signal.
TIER_BANDS: dict[str, Band] = {
    # --- GitHub: stated urgency, no model ---------------------------------
    "security_alert": Band(U, U, U, TypeTag.ALERT, runs_llm=False),
    "ci_failure_mine": Band(U, U, U, TypeTag.ALERT, runs_llm=False),
    "ci_failure_other": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    "ci_ok": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    "review_request_removed": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    # --- GitHub: a gate or a person is waiting; the model rates within band -
    "approval_requested": Band(T, T, U, TypeTag.APPROVE, runs_llm=True),
    "review_requested": Band(T, T, U, TypeTag.REVIEW, runs_llm=True),
    "changes_requested_mine": Band(T, T, U, TypeTag.DECIDE, runs_llm=True),
    "assign": Band(T, T, U, TypeTag.ASSIGNED, runs_llm=True),
    # A mention/comment is a can_wait floor: never later, never auto-urgent.
    "mention": Band(C, C, U, TypeTag.REPLY, runs_llm=True),
    "team_mention": Band(C, C, U, TypeTag.REPLY, runs_llm=True),
    "comment": Band(C, C, U, TypeTag.COMMENT, runs_llm=True),
    # --- Slack ------------------------------------------------------------
    "slack_dm": Band(T, C, U, TypeTag.REPLY, runs_llm=True),
    "slack_mention": Band(C, C, U, TypeTag.REPLY, runs_llm=True),
    "slack_thread_reply": Band(C, C, U, TypeTag.REPLY, runs_llm=True),
    "slack_bot_failure": Band(T, C, U, TypeTag.ALERT, runs_llm=True),
    "slack_bot_noise": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    # --- Gmail: the only source that may sink to later --------------------
    "gmail_message": Band(C, N, U, TypeTag.REPLY, runs_llm=True),
    "gmail_bulk": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    # --- Linear: priority and due date are stated fields ------------------
    "linear_urgent": Band(U, T, U, TypeTag.ASSIGNED, runs_llm=False),
    "linear_due": Band(T, T, U, TypeTag.ASSIGNED, runs_llm=True),
    "linear_high": Band(C, C, U, TypeTag.ASSIGNED, runs_llm=True),
    "linear_in_progress": Band(C, C, U, TypeTag.ASSIGNED, runs_llm=True),
    # No priority and no date: the user's own task nobody is waiting on. It
    # stays as a visible "later" row (ephemeral=False) rather than being
    # dropped like a newsletter.
    "linear_assigned": Band(N, N, C, TypeTag.ASSIGNED, runs_llm=False, ephemeral=False),
    "linear_backlog": Band(N, N, C, TypeTag.ASSIGNED, runs_llm=False, ephemeral=False),
    # --- Calendar ---------------------------------------------------------
    "calendar_starting": Band(U, T, U, TypeTag.FYI, runs_llm=False),
    "calendar_invite": Band(T, C, U, TypeTag.RSVP, runs_llm=True),
    "calendar_changed": Band(T, C, U, TypeTag.FYI, runs_llm=False),
    "calendar_cancelled": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    # --- Google Docs (delivered via Gmail notifications) ------------------
    "docs_mention": Band(C, C, U, TypeTag.COMMENT, runs_llm=True),
    "docs_comment": Band(C, C, U, TypeTag.COMMENT, runs_llm=True),
    "docs_share": Band(C, C, U, TypeTag.FYI, runs_llm=True),
    "docs_edited": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    # --- Generic / terminal -----------------------------------------------
    "invitation": Band(T, C, U, TypeTag.DECIDE, runs_llm=False),
    "state_change": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    "subscribed": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    "author": Band(N, N, N, TypeTag.FYI, runs_llm=False),
    "manual": Band(N, N, N, TypeTag.FYI, runs_llm=False),
}

# An unrecognised signal is handled two ways by the same band. At ingest its
# ``default`` (noise) plus ``ephemeral`` drops it — an unknown reason must not be
# able to shout. At read time its band is deliberately *unclamped* (floor noise,
# ceiling urgent), so a stored row whose signal is missing (a legacy row, or one
# whose signal has since left the table) renders at its own tier rather than
# being force-collapsed to noise.
UNKNOWN = Band(N, N, U, TypeTag.FYI, runs_llm=False)


def band_for(signal: str | None) -> Band:
    """The band a stored item is clamped to at read time. Unknown or missing
    signals fall back to the unclamped ``UNKNOWN`` band."""
    if signal is None:
        return UNKNOWN
    return TIER_BANDS.get(signal, UNKNOWN)


def label_override(band: Band, *, urgent: bool, low: bool) -> tuple[Tier, bool]:
    """A structured label is a stated urgency, so it settles the tier without
    the model. Urgent labels pin to the ceiling, low ones to the floor. Returns
    ``(tier, runs_llm)``; ``runs_llm`` is always False when a label decided it."""
    if urgent:
        return clamp(U, band.floor, band.ceiling), False
    if low:
        return band.floor, False
    return band.default, band.runs_llm
