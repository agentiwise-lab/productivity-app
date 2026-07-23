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


@pytest.fixture(params=["memory", "supabase"])
def repo(request):
    if request.param == "memory":
        return InMemoryFeedRepository()
    return SupabaseFeedRepository(FakeSupabaseClient())


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
        "me", item.id, tier=Tier.URGENT, summary="Priya is blocked", reason="direct ask"
    )
    refetched = repo.upsert(make_item(content_hash="aaa", title="Add feature v2"))
    assert refetched.llm_tier is Tier.URGENT
    assert refetched.summary == "Priya is blocked"
    assert refetched.title == "Add feature v2"


def test_upsert_clears_the_classification_when_the_content_changed(repo):
    """A thread that gained replies is a different thing, so yesterday's
    summary no longer describes it."""
    item = repo.upsert(make_item(content_hash="aaa"))
    repo.apply_classification("me", item.id, tier=Tier.URGENT, summary="s", reason="r")
    refetched = repo.upsert(make_item(content_hash="bbb"))
    assert refetched.llm_tier is None
    assert refetched.summary is None


def test_apply_classification_records_that_the_model_set_the_tier(repo):
    item = repo.upsert(make_item())
    updated = repo.apply_classification(
        "me", item.id, tier=Tier.CAN_WAIT, summary="just an FYI", reason="no ask"
    )
    assert updated.llm_tier is Tier.CAN_WAIT
    assert updated.tier_source is TierSource.LLM
    assert updated.rule_tier is Tier.TODAY  # the rule verdict is not overwritten


def test_apply_classification_is_scoped_to_the_user(repo):
    item = repo.upsert(make_item(user_id="me"))
    assert (
        repo.apply_classification(
            "someone-else", item.id, tier=Tier.URGENT, summary="s", reason="r"
        )
        is None
    )
    assert repo.get("me", item.id).llm_tier is None


def test_pending_classification_returns_only_unclassified_items_that_need_it(repo):
    wanted = repo.upsert(make_item(source_ref="r#1", needs_llm=True, title="wanted"))
    repo.upsert(make_item(source_ref="r#2", needs_llm=False, title="rule only"))
    done = repo.upsert(make_item(source_ref="r#3", needs_llm=True, title="done"))
    repo.apply_classification("me", done.id, tier=Tier.NOISE, summary="s", reason="r")

    pending = repo.list_pending_classification("me")
    assert [item.id for item in pending] == [wanted.id]


def test_pending_classification_is_capped(repo):
    """The batch size is a cost ceiling (plan 4.2), so it must hold even when a
    backlog is much larger than one batch."""
    for n in range(30):
        repo.upsert(make_item(source_ref=f"r#{n}", needs_llm=True))
    assert len(repo.list_pending_classification("me", limit=20)) == 20


def test_list_by_user_drops_items_older_than_the_retention_window(repo):
    """Later holds 30 days, and nothing beyond it reaches a read."""
    repo.upsert(
        make_item(source_ref="r#1", title="old", occurred_at=NOW - timedelta(days=31))
    )
    repo.upsert(
        make_item(source_ref="r#2", title="new", occurred_at=NOW - timedelta(days=2))
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


def test_get_is_scoped_to_the_user(repo):
    item = repo.upsert(make_item(user_id="me"))
    assert repo.get("me", item.id) is not None
    assert repo.get("intruder", item.id) is None
