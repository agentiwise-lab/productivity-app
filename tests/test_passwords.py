"""Password hasher contract.

Run against both the real argon2 hasher and the fake, so the fake the rest of
the suite relies on cannot drift from the real behaviour it stands in for.
"""

from __future__ import annotations

import pytest

from backend.services.passwords import Argon2PasswordHasher, FakePasswordHasher


@pytest.fixture(params=["argon2", "fake"])
def hasher(request):
    return Argon2PasswordHasher() if request.param == "argon2" else FakePasswordHasher()


def test_hash_is_not_the_plaintext(hasher):
    assert hasher.hash("hunter2") != "hunter2"


def test_verify_true_on_match(hasher):
    hashed = hasher.hash("correct horse battery staple")
    assert hasher.verify("correct horse battery staple", hashed) is True


def test_verify_false_on_mismatch(hasher):
    hashed = hasher.hash("hunter2")
    assert hasher.verify("hunter3", hashed) is False


def test_verify_false_on_garbage_hash(hasher):
    assert hasher.verify("hunter2", "not-a-real-hash") is False


def test_argon2_salts_each_hash():
    hasher = Argon2PasswordHasher()
    assert hasher.hash("same") != hasher.hash("same")
    # ...but both still verify.
    assert hasher.verify("same", hasher.hash("same"))
