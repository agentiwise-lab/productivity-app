"""Calendar service internals that must self-heal.

Scoped to ``_email`` resolution: it is cached, and caching an empty result (the
account not yet readable at the moment of the first call) froze an empty address
for the life of the process, which then answered RSVPs for nobody.
"""

from __future__ import annotations

from backend.integrations.calendar import ComposioCalendarService


class _FlakyTools:
    def __init__(self) -> None:
        self._attempts = 0

    def execute(self, slug, user_id=None, arguments=None, version=None):
        if slug == "GOOGLECALENDAR_GET_CALENDAR":
            self._attempts += 1
            if self._attempts == 1:
                return {"data": {}}  # not yet readable → empty id
            return {"data": {"id": "me@example.com"}}
        return {"data": {}}


class _Composio:
    def __init__(self) -> None:
        self.tools = _FlakyTools()


def test_own_email_is_not_cached_until_it_resolves():
    svc = ComposioCalendarService(_Composio(), user_id="u")
    assert svc._email == ""                 # empty result, not cached
    assert svc._email == "me@example.com"   # next call retries, resolves


def test_a_supplied_email_is_used_without_a_lookup():
    svc = ComposioCalendarService(_Composio(), user_id="u", email="given@example.com")
    assert svc._email == "given@example.com"
