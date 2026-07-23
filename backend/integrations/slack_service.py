"""Acting on Slack, through Composio.

Contract first: callers import ``SlackService`` and never this implementation.

Everything here is a write somebody else sees, so the parsing is strict. A
``source_ref`` that cannot be read raises instead of falling back to a default
channel, because the failure mode of guessing is a private reply posted
somewhere public.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel

from backend.integrations.slack import SLACK_TOOLKIT_VERSION
from backend.models.identity import Identity


class SlackMessageRef(BaseModel):
    channel: str
    ts: str


class SlackService(Protocol):
    def reply(
        self, source_ref: str, text: str, thread_ts: str | None = None
    ) -> SlackMessageRef:
        ...

    def mark_read(self, source_ref: str) -> None:
        ...

    def resolve_identity(self) -> Identity:
        ...


def parse_source_ref(source_ref: str) -> SlackMessageRef:
    """"slack:<channel>:<ts>" and nothing else."""
    parts = source_ref.split(":")
    if len(parts) != 3 or parts[0] != "slack" or not parts[1] or not parts[2]:
        raise ValueError(f"not a Slack source_ref: {source_ref!r}")
    return SlackMessageRef(channel=parts[1], ts=parts[2])


class ComposioSlackService:
    def __init__(
        self, composio: Any, user_id: str, version: str = SLACK_TOOLKIT_VERSION
    ) -> None:
        self._composio = composio
        self._user_id = user_id
        self._version = version

    @staticmethod
    def _data(result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result.get("data") or {}
        return getattr(result, "data", {}) or {}

    def _execute(self, slug: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._data(
            self._composio.tools.execute(
                slug,
                user_id=self._user_id,
                arguments=arguments,
                version=self._version,
            )
        )

    def reply(
        self, source_ref: str, text: str, thread_ts: str | None = None
    ) -> SlackMessageRef:
        ref = parse_source_ref(source_ref)
        arguments: dict[str, Any] = {"channel": ref.channel, "text": text}
        if thread_ts:
            # Without this the reply lands in the channel rather than the
            # thread, in front of everyone rather than the people talking.
            arguments["thread_ts"] = thread_ts

        data = self._execute("SLACK_SEND_MESSAGE", arguments)
        return SlackMessageRef(channel=ref.channel, ts=str(data.get("ts") or ""))

    def mark_read(self, source_ref: str) -> None:
        ref = parse_source_ref(source_ref)
        self._execute(
            "SLACK_SET_READ_CURSOR_IN_A_CONVERSATION",
            {"channel": ref.channel, "ts": ref.ts},
        )

    def resolve_identity(self) -> Identity:
        """Section 3.10: mention detection is impossible without this, and it
        is resolved once at connection time rather than per message."""
        data = self._execute("SLACK_TEST_AUTH", {})
        return Identity(slack_user_id=data.get("user_id") or data.get("user_id_str"))
