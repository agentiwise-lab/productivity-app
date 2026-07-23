"""Gmail.

An email has no type, so almost everything here is a judgement the model makes.
The rules' only job is the cheap half: Gmail already sorts promotions, social
and forum mail into its own categories, and classifying a newsletter would be
paying a model to tell us what the label already said.

Only unread mail is considered. Read mail has, by the user's own action, been
dealt with.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.models.events import RawEvent
from backend.models.feed import Actor

GMAIL_TOOLKIT_VERSION = "20260721_00"

#: Gmail's own tabs. Anything filed here was never addressed to a person.
_NOISE_LABELS = {
    "CATEGORY_PROMOTIONS",
    "CATEGORY_SOCIAL",
    "CATEGORY_FORUMS",
    "CATEGORY_UPDATES",
    "SPAM",
    "TRASH",
}


def _header(payload: dict[str, Any], name: str) -> str:
    for header in (payload.get("headers") or []):
        if str(header.get("name", "")).lower() == name.lower():
            return header.get("value") or ""
    return ""


def _parse_internal_date(value: Any) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(value) / 1000, tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _sender(from_header: str) -> tuple[str, str]:
    """"Priya Sharma <priya@x.com>" into a name and an address."""
    if "<" in from_header and ">" in from_header:
        name = from_header.split("<", 1)[0].strip().strip('"')
        email = from_header.split("<", 1)[1].split(">", 1)[0].strip()
        return name or email, email
    return from_header.strip(), from_header.strip()


def _decode(data: str) -> str:
    import base64

    try:
        return base64.urlsafe_b64decode(data + "===").decode("utf-8", "replace")
    except Exception:
        return ""


def _walk_parts(part: dict[str, Any], out: list[str]) -> None:
    """Depth-first for the text/plain parts.

    Preferred over text/html: the sheet renders text, and stripping tags out of
    a marketing email produces worse output than the plain alternative the
    sender already provided.
    """
    mime = part.get("mimeType") or ""
    body = part.get("body") or {}
    if mime == "text/plain" and body.get("data"):
        out.append(_decode(body["data"]))
    for child in part.get("parts") or []:
        _walk_parts(child, out)


def _plain_body(message: dict[str, Any]) -> str:
    for key in ("messageText", "body", "text"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    parts: list[str] = []
    _walk_parts(message.get("payload") or {}, parts)
    text = "\n".join(part for part in parts if part.strip())
    if not text:
        return ""
    # Quoted history doubles the length and adds nothing: the reply is at the
    # top and the thread is already in the app.
    lines: list[str] = []
    for line in text.splitlines():
        if line.startswith(">") or line.startswith("On ") and line.endswith("wrote:"):
            break
        lines.append(line)
    return "\n".join(lines).strip()[:4000]


def message_to_raw_event(message: dict[str, Any]) -> RawEvent | None:
    labels = set(message.get("labelIds") or message.get("label_ids") or [])
    if "UNREAD" not in labels:
        return None

    payload = message.get("payload") or {}
    subject = _header(payload, "Subject") or message.get("subject") or "(no subject)"
    from_header = _header(payload, "From") or message.get("sender") or ""
    name, email = _sender(from_header)

    noisy = bool(labels & _NOISE_LABELS)
    # A mailing list header is a stronger signal than the category tab, which
    # Gmail applies inconsistently to transactional mail.
    if _header(payload, "List-Unsubscribe"):
        noisy = True

    # The whole readable message, not just Gmail's one-line snippet. The
    # detail sheet shows the mail itself, and a snippet is not a mail.
    body = _plain_body(message) or message.get("snippet") or ""

    return RawEvent(
        source="gmail",
        source_ref=f"gmail:{message.get('id') or message.get('messageId', '')}",
        reason="gmail_bulk" if noisy else "gmail_message",
        subject_type="Email",
        title=subject,
        body=body,
        url=(
            f"https://mail.google.com/mail/u/0/#inbox/"
            f"{message.get('threadId') or message.get('id', '')}"
        ),
        repo="",
        context_chip="Inbox",
        actor=Actor(login=email, display_name=name or None),
        occurred_at=_parse_internal_date(
            message.get("internalDate") or message.get("internal_date")
        ),
        # Someone wrote to this person by name and has had no answer.
        is_blocking=not noisy,
        raw=message,
    )


class ComposioGmailService:
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

    def unread(self, max_results: int = 40) -> list[RawEvent]:
        data = self._execute(
            "GMAIL_FETCH_EMAILS",
            {
                "query": "is:unread newer_than:30d",
                "max_results": max_results,
                "verbose": True,
            },
        )
        messages = data.get("messages") or data.get("emails") or []
        found = [message_to_raw_event(message) for message in messages]
        return [event for event in found if event is not None]

    def reply(self, source_ref: str, body: str) -> None:
        thread_id = source_ref.split(":", 1)[1] if ":" in source_ref else source_ref
        self._execute(
            "GMAIL_REPLY_TO_THREAD",
            {"thread_id": thread_id, "message_body": body, "user_id": "me"},
        )

    def mark_read(self, source_ref: str) -> None:
        message_id = source_ref.split(":", 1)[1] if ":" in source_ref else source_ref
        self._execute(
            "GMAIL_MODIFY_EMAIL_LABELS",
            {"message_id": message_id, "remove_label_ids": ["UNREAD"]},
        )
