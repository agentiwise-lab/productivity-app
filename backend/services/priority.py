"""Priority scoring: (FeedItem, UserPreferences) -> float.

Higher scores rank first. The tracer uses a transparent additive composite; the
two-axis (confidence x severity) model from the research is a phase-2 refinement.
The signals here are the ones GitHub gives us cheaply: action type, whether
someone is blocked on the user, deadline proximity, and user preferences.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol

from backend.models.feed import ActionType, FeedItem, UserPreferences


class PriorityService(Protocol):
    def score(self, item: FeedItem, prefs: UserPreferences) -> float:
        ...


# Base weight by what the user is being asked to do.
_ACTION_WEIGHT: dict[ActionType, float] = {
    ActionType.APPROVE: 5.0,
    ActionType.REVIEW: 4.0,
    ActionType.REPLY: 3.5,
    ActionType.DECIDE: 3.0,
    ActionType.FYI: 0.5,
}


class DefaultPriorityService:
    def score(self, item: FeedItem, prefs: UserPreferences) -> float:
        if item.repo in prefs.muted_repos:
            return 0.0
        score = _ACTION_WEIGHT.get(item.action_type, 0.5)
        if item.is_blocking:
            score += 3.0  # someone is waiting on this user
        if item.repo in prefs.priority_repos:
            score += 1.5
        if any(actor.login in prefs.vip_actors for actor in item.actors):
            score += 1.5
        score += self._deadline_boost(item.deadline)
        return round(score, 3)

    @staticmethod
    def _deadline_boost(deadline: datetime | None) -> float:
        if deadline is None:
            return 0.0
        hours = (deadline - datetime.now(timezone.utc)).total_seconds() / 3600
        if hours <= 0:
            return 3.0  # overdue
        if hours < 24:
            return 2.0
        if hours < 72:
            return 1.0
        return 0.0
