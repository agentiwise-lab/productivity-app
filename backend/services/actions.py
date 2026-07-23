"""Acting on a feed item. Phase 3.

Every method here causes something other people can see. That shapes two rules
the whole file follows:

**Upstream first, local state second.** The item is only marked handled after
the send succeeded. Reversing that order means an item disappears from the feed
while the person who asked is still waiting, which is worse than not having the
feature.

**One action per item, ever.** The app is optimistic and networks are flaky, so
a retry is the normal case, not the exception. Acting on an already-handled item
raises instead of sending a second copy into somebody's channel.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable, Protocol

from backend.integrations.github import GitHubService, PRRef
from backend.integrations.slack_service import SlackService
from backend.models.feed import FeedItem, FeedStatus
from backend.repositories.feed_repository import FeedRepository
from backend.services.feed import ItemNotFound, _pr_ref_from_source_ref

log = logging.getLogger(__name__)


class ActionFailed(Exception):
    """The upstream refused, or the request was never valid to send."""


class UnknownAction(Exception):
    """An action id the backend does not implement. Never a silent no-op: the
    app would report success for something that did not happen."""


class ActionService(Protocol):
    def perform(
        self, user_id: str, item_id: str, action: str, body: str | None = None
    ) -> FeedItem:
        ...

    def snooze(self, user_id: str, item_id: str, until: datetime) -> FeedItem:
        ...


_CLOSED = {FeedStatus.ACTED, FeedStatus.DISMISSED}


class DefaultActionService:
    def __init__(
        self,
        repo: FeedRepository,
        github: GitHubService,
        slack: SlackService,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repo = repo
        self._github = github
        self._slack = slack
        self._now = clock or (lambda: datetime.now(timezone.utc))

    def perform(
        self, user_id: str, item_id: str, action: str, body: str | None = None
    ) -> FeedItem:
        item = self._load(user_id, item_id)

        if action in {"reply", "comment"}:
            self._send(item, body)
        elif action == "approve":
            self._approve(item)
        elif action in {"mark_read", "dismiss"}:
            self._mark_read(item)
        else:
            raise UnknownAction(action)

        status = (
            FeedStatus.DISMISSED
            if action in {"mark_read", "dismiss"}
            else FeedStatus.ACTED
        )
        return self._repo.mark_handled(
            user_id, item_id, status=status, at=self._now()
        )

    def snooze(self, user_id: str, item_id: str, until: datetime) -> FeedItem:
        """Snooze touches nothing upstream: it is this user's private decision
        to look later, not a statement to anyone else."""
        self._load(user_id, item_id)
        return self._repo.snooze(user_id, item_id, until)

    # ---------------------------------------------------------- internals

    def _load(self, user_id: str, item_id: str) -> FeedItem:
        item = self._repo.get(user_id, item_id)
        if item is None:
            # Also the cross-user case: another user's item simply does not
            # exist as far as this caller is concerned.
            raise ItemNotFound(item_id)
        if item.status in _CLOSED:
            raise ActionFailed(f"already handled: {item_id}")
        return item

    def _send(self, item: FeedItem, body: str | None) -> None:
        text = (body or "").strip()
        if not text:
            raise ActionFailed("an empty reply is not a reply")

        try:
            if item.source == "slack":
                self._slack.reply(
                    item.source_ref, text, thread_ts=item.raw.get("thread_ts")
                )
            elif item.source == "github":
                self._github.comment_on_pull_request(
                    _pr_ref_from_source_ref(item.source_ref), text
                )
            else:
                raise UnknownAction(f"cannot reply on {item.source}")
        except UnknownAction:
            raise
        except Exception as error:
            log.warning("send failed for %s", item.source_ref, exc_info=True)
            raise ActionFailed(str(error)) from error

    def _approve(self, item: FeedItem) -> None:
        """Submitting a review, not posting a comment. A comment reading
        "approved" leaves the pull request just as blocked as before."""
        if item.source != "github":
            raise UnknownAction(f"cannot approve on {item.source}")
        try:
            self._github.approve_pull_request(
                _pr_ref_from_source_ref(item.source_ref)
            )
        except Exception as error:
            log.warning("approve failed for %s", item.source_ref, exc_info=True)
            raise ActionFailed(str(error)) from error

    def _mark_read(self, item: FeedItem) -> None:
        try:
            if item.source == "slack":
                self._slack.mark_read(item.source_ref)
            # GitHub read-state sync lands with the notification thread API;
            # dismissing locally is still correct in the meantime.
        except Exception as error:
            log.warning("mark read failed for %s", item.source_ref, exc_info=True)
            raise ActionFailed(str(error)) from error


def pr_ref(source_ref: str) -> PRRef:
    return _pr_ref_from_source_ref(source_ref)
