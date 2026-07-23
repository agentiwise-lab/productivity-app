"""LLM classification. Section 4 of the MVP plan.

Only the items the rules deferred reach the model, batched, cached on content
hash, and capped by a daily budget.

The single rule that governs every path in this file: **the feed must never
block on the model, and must never be worse for having tried.** Every failure
mode ends the same way, with the item keeping the rule tier the ingest path
already gave it. That is why nothing here raises: a dead model degrades the
product to rules-only, which still works, rather than to an empty screen.
"""

from __future__ import annotations

import json
import logging
from typing import Protocol

from pydantic import BaseModel

from backend.models.feed import FeedItem
from backend.models.tiers import Tier
from backend.repositories.feed_repository import FeedRepository

log = logging.getLogger(__name__)

BATCH_SIZE = 20
# A stated request usually sits at the end of a message, so a plain head
# truncate is the one cut most likely to remove the thing being judged.
HEAD_CHARS = 250
TAIL_CHARS = 150
# Above this share of urgent in one batch, the model has stopped discriminating.
ALARM_URGENT_RATIO = 0.4

SYSTEM_PROMPT = """\
You triage work notifications for a busy professional. For each item, assign a
tier and write one short line explaining what it is.

TIERS
- urgent:   a specific person is actively waiting on this user right now, OR a
            hard deadline has passed or falls within a few hours.
- today:    needs handling before end of day, but nobody is stopped right now.
            Includes anything with a stated deadline of today or tomorrow.
- can_wait: genuinely needs the user eventually, no time pressure stated.
- noise:    no action required of this user. Status updates, automated messages,
            conversation they were not addressed in.

RULES
- Be conservative. If torn between urgent and today, choose today.
- A stated future deadline ("by tomorrow EOD") means today, never urgent.
- A direct question addressed to this user with no deadline means urgent.
- Labels such as P0, blocker, critical, sev1 or production mean urgent.
- An item assigned to this user is never can_wait unless it explicitly signals
  low priority. When there is no signal at all, choose today.
- Bot and automated messages are noise unless they report a failure in this
  user's own work.
- Recency alone never makes something urgent.

OUTPUT
A JSON array with one object per input id, no prose:
{"id": "...", "tier": "urgent|today|can_wait|noise",
 "summary": "<=90 chars: what it is and why it matters",
 "reason":  "<=60 chars: why this tier"}
"""


class Model(Protocol):
    def judge(self, items: list[dict]) -> list[dict]:
        """Send one batch and return the parsed verdicts."""
        ...


class ClassificationCache(Protocol):
    def get(self, content_hash: str) -> tuple[Tier, str, str] | None:
        ...

    def put(
        self, content_hash: str, tier: Tier, summary: str, reason: str, *, model: str
    ) -> None:
        ...


class ClassificationReport(BaseModel):
    """What one classification pass did. Returned rather than logged so the
    caller can act on it, and so the alarm is testable."""

    requested: int = 0
    classified: int = 0
    from_cache: int = 0
    failed_batches: int = 0
    urgent_ratio: float = 0.0
    alarm: bool = False


class InMemoryClassificationCache:
    def __init__(self) -> None:
        self._entries: dict[str, tuple[Tier, str, str]] = {}

    def get(self, content_hash: str) -> tuple[Tier, str, str] | None:
        return self._entries.get(content_hash)

    def put(
        self, content_hash: str, tier: Tier, summary: str, reason: str, *, model: str
    ) -> None:
        self._entries[content_hash] = (tier, summary, reason)


def truncate(text: str) -> str:
    """Keep the head and the tail, drop the middle."""
    if len(text) <= HEAD_CHARS + TAIL_CHARS:
        return text
    return f"{text[:HEAD_CHARS]} [...] {text[-TAIL_CHARS:]}"


class DefaultClassificationService:
    def __init__(
        self,
        model: Model,
        repo: FeedRepository,
        cache: ClassificationCache,
        daily_budget: int = 200,
        model_name: str = "google/gemini-2.5-flash",
    ) -> None:
        self._model = model
        self._repo = repo
        self._cache = cache
        self._budget = daily_budget
        self._model_name = model_name

    def classify_pending(self, user_id: str) -> ClassificationReport:
        pending = self._repo.list_pending_classification(user_id, limit=self._budget)
        report = ClassificationReport(requested=len(pending))
        if not pending:
            return report

        uncached = [item for item in pending if not self._apply_cached(user_id, item, report)]
        tiers: list[Tier] = []

        for start in range(0, len(uncached), BATCH_SIZE):
            batch = uncached[start : start + BATCH_SIZE]
            verdicts = self._judge(batch)
            if verdicts is None:
                report.failed_batches += 1
                continue
            tiers.extend(self._apply(user_id, batch, verdicts, report))

        if tiers:
            report.urgent_ratio = sum(t is Tier.URGENT for t in tiers) / len(tiers)
            report.alarm = report.urgent_ratio > ALARM_URGENT_RATIO
            if report.alarm:
                log.warning(
                    "classification alarm: %.0f%% of %d items marked urgent",
                    report.urgent_ratio * 100,
                    len(tiers),
                )
        return report

    # ------------------------------------------------------------ internals

    def _apply_cached(
        self, user_id: str, item: FeedItem, report: ClassificationReport
    ) -> bool:
        if item.content_hash is None:
            return False
        hit = self._cache.get(item.content_hash)
        if hit is None:
            return False
        tier, summary, reason = hit
        self._repo.apply_classification(
            user_id, item.id, tier=tier, summary=summary, reason=reason
        )
        report.from_cache += 1
        report.classified += 1
        return True

    def _judge(self, batch: list[FeedItem]) -> list[dict] | None:
        """One request, one retry, then give up on this batch.

        Retrying more would delay every other batch behind it for an outcome
        that a second attempt has already shown to be unlikely.
        """
        payload = [self._to_payload(item) for item in batch]
        for attempt in (1, 2):
            try:
                verdicts = self._model.judge(payload)
            except Exception:
                log.warning("classification request failed (attempt %d)", attempt, exc_info=True)
                continue
            if self._is_well_formed(verdicts):
                return verdicts
            log.warning("classification returned malformed output (attempt %d)", attempt)
        return None

    @staticmethod
    def _is_well_formed(verdicts: object) -> bool:
        return isinstance(verdicts, list) and all(
            isinstance(v, dict) and "id" in v and "tier" in v for v in verdicts
        )

    def _apply(
        self,
        user_id: str,
        batch: list[FeedItem],
        verdicts: list[dict],
        report: ClassificationReport,
    ) -> list[Tier]:
        by_id = {item.id: item for item in batch}
        applied: list[Tier] = []

        for verdict in verdicts:
            item = by_id.get(verdict.get("id"))
            if item is None:
                # An id we never sent. Writing it would corrupt an unrelated
                # item, or invent one.
                log.warning("classification returned an unknown id: %r", verdict.get("id"))
                continue
            tier = _parse_tier(verdict.get("tier"))
            if tier is None:
                log.warning("classification returned an unknown tier: %r", verdict.get("tier"))
                continue

            summary = str(verdict.get("summary") or "")[:90]
            reason = str(verdict.get("reason") or "")[:60]
            self._repo.apply_classification(
                user_id, item.id, tier=tier, summary=summary, reason=reason
            )
            if item.content_hash:
                self._cache.put(
                    item.content_hash, tier, summary, reason, model=self._model_name
                )
            report.classified += 1
            applied.append(tier)

        return applied

    @staticmethod
    def _to_payload(item: FeedItem) -> dict:
        return {
            "id": item.id,
            "source": item.source,
            "type": item.type_tag.value,
            "sender": item.sender_name or item.sender_handle,
            "title": truncate(item.title),
            "text": truncate(str(item.raw.get("text") or "")),
            "labels": item.raw.get("labels") or [],
            "deadline": item.deadline.isoformat() if item.deadline else None,
            "is_direct": item.is_blocking,
        }


def _parse_tier(value: object) -> Tier | None:
    """Never coerce. An unrecognised tier is dropped, because guessing what the
    model meant is how everything silently becomes urgent."""
    try:
        return Tier(str(value).strip().lower())
    except ValueError:
        return None


def parse_model_output(content: str) -> list[dict]:
    """Parse a model reply that may be wrapped in a markdown fence."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(text)
