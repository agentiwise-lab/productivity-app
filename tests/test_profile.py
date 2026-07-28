"""The profile service: read and set the user's display name.

The name is optional and lives beside the credentials, but it is deliberately
not the auth service's job: signing in and being called something are different
concerns. These tests pin the small contract the You tab and the greeting read
through.
"""

from __future__ import annotations

import pytest

from backend.repositories.credentials_repository import InMemoryCredentialsRepository
from backend.services.notifications import NotifyLevel
from backend.services.profile import DefaultProfileService, UserNotFound


def make():
    repo = InMemoryCredentialsRepository()
    user = repo.create_user("vicky@agentiwise.com", "hash")
    return DefaultProfileService(repo), repo, user.id


def test_get_returns_email_and_a_null_name_before_one_is_set():
    service, _, user_id = make()
    profile = service.get(user_id)
    assert profile.email == "vicky@agentiwise.com"
    assert profile.name is None


def test_set_name_persists_and_is_returned():
    service, repo, user_id = make()
    profile = service.set_name(user_id, "Vicky")
    assert profile.name == "Vicky"
    # And it is durable: a fresh read sees it.
    assert service.get(user_id).name == "Vicky"
    assert repo.get_user_by_id(user_id).name == "Vicky"


def test_set_name_trims_surrounding_whitespace():
    service, _, user_id = make()
    assert service.set_name(user_id, "  Vicky  ").name == "Vicky"


def test_a_blank_name_clears_it_back_to_no_name():
    service, _, user_id = make()
    service.set_name(user_id, "Vicky")
    assert service.set_name(user_id, "   ").name is None
    assert service.set_name(user_id, None).name is None


def test_an_over_long_name_is_truncated_not_rejected():
    service, _, user_id = make()
    profile = service.set_name(user_id, "x" * 200)
    assert len(profile.name) == 80


def test_get_for_an_unknown_user_raises():
    service, _, _ = make()
    with pytest.raises(UserNotFound):
        service.get("00000000-0000-0000-0000-000000000000")


# --- notify level ----------------------------------------------------------
#
# The You tab's "Notify me" control. It lived as a `useState` in the app until
# now, which meant it reset on every launch and drove nothing; these pin the
# other half of making it real.


def test_notify_level_defaults_to_urgent():
    """A new account is opted in at the narrowest setting. Off by default would
    make the feature invisible; anything wider would buzz about things the user
    never asked to be buzzed about."""
    service, _, user_id = make()
    assert service.get(user_id).notify_level == NotifyLevel.URGENT


def test_set_notify_level_persists_and_is_returned():
    service, repo, user_id = make()
    profile = service.set_notify_level(user_id, NotifyLevel.URGENT_TODAY)
    assert profile.notify_level == NotifyLevel.URGENT_TODAY
    assert service.get(user_id).notify_level == NotifyLevel.URGENT_TODAY
    assert repo.get_user_by_id(user_id).notify_level == "urgent_today"


def test_setting_the_notify_level_leaves_the_name_alone():
    """Both live on the users row and both are written through PATCH /me, so
    the one thing worth pinning is that neither erases the other."""
    service, _, user_id = make()
    service.set_name(user_id, "Vicky")
    service.set_notify_level(user_id, NotifyLevel.OFF)
    assert service.get(user_id).name == "Vicky"
    service.set_name(user_id, "Vicky P")
    assert service.get(user_id).notify_level == NotifyLevel.OFF


def test_an_unknown_notify_level_is_rejected():
    """The column carries a check constraint, so a bad value would fail at the
    database with a 500. Refusing it in the service turns that into a 422."""
    service, _, user_id = make()
    with pytest.raises(ValueError):
        service.set_notify_level(user_id, "sometimes")


def test_set_notify_level_for_an_unknown_user_raises():
    service, _, _ = make()
    with pytest.raises(UserNotFound):
        service.set_notify_level(
            "00000000-0000-0000-0000-000000000000", NotifyLevel.OFF
        )
