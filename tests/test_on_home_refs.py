"""Contract for main._on_home_refs (the Later exclusion set).

Everything stored for the feed is on Home now — including noise-tier items, which
render at the bottom of To-dos — so all of it is excluded from Later. Later stays
the residual: the live provider set minus what the refresh already pulled in.
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


def test_everything_stored_is_excluded_from_later():
    repo = InMemoryFeedRepository()
    repo.upsert(_item("gmail:held"))  # llm_tier None -> still held
    repo.upsert(_item("gmail:noise", llm_tier=Tier.NOISE))  # shown at bottom of To-dos
    repo.upsert(_item("gmail:kept", llm_tier=Tier.TODAY))  # elevated to Home

    refs = _on_home_refs(repo, "me")

    # All three are on Home (noise renders at the bottom), so none double-shows
    # in Later; Later is the live provider residual minus these.
    assert refs == {"gmail:held", "gmail:noise", "gmail:kept"}
