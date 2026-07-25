"""Turning a password into something safe to store, and checking it back.

Behind a two-method contract so the algorithm is swappable and so tests can use
a trivial fake instead of paying argon2's deliberate cost on every run. The real
implementation is argon2id (current OWASP first choice); the salt is per-hash and
internal, so two hashes of the same password differ and neither reveals it.
"""

from __future__ import annotations

from typing import Protocol

from argon2 import PasswordHasher as _Argon2
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError


class PasswordHasher(Protocol):
    def hash(self, plain: str) -> str:
        ...

    def verify(self, plain: str, hashed: str) -> bool:
        """True only if ``plain`` produced ``hashed``. Never raises on a wrong
        password: a mismatch is a return value, not an exception the caller has
        to remember to catch."""
        ...


class Argon2PasswordHasher:
    def __init__(self) -> None:
        self._hasher = _Argon2()

    def hash(self, plain: str) -> str:
        return self._hasher.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, plain)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False


class FakePasswordHasher:
    """Deterministic and fast, for tests. Keeps the real verify semantics (only
    the matching plaintext verifies) without argon2's per-call cost."""

    _PREFIX = "fake$"

    def hash(self, plain: str) -> str:
        return f"{self._PREFIX}{plain}"

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == f"{self._PREFIX}{plain}"
