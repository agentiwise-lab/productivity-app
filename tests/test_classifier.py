"""LLM classification: section 4 of the MVP plan.

Almost every case here is a failure mode. That ratio is deliberate: the happy
path is one model call, and the thing that decides whether this product is
usable is what happens when the call is slow, wrong, malformed or absent. The
governing rule is that the feed degrades to rule tiers and never blocks or
blanks.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.models.feed import FeedItem, TierSource
from backend.models.tiers import Tier, TypeTag
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.services.classifier import (
    BATCH_SIZE,
    DefaultClassificationService,
    InMemoryClassificationCache,
    truncate,
)

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


class FakeModel:
    """Stands in for OpenRouter. Records the batches it was asked to judge."""

    def __init__(self, replies=None, error: Exception | None = None) -> None:
        self._replies = replies if replies is not None else []
        self._error = error
        self.batches: list[list[dict]] = []

    def judge(self, items: list[dict]) -> list[dict]:
        self.batches.append(items)
        if self._error is not None:
            raise self._error
        if callable(self._replies):
            return self._replies(items)
        return self._replies


def make_item(item_id="i1", **overrides) -> FeedItem:
    defaults = dict(
        id=item_id,
        user_id="me",
        source="slack",
        source_ref=f"slack#{item_id}",
        rule_tier=Tier.TODAY,
        type_tag=TypeTag.REPLY,
        needs_llm=True,
        title="can you unblock the staging deploy?",
        url="https://slack.com/x",
        content_hash=f"hash-{item_id}",
        occurred_at=NOW,
        created_at=NOW,
    )
    defaults.update(overrides)
    return FeedItem(**defaults)


def build(model, repo=None, cache=None, budget: int = 200):
    repo = repo or InMemoryFeedRepository()
    return (
        DefaultClassificationService(
            model=model,
            repo=repo,
            cache=cache or InMemoryClassificationCache(),
            daily_budget=budget,
        ),
        repo,
    )


def reply(item_id, tier="urgent", summary="Priya is blocked", reason="direct ask"):
    return {"id": item_id, "tier": tier, "summary": summary, "reason": reason}


# --- the happy path --------------------------------------------------------


def test_a_verdict_is_written_back_to_the_item():
    svc, repo = build(FakeModel([reply("i1")]))
    repo.upsert(make_item())
    svc.classify_pending("me")

    stored = repo.get("me", "i1")
    assert stored.llm_tier is Tier.URGENT
    assert stored.tier_source is TierSource.LLM
    assert stored.summary == "Priya is blocked"
    assert stored.reason == "direct ask"


def test_only_items_the_rules_deferred_are_sent():
    """Everything the rules already knew is free. Paying to re-judge it would
    be the most expensive way to learn nothing."""
    model = FakeModel([reply("i1")])
    svc, repo = build(model)
    repo.upsert(make_item("i1", needs_llm=True))
    repo.upsert(make_item("i2", needs_llm=False, rule_tier=Tier.URGENT))
    svc.classify_pending("me")

    assert [row["id"] for row in model.batches[0]] == ["i1"]


def test_nothing_pending_makes_no_request_at_all():
    model = FakeModel([])
    svc, _ = build(model)
    svc.classify_pending("me")
    assert model.batches == []


# --- batching and cost -----------------------------------------------------


def test_items_go_in_one_request_not_one_request_each():
    model = FakeModel(lambda items: [reply(row["id"]) for row in items])
    svc, repo = build(model)
    for n in range(5):
        repo.upsert(make_item(f"i{n}"))
    svc.classify_pending("me")

    assert len(model.batches) == 1
    assert len(model.batches[0]) == 5


def test_more_than_a_batch_is_chunked():
    model = FakeModel(lambda items: [reply(row["id"]) for row in items])
    svc, repo = build(model)
    for n in range(BATCH_SIZE + 3):
        repo.upsert(make_item(f"i{n}"))
    svc.classify_pending("me")

    assert [len(batch) for batch in model.batches] == [BATCH_SIZE, 3]


def test_a_cached_verdict_is_reused_without_calling_the_model():
    """Cache hits are what make re-opening the app free."""
    cache = InMemoryClassificationCache()
    cache.put("hash-i1", Tier.URGENT, "Priya is blocked", "direct ask", model="test")
    model = FakeModel([])
    svc, repo = build(model, cache=cache)
    repo.upsert(make_item())
    svc.classify_pending("me")

    assert model.batches == []
    assert repo.get("me", "i1").llm_tier is Tier.URGENT


def test_the_daily_budget_stops_classification_rather_than_the_feed():
    model = FakeModel(lambda items: [reply(row["id"]) for row in items])
    svc, repo = build(model, budget=2)
    for n in range(5):
        repo.upsert(make_item(f"i{n}"))
    svc.classify_pending("me")

    assert sum(len(batch) for batch in model.batches) == 2
    # The rest keep their rule tier and stay perfectly usable.
    assert repo.get("me", "i4").rule_tier is Tier.TODAY


def test_content_is_truncated_from_both_ends():
    """A plain head-truncate cuts the actual ask, because requests usually sit
    at the end of a message."""
    body = "A" * 250 + "M" * 500 + "Z" * 150
    out = truncate(body)
    assert out.startswith("A" * 250)
    assert out.endswith("Z" * 150)
    assert "M" not in out
    assert len(out) < len(body)


def test_short_content_is_left_alone():
    assert truncate("hello") == "hello"


# --- failure modes (4.4) ---------------------------------------------------


def test_a_model_outage_leaves_the_rule_tier_in_place():
    svc, repo = build(FakeModel(error=RuntimeError("openrouter is down")))
    repo.upsert(make_item())
    svc.classify_pending("me")  # must not raise

    stored = repo.get("me", "i1")
    assert stored.llm_tier is None
    assert stored.rule_tier is Tier.TODAY  # still renders, still ranked


def test_malformed_output_is_retried_once_then_abandoned():
    model = FakeModel([{"nonsense": True}])
    svc, repo = build(model)
    repo.upsert(make_item())
    svc.classify_pending("me")

    assert len(model.batches) == 2  # one retry, no more
    assert repo.get("me", "i1").llm_tier is None


def test_a_verdict_for_an_unknown_id_is_ignored():
    """The model returning an id we never sent is a hallucination, and writing
    it would corrupt an unrelated item."""
    svc, repo = build(FakeModel([reply("i1"), reply("not-a-real-item")]))
    repo.upsert(make_item())
    svc.classify_pending("me")

    assert repo.get("me", "i1").llm_tier is Tier.URGENT
    assert repo.get("me", "not-a-real-item") is None


def test_an_invalid_tier_is_dropped_not_coerced():
    svc, repo = build(FakeModel([reply("i1", tier="EXTREMELY_URGENT")]))
    repo.upsert(make_item())
    svc.classify_pending("me")
    assert repo.get("me", "i1").llm_tier is None


def test_a_partial_response_still_applies_the_verdicts_it_did_return():
    """One missing row must not throw away the other nineteen."""
    svc, repo = build(FakeModel([reply("i1")]))
    repo.upsert(make_item("i1"))
    repo.upsert(make_item("i2"))
    svc.classify_pending("me")

    assert repo.get("me", "i1").llm_tier is Tier.URGENT
    assert repo.get("me", "i2").llm_tier is None


def test_a_batch_that_is_mostly_urgent_raises_the_alarm():
    """A model that marks everything urgent has defeated the product, so this
    has to be visible rather than merely wrong."""
    model = FakeModel(lambda items: [reply(row["id"], tier="urgent") for row in items])
    svc, repo = build(model)
    for n in range(5):
        repo.upsert(make_item(f"i{n}"))
    report = svc.classify_pending("me")

    assert report.urgent_ratio == pytest.approx(1.0)
    assert report.alarm is True


def test_a_normal_spread_raises_no_alarm():
    tiers = iter(["urgent", "today", "today", "can_wait", "noise"])
    model = FakeModel(lambda items: [reply(r["id"], tier=next(tiers)) for r in items])
    svc, repo = build(model)
    for n in range(5):
        repo.upsert(make_item(f"i{n}"))
    assert svc.classify_pending("me").alarm is False
