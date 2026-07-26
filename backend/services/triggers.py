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
    # Linear is intentionally absent: every Linear trigger requires a team_id we
    # do not have at connect time, so Linear stays poll-only (backfill on
    # refresh) until team resolution is built.
}


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
        wanted = _TRIGGERS.get(source, [])
        if not wanted:
            return

        existing = self._existing_slugs(connected_account_id)
        for slug, config in wanted:
            if slug in existing:
                continue
            try:
                self._composio.triggers.create(
                    slug=slug,
                    user_id=user_id,
                    connected_account_id=connected_account_id,
                    trigger_config=config or None,
                )
            except Exception:
                # Best effort: one trigger failing must not abandon the rest or
                # the connect flow. The next reconcile retries, and create is an
                # upsert, so the retry cannot double up.
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
