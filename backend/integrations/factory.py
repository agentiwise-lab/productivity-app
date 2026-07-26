"""Per-user integration services, minted on demand.

Each integration service (`ComposioGitHubService` and its siblings) already
encapsulates "who am I acting as" cleanly: it holds a Composio client and one
``user_id``. The only thing wrong with the old wiring was that the app built one
of each, bound to a single shared id. This factory keeps the services exactly as
they are and moves the binding to call time: an orchestrator that already knows
whose refresh it is asks the factory for that user's GitHub, that user's Gmail,
and so on.

Instances are memoised per ``(toolkit, user_id)`` so the in-instance caches the
services keep (Slack's channel-name map, Linear's "who am I", Calendar's own
email) survive across calls within a process, rather than being thrown away and
rebuilt on every refresh.
"""

from __future__ import annotations

from typing import Any, Protocol

from backend.integrations.calendar import ComposioCalendarService
from backend.integrations.composio_github import ComposioGitHubService
from backend.integrations.gmail import ComposioGmailService
from backend.integrations.google_docs import ComposioGoogleDocsService
from backend.integrations.linear import ComposioLinearService
from backend.integrations.slack_service import ComposioSlackService


class Integrations(Protocol):
    """The seam. Callers depend on this, not on how a service is constructed."""

    def github(self, user_id: str) -> Any:
        ...

    def slack(self, user_id: str) -> Any:
        ...

    def linear(self, user_id: str) -> Any:
        ...

    def gmail(self, user_id: str) -> Any:
        ...

    def calendar(self, user_id: str) -> Any:
        ...

    def google_docs(self, user_id: str) -> Any:
        ...


class ComposioIntegrations:
    def __init__(self, composio: Any) -> None:
        self._composio = composio
        self._cache: dict[tuple[str, str], Any] = {}

    def github(self, user_id: str) -> Any:
        return self._get("github", user_id, ComposioGitHubService)

    def slack(self, user_id: str) -> Any:
        return self._get("slack", user_id, ComposioSlackService)

    def linear(self, user_id: str) -> Any:
        return self._get("linear", user_id, ComposioLinearService)

    def gmail(self, user_id: str) -> Any:
        return self._get("gmail", user_id, ComposioGmailService)

    def calendar(self, user_id: str) -> Any:
        return self._get("calendar", user_id, ComposioCalendarService)

    def google_docs(self, user_id: str) -> Any:
        return self._get("google_docs", user_id, ComposioGoogleDocsService)

    def _get(self, toolkit: str, user_id: str, cls: Any) -> Any:
        key = (toolkit, user_id)
        if key not in self._cache:
            self._cache[key] = cls(self._composio, user_id=user_id)
        return self._cache[key]
