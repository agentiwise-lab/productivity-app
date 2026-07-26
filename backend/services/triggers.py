"""Turning a linked account into a live feed source.

Linking an OAuth account tells Composio *who* the user is; it does not start any
polling. The trigger instance is the missing half: it is the thing that checks
GitHub every couple of minutes for a newly assigned issue and posts it to our
webhook. Without it the connect flow completed, the account showed as connected,
and the feed stayed empty forever, because nothing upstream was watching.

The slugs here are not free to choose. Each one must have a matching entry in
``ingest._MAPPERS``: a trigger we create but cannot map would deliver events that
are received, verified, and then silently dropped. The two lists are kept honest
by a test.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

from backend.models.sources import Source

log = logging.getLogger(__name__)

# Per-source trigger instances to create when the account first goes active.
# Each entry is (trigger_slug, trigger_config); an empty config takes the
# trigger's own defaults.
#
# GitHub provisions only the assigned-issue trigger. The repository-notification
# trigger needs a repo ``owner`` we do not have at connect time, so it is left
# out rather than created broken. The assigned-issue trigger already defaults to
# a two-minute poll; the config is spelled out so the cadence is not at the mercy
# of a changing upstream default (the earlier 60-minute setting is what made
# testing look dead).
_TRIGGERS: dict[Source, list[tuple[str, dict[str, Any]]]] = {
    Source.GITHUB: [
        ("GITHUB_ISSUE_ASSIGNED_TO_ME_TRIGGER", {"interval": 2, "state": "open"}),
    ],
    Source.SLACK: [
        ("SLACK_DIRECT_MESSAGE_RECEIVED", {}),
        ("SLACK_CHANNEL_MESSAGE_RECEIVED", {}),
    ],
    # Gmail and Calendar both take poll-type triggers that provision cleanly with
    # their own defaults (a two-minute poll). The Gmail message trigger also
    # carries Google Docs comment/mention/share notifications, since those are
    # delivered as email and Docs has no trigger of its own.
    Source.GMAIL: [
        ("GMAIL_NEW_GMAIL_MESSAGE", {}),
    ],
    Source.CALENDAR: [
        ("GOOGLECALENDAR_EVENT_STARTING_SOON_TRIGGER", {}),
    ],
    # Linear is handled dynamically (see _provision_linear): its triggers require
    # a team_id, resolved per-account at connect from LINEAR_LIST_LINEAR_TEAMS,
    # one trigger of each kind per team.
}

#: Linear trigger kinds, provisioned once per team the user belongs to. Both have
#: matching mappers in ``ingest._MAPPERS`` (issue-created and comment-received).
_LINEAR_TEAM_TRIGGERS = (
    "LINEAR_ISSUE_CREATED_TRIGGER",
    "LINEAR_COMMENT_EVENT_TRIGGER",
)
_LINEAR_VERSION = "20260721_00"


class TriggerProvisioner(Protocol):
    def provision(
        self, user_id: str, source: Source, connected_account_id: str
    ) -> None:
        ...


class DefaultTriggerProvisioner:
    """Creates a source's polling triggers the first time it goes active.

    Idempotent on two levels: a slug already active for the connected account is
    skipped, and ``triggers.create`` is itself an upsert keyed on
    (slug, connected account), so even a racing double-provision converges on one
    instance rather than two pollers. That matters because the connect flow
    reconciles on every poll, so this runs repeatedly for the same account.
    """

    def __init__(self, composio: Any) -> None:
        self._composio = composio

    def provision(
        self, user_id: str, source: Source, connected_account_id: str
    ) -> None:
        if source is Source.LINEAR:
            self._provision_linear(user_id, connected_account_id)
            return

        wanted = _TRIGGERS.get(source, [])
        if not wanted:
            return

        existing = self._existing_slugs(connected_account_id)
        for slug, config in wanted:
            if slug in existing:
                continue
            self._create(user_id, connected_account_id, slug, config or None)

    def _provision_linear(self, user_id: str, connected_account_id: str) -> None:
        """One issue-created + one comment trigger per team the user is in.

        Linear's triggers are team-scoped and require a ``team_id``, resolved here
        from ``LINEAR_LIST_LINEAR_TEAMS``. The mappers then filter team-wide events
        down to this user (their assigned issues, others' comments)."""
        teams = self._linear_team_ids(user_id)
        if not teams:
            log.warning("no Linear teams resolved; skipping trigger provisioning")
            return
        existing = self._existing_slugs(connected_account_id)
        for team_id in teams:
            for slug in _LINEAR_TEAM_TRIGGERS:
                # create is an upsert keyed on (slug, account, config); the
                # per-slug existing check is a coarse skip, safe to over-attempt.
                if slug in existing and len(teams) == 1:
                    continue
                self._create(
                    user_id, connected_account_id, slug, {"team_id": team_id}
                )

    def _linear_team_ids(self, user_id: str) -> list[str]:
        try:
            result = self._composio.tools.execute(
                "LINEAR_LIST_LINEAR_TEAMS",
                user_id=user_id,
                arguments={},
                version=_LINEAR_VERSION,
            )
            data = (
                result.get("data")
                if isinstance(result, dict)
                else getattr(result, "data", {})
            ) or {}
            teams = data.get("teams") or data.get("nodes") or []
            if isinstance(teams, dict):
                teams = teams.get("nodes") or []
            return [t["id"] for t in teams if isinstance(t, dict) and t.get("id")]
        except Exception:
            log.warning("could not list Linear teams", exc_info=True)
            return []

    def _create(
        self, user_id: str, connected_account_id: str, slug: str, config: dict | None
    ) -> None:
        try:
            self._composio.triggers.create(
                slug=slug,
                user_id=user_id,
                connected_account_id=connected_account_id,
                trigger_config=config,
            )
        except Exception:
            # Best effort: one trigger failing must not abandon the rest or the
            # connect flow. The next reconcile retries, and create is an upsert,
            # so the retry cannot double up.
            log.warning(
                "could not create trigger %s for %s",
                slug,
                connected_account_id,
                exc_info=True,
            )

    def _existing_slugs(self, connected_account_id: str) -> set[str]:
        """The trigger slugs already active for this account.

        A failed read returns an empty set rather than raising: better to attempt
        the create (an upsert, so it is safe) than to skip provisioning because we
        could not confirm the current state and leave the feed dead.
        """
        try:
            response = self._composio.triggers.list_active(
                connected_account_ids=[connected_account_id]
            )
        except Exception:
            log.warning("could not list active triggers", exc_info=True)
            return set()

        slugs: set[str] = set()
        for row in getattr(response, "items", response) or []:
            if isinstance(row, dict):
                name = row.get("trigger_name") or row.get("triggerName")
            else:
                name = getattr(row, "trigger_name", None)
            if name:
                slugs.add(str(name))
        return slugs
