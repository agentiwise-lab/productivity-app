"""A minimal in-process Redis stand-in: just the hash ops the feed store uses.

Avoids a fakeredis dependency. Supports the exact surface
``RedisFeedRepository`` touches: hset / hget / hgetall / hdel / expire / delete.
"""

from __future__ import annotations

from typing import Any


class FakeRedis:
    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, Any]] = {}

    def hset(self, key: str, field: str, value: Any) -> int:
        h = self._hashes.setdefault(key, {})
        is_new = field not in h
        h[field] = value
        return 1 if is_new else 0

    def hget(self, key: str, field: str) -> Any:
        return self._hashes.get(key, {}).get(field)

    def hgetall(self, key: str) -> dict[str, Any]:
        return dict(self._hashes.get(key, {}))

    def hdel(self, key: str, *fields: str) -> int:
        h = self._hashes.get(key, {})
        removed = 0
        for field in fields:
            if field in h:
                del h[field]
                removed += 1
        return removed

    def expire(self, key: str, ttl: int) -> bool:
        return key in self._hashes  # TTL is a no-op in the fake

    def delete(self, key: str) -> int:
        return 1 if self._hashes.pop(key, None) is not None else 0
