"""Google Docs, delivered through its notification emails.

Composio exposes no Google Docs comment/mention/share *event*: the only
first-party path is the Drive comments API (``GOOGLEDRIVE_LIST_COMMENTS``), which
needs a separate Google Drive connection and a find-files-then-scan-comments walk
with fuzzy mention detection. Google itself, though, emails every one of these
the moment it happens — a comment mentioning you from
``comments-noreply@docs.google.com``, a share from ``drive-shares-noreply``. That
notification is the clean, reliable "you were mentioned" signal.

So Google Docs is its own source with its own pull, and that pull reads the
notification emails from Gmail. It is deliberately kept separate from the Gmail
source (the same mail may surface under both; dedupe is a later concern), and it
tags every item ``source="google_docs"`` so it lands under Google Docs, not Gmail.
The Gmail dependency is a pragmatic implementation detail: switching to the Drive
comments API later would make it fully independent.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from backend.integrations.gmail import (
    GMAIL_TOOLKIT_VERSION,
    _header,
    _plain_body,
    _preview_text,
    _sender,
    _sent_at,
)
from backend.models.events import RawEvent
from backend.models.feed import Actor

log = logging.getLogger(__name__)

#: Notification senders Google uses, mapped to the reason (and thus the band).
_DOCS_SENDERS: dict[str, str] = {
    "comments-noreply@docs.google.com": "docs_mention",
    "drive-shares-noreply@google.com": "docs_share",
}

#: The Gmail search that finds them. Broad on purpose (no unread filter): a Docs
#: mention is worth surfacing whether or not the mail was opened.
_QUERY = " OR ".join(f"from:{sender}" for sender in _DOCS_SENDERS) + " newer_than:30d"


def docs_notification_to_raw_event(message: dict[str, Any]) -> RawEvent | None:
    """A Google notification email -> a Google Docs feed item.

    Only mail from a known Docs/Drive notification address becomes an item; any
    other message the query happens to return is ignored rather than mis-filed.
    """
    payload = message.get("payload") or {}
    from_header = _header(payload, "From") or message.get("sender") or ""
    name, email = _sender(from_header)
    reason = _DOCS_SENDERS.get(email.strip().lower())
    if reason is None:
        return None

    subject = _header(payload, "Subject") or message.get("subject") or "(no subject)"
    body = _plain_body(message) or _preview_text(message)
    return RawEvent(
        source="google_docs",
        source_ref=f"google_docs:{message.get('id') or message.get('messageId', '')}",
        reason=reason,
        subject_type="Document",
        title=subject,
        body=body,
        url=(
            f"https://mail.google.com/mail/u/0/#inbox/"
            f"{message.get('threadId') or message.get('thread_id') or message.get('id', '')}"
        ),
        repo="",
        context_chip="Google Docs",
        actor=Actor(login=email, display_name=name or None),
        occurred_at=_sent_at(message),
        # A mention names you and expects an answer.
        is_blocking=reason == "docs_mention",
        raw=message,
    )


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


class GoogleDocsService(Protocol):
    def mentions(self, limit: int = 50) -> list[RawEvent]:
        ...

    def documents(self, limit: int = 25) -> list[dict[str, Any]]:
        ...


class ComposioGoogleDocsService:
    """Reads Google Docs comment-mentions and shares from their Gmail
    notifications. Needs the user's Gmail connected (that is where Google delivers
    the notifications), which the factory binds by ``user_id``."""

    def __init__(
        self, composio: Any, user_id: str, version: str = GMAIL_TOOLKIT_VERSION
    ) -> None:
        self._composio = composio
        self._user_id = user_id
        self._version = version

    def _execute(self, slug: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._composio.tools.execute(
            slug, user_id=self._user_id, arguments=arguments, version=self._version
        )
        if isinstance(result, dict):
            return result.get("data") or {}
        return getattr(result, "data", {}) or {}

    def mentions(self, limit: int = 50) -> list[RawEvent]:
        try:
            data = self._execute(
                "GMAIL_FETCH_EMAILS",
                {"query": _QUERY, "max_results": limit, "verbose": True},
            )
        except Exception:
            log.warning("could not read Google Docs notifications", exc_info=True)
            return []
        messages = data.get("messages") or data.get("emails") or []
        found = [docs_notification_to_raw_event(message) for message in messages]
        return [event for event in found if event is not None]

    def documents(self, limit: int = 25) -> list[dict[str, Any]]:
        """The user's recent Google Docs, newest first. Unlike ``mentions`` this
        reads the Docs account directly (GOOGLEDOCS_SEARCH_DOCUMENTS), so it works
        from the Docs connection alone."""
        try:
            data = self._execute(
                "GOOGLEDOCS_SEARCH_DOCUMENTS", {"max_results": limit}
            )
        except Exception:
            log.warning("could not list Google Docs documents", exc_info=True)
            return []
        files = data.get("files") or data.get("documents") or []
        out: list[dict[str, Any]] = []
        for f in files:
            if not isinstance(f, dict):
                continue
            out.append(
                {
                    "name": f.get("name") or "(untitled)",
                    "url": f.get("webViewLink") or f.get("display_url") or "",
                    "modified": _parse_time(f.get("modifiedTime")),
                }
            )
        return out
