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
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

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
You triage work notifications for a busy professional. For each item, rate how
urgently it needs this user, and write one short line explaining what it is.

Rate only what the content shows. A separate policy already sets the floor and
ceiling each item can land in from its source and type, so you do not need to
protect any category — rate honestly and it will be confined to sane bounds.

TIERS
- urgent:   a specific person is actively waiting on this user right now, OR a
            hard deadline has passed or falls within a few hours.
- today:    needs handling before end of day; nobody is stopped right now.
            Includes anything with a stated deadline of today or tomorrow.
- can_wait: genuinely needs the user eventually, no time pressure stated.
- noise:    no action is asked of this user.

RULES
- Be conservative. If torn between urgent and today, choose today.
- A stated future deadline ("by tomorrow EOD") means today, never urgent.
- A direct question addressed to this user with no deadline means urgent.
- Recency alone never makes something urgent.
- Today's date is given as `now`, and each item carries `sent_at`. Use them.
  Anything whose moment has already passed, such as an invitation to a meeting
  that has happened, is noise: there is nothing left to do about it.

WRITING THE TWO LINES
- summary: what this actually asks of the user, in their words. Name the thing
  being asked for. "Priya needs the staging deploy unblocked" is useful;
  "a Slack message from Priya" is not, because the card already says that.
- reason: the specific evidence for the tier, not a restatement of it. Good:
  "asks a direct question, no deadline given". Useless: "direct reply",
  "no subject", "it is an email". If the only evidence is that the item exists,
  the tier is wrong and should be lower.
- Never mention the source, the sender's name alone, or the absence of a
  subject line as a reason. None of those make anything urgent.

OUTPUT
A JSON array with one object per input id, no prose:
{"id": "...", "tier": "urgent|today|can_wait|noise",
 "summary": "<=90 chars: what it asks of this user",
 "reason":  "<=60 chars: the evidence for that tier"}
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
    #: Items still without a verdict after this pass (held or failed). The
    #: syncing pill reports this as "still classifying N" so a finished sync with
    #: an incomplete feed does not read as "nothing else needs you".
    unclassified: int = 0
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
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._model = model
        self._repo = repo
        self._cache = cache
        self._budget = daily_budget
        self._model_name = model_name
        self._now = clock or (lambda: datetime.now(timezone.utc))

    def classify_pending(
        self, user_id: str, *, time_budget: float | None = None
    ) -> ClassificationReport:
        """Classify this user's held items.

        ``time_budget`` (seconds) bounds the synchronous refresh path: once it is
        exceeded no new batch is *started*, and whatever is left stays held for
        the next pass. Without a budget (the background path) it runs the whole
        queue up to ``daily_budget``."""
        pending = self._repo.list_pending_classification(user_id, limit=self._budget)
        report = ClassificationReport(requested=len(pending))
        if not pending:
            return report

        deadline = None
        if time_budget is not None:
            deadline = self._now() + timedelta(seconds=time_budget)

        uncached = [item for item in pending if not self._apply_cached(user_id, item, report)]
        tiers: list[Tier] = []

        for start in range(0, len(uncached), BATCH_SIZE):
            if deadline is not None and self._now() >= deadline:
                break
            batch = uncached[start : start + BATCH_SIZE]
            tiers.extend(self._run_batch(user_id, batch, report))

        report.unclassified = report.requested - report.classified
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

    def classify_item(self, user_id: str, item: FeedItem) -> ClassificationReport:
        """Classify a single item now (the webhook path).

        The webhook acks Composio's delivery first, then calls this on the one
        pushed item, so the item appears already-classified about a second later
        rather than as a placeholder — without coupling delivery to model
        latency. Never the whole-user sweep: one DM must not re-run the backlog."""
        report = ClassificationReport(requested=1)
        if not (item.needs_llm and item.llm_tier is None):
            return report
        if not self._apply_cached(user_id, item, report):
            self._run_batch(user_id, [item], report)
        report.unclassified = report.requested - report.classified
        return report

    def _run_batch(
        self, user_id: str, batch: list[FeedItem], report: ClassificationReport
    ) -> list[Tier]:
        """One model batch: judge, apply, and mark every item attempted.

        Whatever the model does not return a usable verdict for — a failed batch
        or an id it silently dropped — is still marked *attempted*, so it stops
        being held and surfaces at its band ceiling instead of vanishing."""
        verdicts = self._judge(batch)
        if verdicts is None:
            report.failed_batches += 1
            self._repo.mark_attempted(
                user_id, [item.id for item in batch], at=self._now()
            )
            return []
        applied = self._apply(user_id, batch, verdicts, report)
        judged_ids = {item.id for item, _ in applied}
        missed = [item.id for item in batch if item.id not in judged_ids]
        if missed:
            self._repo.mark_attempted(user_id, missed, at=self._now())
        return [tier for _, tier in applied]

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
            user_id, item.id, tier=tier, summary=summary, reason=reason, at=self._now()
        )
        report.from_cache += 1
        report.classified += 1
        return True

    def _judge(self, batch: list[FeedItem]) -> list[dict] | None:
        """One request, one retry, then give up on this batch.

        Retrying more would delay every other batch behind it for an outcome
        that a second attempt has already shown to be unlikely.
        """
        now = self._now().isoformat()
        payload = [self._to_payload(item, now) for item in batch]
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
    ) -> list[tuple[FeedItem, Tier]]:
        by_id = {item.id: item for item in batch}
        applied: list[tuple[FeedItem, Tier]] = []

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
                user_id,
                item.id,
                tier=tier,
                summary=summary,
                reason=reason,
                at=self._now(),
            )
            if item.content_hash:
                self._cache.put(
                    item.content_hash, tier, summary, reason, model=self._model_name
                )
            report.classified += 1
            applied.append((item, tier))

        return applied

    @staticmethod
    def _to_payload(item: FeedItem, now: str) -> dict:
        return {
            "now": now,
            "id": item.id,
            "source": item.source,
            "type": item.type_tag.value,
            "sender": item.sender_name or item.sender_handle,
            "title": truncate(item.title),
            "text": truncate(item.body_text()),
            "labels": item.raw.get("labels") or [],
            "deadline": item.deadline.isoformat() if item.deadline else None,
            "is_direct": item.is_blocking,
            # Without these the model cannot tell a past event from a future
            # one. It read a 17 July invitation as "far in the future" a week
            # after the meeting had happened, and filed it under Can wait.
            "sent_at": (item.occurred_at or item.created_at).isoformat()
            if (item.occurred_at or item.created_at)
            else None,
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
