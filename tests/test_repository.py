"""Repository contract tests.

Every case runs against both implementations. They are written against the
contract, never against the dict or the table behind it, so this file is the
single specification the in-memory store and the Supabase store both answer to.
That is the point: the two must not be allowed to drift, because the tests would
then be passing on one thing while production runs the other.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.models.feed import FeedItem, FeedStatus, TierSource
from backend.models.tiers import Tier, TypeTag
from backend.repositories.feed_repository import InMemoryFeedRepository
from backend.repositories.supabase_feed_repository import SupabaseFeedRepository
from backend.repositories.supabase_client import SupabaseClientProvider
from tests.fake_supabase import FakeSupabaseClient

NOW = datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc)


def make_item(item_id="i1", user_id="me", source_ref="octo/repo#1", **overrides):
    defaults = dict(
        id=item_id,
        user_id=user_id,
        source_ref=source_ref,
        rule_tier=Tier.TODAY,
        type_tag=TypeTag.ASSIGNED,
        title="Add feature",
        url="https://github.com/octo/repo/pull/1",
        created_at=NOW,
        occurred_at=NOW,
    )
    defaults.update(overrides)
    return FeedItem(**defaults)


@pytest.fixture(params=["memory", "supabase", "redis"])
def repo(request):
    if request.param == "memory":
        return InMemoryFeedRepository()
    if request.param == "redis":
        from backend.repositories.feed_actions import InMemoryFeedActionsRepository
        from backend.repositories.redis_feed_repository import RedisFeedRepository
        from tests.fake_redis import FakeRedis

        return RedisFeedRepository(FakeRedis(), InMemoryFeedActionsRepository())
    fake = FakeSupabaseClient()
    return SupabaseFeedRepository(SupabaseClientProvider(lambda: fake))


def test_upsert_dedupes_on_user_and_source_ref(repo):
    first = repo.upsert(make_item())
    second = repo.upsert(make_item(title="Renamed"))
    assert second.id == first.id  # identity of the existing row is preserved
    assert second.title == "Renamed"
    assert len(repo.list_by_user("me", now=NOW)) == 1


def test_the_same_source_ref_for_two_users_is_two_rows(repo):
    """Dedupe is per user. Two people can both be asked to review one PR."""
    repo.upsert(make_item(user_id="me"))
    repo.upsert(make_item(user_id="you"))
    assert len(repo.list_by_user("me", now=NOW)) == 1
    assert len(repo.list_by_user("you", now=NOW)) == 1


def test_upsert_preserves_a_classification_already_applied(repo):
    """A refetch of the same notification must not wipe the model's verdict and
    silently send the item back through the classifier."""
    item = repo.upsert(make_item(content_hash="aaa"))
    repo.apply_classification(
        "me", item.id, tier=Tier.URGENT, summary="Priya is blocked",
        reason="direct ask", at=NOW,
    )
    refetched = repo.upsert(make_item(content_hash="aaa", title="Add feature v2"))
    assert refetched.llm_tier is Tier.URGENT
    assert refetched.summary == "Priya is blocked"
    assert refetched.title == "Add feature v2"


def test_upsert_clears_the_classification_when_the_content_changed(repo):
    """A thread that gained replies is a different thing, so yesterday's
    summary no longer describes it."""
    item = repo.upsert(make_item(content_hash="aaa"))
    repo.apply_classification(
        "me", item.id, tier=Tier.URGENT, summary="s", reason="r", at=NOW
    )
    refetched = repo.upsert(make_item(content_hash="bbb"))
    assert refetched.llm_tier is None
    assert refetched.summary is None


def test_apply_classification_records_that_the_model_set_the_tier(repo):
    item = repo.upsert(make_item())
    updated = repo.apply_classification(
        "me", item.id, tier=Tier.CAN_WAIT, summary="just an FYI", reason="no ask",
        at=NOW,
    )
    assert updated.llm_tier is Tier.CAN_WAIT
    assert updated.tier_source is TierSource.LLM
    assert updated.llm_attempted_at == NOW  # the attempt is stamped
    assert updated.rule_tier is Tier.TODAY  # the rule verdict is not overwritten


def test_apply_classification_is_scoped_to_the_user(repo):
    item = repo.upsert(make_item(user_id="me"))
    assert (
        repo.apply_classification(
            "someone-else", item.id, tier=Tier.URGENT, summary="s", reason="r", at=NOW
        )
        is None
    )
    assert repo.get("me", item.id).llm_tier is None


def test_pending_classification_returns_only_unclassified_items_that_need_it(repo):
    wanted = repo.upsert(make_item(source_ref="r#1", needs_llm=True, title="wanted"))
    repo.upsert(make_item(source_ref="r#2", needs_llm=False, title="rule only"))
    done = repo.upsert(make_item(source_ref="r#3", needs_llm=True, title="done"))
    repo.apply_classification(
        "me", done.id, tier=Tier.NOISE, summary="s", reason="r", at=NOW
    )

    pending = repo.list_pending_classification("me")
    assert [item.id for item in pending] == [wanted.id]


def test_pending_classification_is_capped(repo):
    """The batch size is a cost ceiling (plan 4.2), so it must hold even when a
    backlog is much larger than one batch."""
    for n in range(30):
        repo.upsert(make_item(source_ref=f"r#{n}", needs_llm=True))
    assert len(repo.list_pending_classification("me", limit=20)) == 20


def test_list_by_user_drops_items_older_than_the_retention_window(repo):
    """Later holds 30 days, and nothing beyond it reaches a read.

    Tagged REPLY rather than the fixture's default ASSIGNED: assigned work is
    an obligation and deliberately never ages out, so it cannot demonstrate
    the window. A month-old mention genuinely is stale.
    """
    repo.upsert(
        make_item(
            source_ref="r#1", title="old", type_tag=TypeTag.REPLY,
            occurred_at=NOW - timedelta(days=31),
        )
    )
    repo.upsert(
        make_item(
            source_ref="r#2", title="new", type_tag=TypeTag.REPLY,
            occurred_at=NOW - timedelta(days=2),
        )
    )
    assert [i.title for i in repo.list_by_user("me", now=NOW)] == ["new"]


def test_list_by_user_excludes_handled_items(repo):
    """Acting on something removes it immediately (3.11)."""
    done = repo.upsert(make_item(source_ref="r#1", title="done"))
    repo.mark_handled("me", done.id, status=FeedStatus.ACTED, at=NOW)
    repo.upsert(make_item(source_ref="r#2", title="open"))
    assert [i.title for i in repo.list_by_user("me", now=NOW)] == ["open"]


def test_a_refetch_never_resurrects_an_item_the_user_already_handled(repo):
    """GitHub keeps returning a notification until it is marked read upstream,
    so ingest runs again over rows the user has already dealt with. If upsert
    wrote the source's state, replied-to items would reappear."""
    item = repo.upsert(make_item())
    repo.mark_handled("me", item.id, status=FeedStatus.ACTED, at=NOW)
    repo.upsert(make_item(title="Add feature"))
    assert repo.list_by_user("me", now=NOW) == []


def test_mark_handled_is_scoped_to_the_user(repo):
    item = repo.upsert(make_item(user_id="me"))
    assert (
        repo.mark_handled("intruder", item.id, status=FeedStatus.ACTED, at=NOW) is None
    )
    assert repo.get("me", item.id).status is FeedStatus.UNREAD


def test_snooze_hides_an_item_without_marking_it_done(repo):
    """Snooze and dismiss must not collapse into each other: a snoozed item has
    to come back, and Later has to keep showing it meanwhile."""
    item = repo.upsert(make_item())
    later = NOW + timedelta(hours=3)

    snoozed = repo.snooze("me", item.id, later)

    assert snoozed.status is FeedStatus.SNOOZED
    assert snoozed.handled_at is None
    assert [row.id for row in repo.list_by_user("me", now=NOW)] == [item.id]


def test_snooze_is_scoped_to_the_user(repo):
    item = repo.upsert(make_item(user_id="me"))
    assert repo.snooze("intruder", item.id, NOW + timedelta(hours=1)) is None


def test_get_is_scoped_to_the_user(repo):
    item = repo.upsert(make_item(user_id="me"))
    assert repo.get("me", item.id) is not None
    assert repo.get("intruder", item.id) is None


def test_mark_attempted_makes_a_failed_item_distinct_from_a_held_one(repo):
    """A held item and a failed one both lack an ``llm_tier``; only the attempt
    marker separates them, and it is what lets the feed show the failed one at
    its ceiling rather than hiding it with the still-pending ones."""
    item = repo.upsert(make_item(needs_llm=True))
    assert repo.get("me", item.id).llm_attempted_at is None  # held

    repo.mark_attempted("me", [item.id], at=NOW)

    got = repo.get("me", item.id)
    assert got.llm_tier is None
    assert got.llm_attempted_at == NOW  # failed, not held


def test_mark_attempted_never_clobbers_a_verdict_that_landed(repo):
    """The bulk mark runs after a failed batch, but a verdict may have landed on
    one of its items in between; the ``llm_tier is null`` guard protects it."""
    item = repo.upsert(make_item(needs_llm=True, content_hash="h"))
    repo.apply_classification(
        "me", item.id, tier=Tier.URGENT, summary="s", reason="r", at=NOW
    )
    repo.mark_attempted("me", [item.id], at=NOW + timedelta(hours=1))
    assert repo.get("me", item.id).llm_tier is Tier.URGENT


def test_content_change_keeps_a_classified_card_visible(repo):
    """H1: when a classified item's content changes it is re-queued, but its
    attempt marker survives so it stays visible (at the ceiling) instead of
    dropping back into the hidden held state mid-session."""
    item = repo.upsert(make_item(needs_llm=True, content_hash="aaa"))
    repo.apply_classification(
        "me", item.id, tier=Tier.CAN_WAIT, summary="s", reason="r", at=NOW
    )
    refetched = repo.upsert(make_item(needs_llm=True, content_hash="bbb"))
    assert refetched.llm_tier is None  # the stale verdict is dropped
    assert refetched.llm_attempted_at == NOW  # but it is not held -> still shown


def test_the_db_backed_cache_reads_a_verdict_off_an_existing_row():
    """H4: the classification cache is the feed table itself, so it survives a
    restart and is shared across workers. A row already classified for one item
    answers the cache for another item with the same content hash."""
    from backend.repositories.supabase_feed_repository import (
        SupabaseClassificationCache,
    )

    client = FakeSupabaseClient()
    provider = SupabaseClientProvider(lambda: client)
    repo = SupabaseFeedRepository(provider)
    item = repo.upsert(make_item(content_hash="shared", needs_llm=True))
    repo.apply_classification(
        "me", item.id, tier=Tier.URGENT, summary="blocked", reason="direct ask", at=NOW
    )

    cache = SupabaseClassificationCache(provider)
    assert cache.get("shared") == (Tier.URGENT, "blocked", "direct ask")
    assert cache.get("never-seen") is None


def test_an_overdue_item_is_not_aged_out_of_the_feed():
    """Retention drops stale *events*. An open item whose deadline has passed
    is not a stale event, it is an obligation: the user's June Linear issues
    were overdue and invisible at the same time, which is the worst pair.
    """
    from datetime import datetime, timedelta, timezone

    from backend.models.feed import FeedItem
    from backend.models.tiers import Tier, TypeTag
    from backend.repositories.feed_repository import InMemoryFeedRepository

    now = datetime(2026, 7, 24, tzinfo=timezone.utc)
    long_ago = now - timedelta(days=45)

    repo = InMemoryFeedRepository()
    repo.upsert(
        FeedItem(
            id="overdue", user_id="u", source="linear", source_ref="linear:AGE-52",
            rule_tier=Tier.TODAY, type_tag=TypeTag.ASSIGNED, title="Admin dashboard", url="",
            occurred_at=long_ago, created_at=long_ago,
            deadline=now - timedelta(days=30),
        )
    )
    repo.upsert(
        FeedItem(
            id="stale", user_id="u", source="gmail", source_ref="gmail:1",
            rule_tier=Tier.NOISE, type_tag=TypeTag.FYI, title="Old newsletter", url="",
            occurred_at=long_ago, created_at=long_ago,
        )
    )

    kept = {item.id for item in repo.list_by_user("u", now=now)}
    assert "overdue" in kept
    assert "stale" not in kept


def test_assigned_work_never_ages_out_even_with_no_deadline():
    """An open issue assigned to you is a standing obligation, not an event
    that gets old. Six of the user's Linear issues were invisible purely
    because nobody had edited them in a month, including one at Urgent
    priority and five backlog items that left the Later tab empty."""
    from datetime import datetime, timedelta, timezone

    from backend.models.feed import FeedItem
    from backend.models.tiers import Tier, TypeTag
    from backend.repositories.feed_repository import InMemoryFeedRepository

    now = datetime(2026, 7, 24, tzinfo=timezone.utc)
    june = now - timedelta(days=46)

    repo = InMemoryFeedRepository()
    repo.upsert(
        FeedItem(
            id="assigned", user_id="u", source="linear", source_ref="linear:AGE-25",
            rule_tier=Tier.URGENT, type_tag=TypeTag.ASSIGNED, title="Test suite",
            url="", occurred_at=june, created_at=june,
        )
    )
    repo.upsert(
        FeedItem(
            id="backlog", user_id="u", source="linear", source_ref="linear:AGE-21",
            rule_tier=Tier.NOISE, type_tag=TypeTag.ASSIGNED, title="Summary card",
            url="", occurred_at=june, created_at=june,
        )
    )
    repo.upsert(
        FeedItem(
            id="old_mention", user_id="u", source="slack", source_ref="slack:C1:1",
            rule_tier=Tier.CAN_WAIT, type_tag=TypeTag.REPLY, title="old chatter",
            url="", occurred_at=june, created_at=june,
        )
    )

    kept = {item.id for item in repo.list_by_user("u", now=now)}
    assert "assigned" in kept, "an urgent assigned issue must not age out"
    assert "backlog" in kept, "backlog work belongs in Later, not nowhere"
    assert "old_mention" not in kept, "a month-old Slack line is genuinely stale"


# --- Redis serializer round-trip (data-integrity fix #5) -------------------


def test_redis_row_roundtrips_every_ranking_field():
    """The Redis row is the FeedItem minus exactly the three ledger-owned fields.
    Everything that drives ranking, the model's sent_at, and dedupe must survive
    serialize -> deserialize, so a dropped field fails here, not in production."""
    from backend.repositories.redis_feed_repository import RedisFeedRepository

    item = make_item(
        is_blocking=True,
        content_hash="abc123",
        deadline=NOW + timedelta(hours=3),
        occurred_at=NOW - timedelta(minutes=5),
        created_at=NOW - timedelta(minutes=10),
        llm_tier=Tier.URGENT,
        summary="s",
        reason="r",
        signal="assign",
        needs_llm=True,
        body="the full body",
    )
    restored = RedisFeedRepository._deserialize(RedisFeedRepository._serialize(item))

    for field in (
        "is_blocking", "content_hash", "deadline", "occurred_at", "created_at",
        "llm_tier", "summary", "reason", "signal", "needs_llm", "body",
        "source_ref", "rule_tier", "type_tag", "id", "user_id",
    ):
        assert getattr(restored, field) == getattr(item, field), field
    # The three ledger-owned fields are intentionally not stored: they default.
    assert restored.status is FeedStatus.UNREAD
    assert restored.snoozed_until is None
    assert restored.handled_at is None
