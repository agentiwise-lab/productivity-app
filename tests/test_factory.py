"""The integrations factory mints per-user services.

The whole point of the factory is that two users get two different bound
services, each carrying its own user_id into Composio. If it ever returned one
shared instance, every user would read and act as whoever built it, which is the
exact single-tenant bug the factory exists to remove.
"""

from __future__ import annotations

from backend.integrations.factory import ComposioIntegrations


class FakeComposio:
    pass


def test_each_user_gets_a_service_bound_to_their_own_id():
    factory = ComposioIntegrations(FakeComposio())
    a = factory.github("user-a")
    b = factory.github("user-b")
    assert a is not b
    assert a._user_id == "user-a"
    assert b._user_id == "user-b"


def test_the_same_user_and_toolkit_is_memoised():
    factory = ComposioIntegrations(FakeComposio())
    assert factory.gmail("user-a") is factory.gmail("user-a")


def test_different_toolkits_for_one_user_are_distinct():
    factory = ComposioIntegrations(FakeComposio())
    assert factory.github("user-a") is not factory.slack("user-a")
