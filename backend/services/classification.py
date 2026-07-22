"""Classification: RawEvent -> ActionType.

Deterministic and rule-based for the tracer. GitHub's notification ``reason`` is
already a coarse classifier, so this is mostly a lookup plus two refinements. The
LLM classifier (phase 2) handles only the ambiguous residue this cannot; it does
not replace these rules.
"""

from __future__ import annotations

from typing import Protocol

from backend.models.events import RawEvent
from backend.models.feed import ActionType


class ClassificationService(Protocol):
    def classify(self, event: RawEvent) -> ActionType:
        ...


# GitHub notification `reason` -> action type. Unknown reasons fall back to FYI.
_REASON_MAP: dict[str, ActionType] = {
    "review_requested": ActionType.REVIEW,
    "approval_requested": ActionType.APPROVE,
    "mention": ActionType.REPLY,
    "team_mention": ActionType.REPLY,
    "comment": ActionType.REPLY,
    "assign": ActionType.DECIDE,
    "security_alert": ActionType.DECIDE,
    "invitation": ActionType.DECIDE,
    "author": ActionType.FYI,
    "state_change": ActionType.FYI,
    "subscribed": ActionType.FYI,
    "manual": ActionType.FYI,
}


class DefaultClassificationService:
    def classify(self, event: RawEvent) -> ActionType:
        # Refinements that override the coarse reason.
        if event.review_state == "changes_requested":
            return ActionType.DECIDE
        if event.reason == "ci_activity":
            return (
                ActionType.DECIDE
                if event.check_conclusion == "failure"
                else ActionType.FYI
            )
        return _REASON_MAP.get(event.reason, ActionType.FYI)
