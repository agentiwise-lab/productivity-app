"""Contract for main._on_home_refs (the Later exclusion set).

Held items stay excluded from Later (they must not flicker in mid-classification);
an item the model settled as noise is dropped from the exclusion set so it
surfaces in Later's live view (bible 7.1).
"""

from __future__ import annotations

from datetime import datetime, timezone

from backend.main import _on_home_refs
from backend.models.feed import FeedItem
from backend.models.tiers import Tier, TypeTag
from backend.repositories.feed_repository import InMemoryFeedRepository

NOW = datetime(2026, 7, 26, 12, 0, tzinfo=timezone.utc)


def _item(source_ref: str, **overrides) -> FeedItem:
    defaults = dict(
        id=source_ref,
        user_id="me",
        source="gmail",
        source_ref=source_ref,
        type_tag=TypeTag.REPLY,
        rule_tier=Tier.NOISE,
        needs_llm=True,
        signal="gmail_message",
        title="hi",
        url="",
        occurred_at=NOW,
    )
    defaults.update(overrides)
    return FeedItem(**defaults)


def test_model_noise_is_excluded_so_later_can_show_it():
    repo = InMemoryFeedRepository()
    repo.upsert(_item("gmail:held"))  # llm_tier None -> still held
    repo.upsert(_item("gmail:noise", llm_tier=Tier.NOISE))  # model said noise
    repo.upsert(_item("gmail:kept", llm_tier=Tier.TODAY))  # elevated to Home

    refs = _on_home_refs(repo, "me")

    assert "gmail:noise" not in refs  # surfaces in Later
    assert "gmail:held" in refs  # excluded from Later while pending
    assert "gmail:kept" in refs  # on Home, excluded from Later
