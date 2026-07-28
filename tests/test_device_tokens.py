"""Where a phone says "send here".

One row per device, keyed on the token rather than on a surrogate id, because
a token is globally unique and a device can move between accounts. That last
part is the reason most of these tests exist: getting the move wrong does not
produce a missing notification, it produces one person's work arriving on
another person's phone.
"""

from __future__ import annotations

from backend.repositories.device_token_repository import (
    InMemoryDeviceTokenRepository,
)

PHONE = "ExponentPushToken[aaaaaaaaaaaaaaaaaaaaaa]"
TABLET = "ExponentPushToken[bbbbbbbbbbbbbbbbbbbbbb]"
ALICE = "11111111-1111-1111-1111-111111111111"
BOB = "22222222-2222-2222-2222-222222222222"


def test_a_registered_token_comes_back_for_its_user():
    repo = InMemoryDeviceTokenRepository()
    repo.upsert(ALICE, PHONE, "android")
    assert repo.tokens_for(ALICE) == [PHONE]


def test_a_user_with_no_devices_has_no_tokens():
    assert InMemoryDeviceTokenRepository().tokens_for(ALICE) == []


def test_registering_the_same_token_twice_stores_one_row():
    """The app re-registers on every launch, because a token can rotate. That
    makes this the most-called write in the feature and it has to be idempotent
    or a daily user accrues a row a day and gets duplicate buzzes."""
    repo = InMemoryDeviceTokenRepository()
    repo.upsert(ALICE, PHONE, "android")
    repo.upsert(ALICE, PHONE, "android")
    assert repo.tokens_for(ALICE) == [PHONE]


def test_one_user_can_have_several_devices():
    repo = InMemoryDeviceTokenRepository()
    repo.upsert(ALICE, PHONE, "android")
    repo.upsert(ALICE, TABLET, "ios")
    assert sorted(repo.tokens_for(ALICE)) == sorted([PHONE, TABLET])


def test_a_device_that_changes_hands_moves_rather_than_duplicating():
    """Alice signs out on this phone and Bob signs in. If the row kept Alice's
    user_id, Bob's phone would keep buzzing with Alice's work. This is the one
    case here that is a privacy bug rather than a papercut."""
    repo = InMemoryDeviceTokenRepository()
    repo.upsert(ALICE, PHONE, "android")

    repo.upsert(BOB, PHONE, "android")

    assert repo.tokens_for(ALICE) == []
    assert repo.tokens_for(BOB) == [PHONE]


def test_delete_removes_only_that_token():
    repo = InMemoryDeviceTokenRepository()
    repo.upsert(ALICE, PHONE, "android")
    repo.upsert(ALICE, TABLET, "ios")

    repo.delete(PHONE)

    assert repo.tokens_for(ALICE) == [TABLET]


def test_deleting_a_token_that_was_never_there_is_not_an_error():
    """Called from two places that cannot know the state: sign-out, and the
    sweep that reacts to Expo reporting a dead device. Both may race."""
    InMemoryDeviceTokenRepository().delete(PHONE)


def test_tokens_are_scoped_to_their_user():
    repo = InMemoryDeviceTokenRepository()
    repo.upsert(ALICE, PHONE, "android")
    repo.upsert(BOB, TABLET, "ios")
    assert repo.tokens_for(ALICE) == [PHONE]
    assert repo.tokens_for(BOB) == [TABLET]
