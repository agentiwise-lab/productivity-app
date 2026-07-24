"""Gmail.

An email has no type, so almost everything here is a judgement the model makes.
The rules' only job is the cheap half: Gmail already sorts promotions, social
and forum mail into its own categories, and classifying a newsletter would be
paying a model to tell us what the label already said.

Only unread mail is considered. Read mail has, by the user's own action, been
dealt with.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

from backend.models.events import RawEvent
from backend.models.feed import Actor

log = logging.getLogger(__name__)

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


#: One page of the compact form. Larger pages 413 through Composio.
PAGE_SIZE = 100
#: Ceiling on one refresh. Not a view limit: Later shows everything fetched.
#: This only stops a mailbox with thousands unread from stalling a refresh.
MAX_UNREAD = 400
#: How many messages the sender breakdown looks at. Composio's latency on this
#: call is roughly linear in messages returned, about 0.09s each, so 100 cost
#: eleven seconds for a list that only ever shows its top rows.
SENDER_SAMPLE = 50


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


def _sent_at(message: dict[str, Any]) -> datetime | None:
    """When the message was actually sent.

    The two fetch shapes disagree: the verbose form and the webhooks carry
    ``internalDate`` as epoch milliseconds, the compact form carries
    ``messageTimestamp`` as ISO. Reading only the first meant every message from
    the compact fetch had no date, so the feed stamped it with the ingest time
    and a week-old invitation was displayed as having just arrived.
    """
    epoch = _parse_internal_date(
        message.get("internalDate") or message.get("internal_date")
    )
    if epoch is not None:
        return epoch

    stamp = message.get("messageTimestamp") or message.get("message_timestamp")
    if not isinstance(stamp, str) or not stamp:
        return None
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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


def _preview_text(message: dict[str, Any]) -> str:
    """What the compact form offers instead of a body.

    ``preview`` arrives as ``{"body": "..."}`` rather than a string, and passing
    the dict straight through failed RawEvent validation, which took the whole
    Gmail source down mid-refresh. Every branch here is guarded on type for the
    same reason.
    """
    preview = message.get("preview")
    if isinstance(preview, dict):
        text = preview.get("body")
        if isinstance(text, str) and text.strip():
            return text.strip()[:4000]
    for key in ("preview", "snippet"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:4000]
    return ""


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
    body = _plain_body(message) or _preview_text(message)

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
        occurred_at=_sent_at(message),
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

    def actionable(self, limit: int = PAGE_SIZE) -> list[RawEvent]:
        """Unread mail that could plausibly need a reply.

        The ingest path used to ask for every unread message and then let the
        rules discard the newsletters: 361 messages over three sequential pages,
        thirty-seven seconds, to find the dozen a person actually wrote. Gmail
        can exclude its own category tabs, which returns fifteen in a single
        page in four seconds, and made the whole refresh eight times faster.

        Nothing becomes invisible. Later keeps the broad query and reads it live,
        so the newsletters are all still there, one tab away.
        """
        data = self._execute(
            "GMAIL_FETCH_EMAILS",
            {
                "query": (
                    "is:unread newer_than:30d "
                    "-category:promotions -category:social "
                    "-category:forums -category:updates"
                ),
                "max_results": limit,
                "verbose": False,
            },
        )
        messages = data.get("messages") or data.get("emails") or []
        found = [message_to_raw_event(message) for message in messages]
        return [event for event in found if event is not None]

    def unread_pages(self, limit: int = MAX_UNREAD) -> Iterator[list[RawEvent]]:
        """One page at a time, so Later can render before the fetch finishes.

        Same walk as ``unread``, yielding instead of accumulating. Pulling every
        unread message is three pages and most of a minute; a list that appears
        after all of it feels broken, and one that fills in does not.
        """
        seen = 0
        page_token: str | None = None

        while seen < limit:
            arguments: dict[str, Any] = {
                "query": "is:unread newer_than:30d",
                "max_results": min(PAGE_SIZE, limit - seen),
                "verbose": False,
            }
            if page_token:
                arguments["page_token"] = page_token
            data = self._execute("GMAIL_FETCH_EMAILS", arguments)

            messages = data.get("messages") or data.get("emails") or []
            if not messages:
                return
            page = [message_to_raw_event(m) for m in messages]
            page = [event for event in page if event is not None]
            seen += len(page)
            if page:
                yield page

            page_token = data.get("nextPageToken") or data.get("next_page_token")
            if not page_token:
                return

    def unread(self, limit: int = MAX_UNREAD) -> list[RawEvent]:
        """Every unread message in the window, collected.

        The ingest path wants one list; Later wants the pages as they arrive.
        Both walk the same pager so they can never drift apart.
        """
        found: list[RawEvent] = []
        for page in self.unread_pages(limit=limit):
            found.extend(page)
        return found[:limit]

    def inbox_summary(self, sample: int = SENDER_SAMPLE) -> dict[str, Any]:
        """The real unread picture, straight from Gmail.

        The dashboard used to count the feed, which is capped per refresh and,
        since noise stopped being stored, holds only the handful of mails that
        need a reply. It reported "42 emails, 31 senders" when the mailbox had
        two hundred unread, and after the change it would have reported three.

        ``resultSizeEstimate`` gives the true unread total in one call; the
        sample is only for the per-sender breakdown, and says how far it reached.
        """
        # ``verbose`` is off deliberately. The full form carries every body and
        # blew past Composio's payload ceiling with a 413 at this sample size,
        # and the summary only needs who sent what: the compact form still
        # carries ``sender`` and the unread estimate, which is all of it.
        # The sample and the count are independent calls, so they go together.
        with ThreadPoolExecutor(max_workers=2) as pool:
            sample_f = pool.submit(
                self._execute,
                "GMAIL_FETCH_EMAILS",
                {
                    "query": "is:unread newer_than:30d",
                    "max_results": sample,
                    "verbose": False,
                },
            )
            count_f = pool.submit(self._unread_count)

        data = sample_f.result()
        messages = data.get("messages") or data.get("emails") or []
        senders: dict[tuple[str, str], int] = {}
        for message in messages:
            from_header = message.get("sender") or _header(
                message.get("payload") or {}, "From"
            )
            name, email = _sender(from_header or "")
            key = (name or email or "unknown", email)
            senders[key] = senders.get(key, 0) + 1

        return {
            "unread": count_f.result() or len(messages),
            "sampled": len(messages),
            "senders": senders,
        }

    def _unread_count(self) -> int:
        """How many messages are actually unread, counted rather than estimated.

        ``resultSizeEstimate`` is what it says: on this mailbox it reported 201
        against a true 361, so the tile understated the inbox by nearly half.
        ``ids_only`` returns every id and nothing else, which is both exact and
        the cheapest call the toolkit offers: all 361 in about a second and a
        half, against thirty-two seconds to fetch the same messages in full.
        """
        try:
            data = self._execute(
                "GMAIL_FETCH_EMAILS",
                {
                    "query": "is:unread newer_than:30d",
                    "max_results": 500,
                    "ids_only": True,
                },
            )
        except Exception:
            log.info("could not count unread mail", exc_info=True)
            return 0
        return len(data.get("messages") or data.get("emails") or [])

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
