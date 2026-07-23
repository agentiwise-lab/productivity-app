"""Who the user is on each connected platform.

Plan 3.10 says resolve this once at connection time. The gap this file closes is
that the contract existed and production wired a null implementation, so
``identity.slack_user_id`` was always None. Mention detection then dropped every
channel message, silently: the events arrived, verified, returned 200, and
produced nothing. Found by sending a real message, not by reading the code.

Resolution is lazy and cached because it is two extra API calls per user per
process, and identities do not change.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.models.identity import Identity

log = logging.getLogger(__name__)


class InMemoryConnectionRepository:
    """Resolves identity through Composio and remembers it.

    A failed lookup is cached as an empty Identity rather than retried on every
    webhook: a workspace we cannot introspect will not start working because we
    asked sixty times a minute.
    """

    def __init__(
        self,
        composio: Any | None = None,
        composio_user_id: str | None = None,
        github_version: str = "20260721_00",
        slack_version: str = "20260721_00",
    ) -> None:
        self._composio = composio
        self._composio_user_id = composio_user_id
        self._github_version = github_version
        self._slack_version = slack_version
        self._identities: dict[tuple[str, str], Identity] = {}
        self._statuses: dict[tuple[str, str], str] = {}

    def mark_status(self, user_id: str, provider: str, status: str) -> None:
        self._statuses[(user_id, provider)] = status
        if status != "active":
            log.warning("connection %s/%s is %s", user_id, provider, status)

    def status_of(self, user_id: str, provider: str) -> str:
        return self._statuses.get((user_id, provider), "active")

    def identity_for(self, user_id: str, provider: str) -> Identity:
        key = (user_id, provider)
        if key in self._identities:
            return self._identities[key]

        identity = self._resolve(provider)
        self._identities[key] = identity
        return identity

    def _resolve(self, provider: str) -> Identity:
        if self._composio is None or self._composio_user_id is None:
            return Identity()
        try:
            if provider == "slack":
                return self._resolve_slack()
            if provider == "github":
                return self._resolve_github()
        except Exception:
            log.warning("could not resolve %s identity", provider, exc_info=True)
        return Identity()

    def _execute(self, slug: str, arguments: dict, version: str) -> dict:
        result = self._composio.tools.execute(
            slug,
            user_id=self._composio_user_id,
            arguments=arguments,
            version=version,
        )
        if isinstance(result, dict):
            return result.get("data") or {}
        return getattr(result, "data", {}) or {}

    def _resolve_slack(self) -> Identity:
        auth = self._execute("SLACK_TEST_AUTH", {}, self._slack_version)
        user_id = auth.get("user_id") or auth.get("user_id_str")
        if not user_id:
            return Identity()

        # The self-DM channel, so a note to yourself can be told apart from a
        # reply you sent in somebody else's conversation.
        dm_channel = None
        try:
            opened = self._execute(
                "SLACK_OPEN_DM", {"users": user_id}, self._slack_version
            )
            dm_channel = (opened.get("channel") or {}).get("id")
        except Exception:
            log.info("could not resolve the self-DM channel", exc_info=True)

        return Identity(slack_user_id=user_id, slack_dm_channel=dm_channel)

    def _resolve_github(self) -> Identity:
        me = self._execute(
            "GITHUB_GET_THE_AUTHENTICATED_USER", {}, self._github_version
        )
        return Identity(github_login=me.get("login"))
