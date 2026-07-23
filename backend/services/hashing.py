"""Content fingerprint for the classification cache.

Keyed on what the model actually reads, not on the item's reference. A Slack
thread keeps one ``source_ref`` while its content changes under it, so keying
the cache on the reference would serve a stale verdict forever.
"""

from __future__ import annotations

from hashlib import sha256

from backend.models.events import RawEvent


def content_hash(event: RawEvent) -> str:
    parts = [
        event.source,
        event.source_ref,
        event.reason,
        event.title,
        event.body or "",
        ",".join(sorted(event.labels)),
    ]
    return sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
