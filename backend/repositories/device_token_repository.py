"""Where each of a user's devices can be reached.

Keyed on the Expo token rather than a surrogate id, for one reason that is
worth stating plainly: a token identifies a **device**, not a person, and the
same device can end up in somebody else's hands. Making it the primary key
means the account that owns it is a value to overwrite, not a row to duplicate,
so signing out and signing in as somebody else cannot leave two claims on the
same phone.

The contract carries no `get`: nothing needs one device, only the whole set for
a user at send time, and one token at deletion time.
"""

from __future__ import annotations

from typing import Protocol


class DeviceTokenRepository(Protocol):
    def upsert(self, user_id: str, token: str, platform: str) -> None:
        """Register a device, or move it to this user.

        Called on every app launch, because a token can rotate underneath us,
        so it must be idempotent rather than merely tolerable.
        """
        ...

    def delete(self, token: str) -> None:
        """Stop sending here. Called on sign-out, and when Expo reports the
        token as dead. Deleting one that is already gone is not an error:
        both callers race by nature."""
        ...

    def tokens_for(self, user_id: str) -> list[str]:
        ...


class InMemoryDeviceTokenRepository:
    """The test and local implementation."""

    def __init__(self) -> None:
        # token -> user_id. The direction matters: it is what makes a device
        # able to belong to exactly one user at a time, for free.
        self._owner: dict[str, str] = {}
        self._platform: dict[str, str] = {}

    def upsert(self, user_id: str, token: str, platform: str) -> None:
        self._owner[token] = user_id
        self._platform[token] = platform

    def delete(self, token: str) -> None:
        self._owner.pop(token, None)
        self._platform.pop(token, None)

    def tokens_for(self, user_id: str) -> list[str]:
        return [
            token for token, owner in self._owner.items() if owner == user_id
        ]
