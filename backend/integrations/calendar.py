"""Google Calendar.

Calendar does two jobs here and they must not be confused. It supplies the feed
with things needing a decision (an invite awaiting your RSVP, a meeting about to
start), and it supplies "Your day" with the shape of the day itself. The second
is never stored: a cached schedule is a schedule that will eventually be shown
after it stopped being true.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic import BaseModel

from backend.models.events import RawEvent
from backend.models.feed import Actor

CALENDAR_TOOLKIT_VERSION = "20260721_00"

#: A meeting this close is the most urgent thing a person can have, because
#: unlike everything else in the feed it cannot be done later. An hour is the
#: point at which you would want to be told, not fifteen minutes, by which time
#: being told is no longer useful.
STARTING_SOON = timedelta(hours=1)

#: How far ahead a scheduled (already-accepted) meeting is worth putting on the
#: feed. Meetings inside this window are "your day"; ones further out are context
#: on the ruler, not an action, so they are left off the feed until the day of.
DAY_AHEAD = timedelta(hours=24)


class Meeting(BaseModel):
    title: str
    start: datetime
    end: datetime
    location: str | None = None
    conference_url: str | None = None


def _parse(value: Any) -> datetime | None:
    if isinstance(value, dict):
        value = value.get("dateTime") or value.get("date")
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    # All-day events parse without a timezone; treat them as UTC midnight
    # rather than dropping them, so they still occupy the ruler.
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def event_to_meeting(event: dict[str, Any]) -> Meeting | None:
    start = _parse(event.get("start"))
    end = _parse(event.get("end"))
    if start is None or end is None:
        return None
    return Meeting(
        title=event.get("summary") or "(no title)",
        start=start,
        end=end,
        location=event.get("location"),
        conference_url=event.get("hangoutLink"),
    )


def _my_response(event: dict[str, Any], email: str | None) -> str | None:
    for attendee in event.get("attendees") or []:
        if attendee.get("self") or (email and attendee.get("email") == email):
            return attendee.get("responseStatus")
    return None


def event_to_raw_event(
    event: dict[str, Any], *, email: str | None = None, now: datetime | None = None
) -> RawEvent | None:
    """An event becomes a feed item when it is on your day or wants an answer.

    A meeting that has already ended is gone: nothing is left to do about it, so
    it never reaches the feed. What remains is an invitation you have not
    answered (any time), or a meeting on your day (within the next 18 hours). The
    *tier* is not decided here — read-time ranking places it from how close the
    start is (within the hour is Urgent, otherwise by-EOD), so the same stored
    row moves as the clock does. ``deadline`` carries the *end* so a passed
    meeting can be dropped, and ``occurred_at`` carries the *start* so the tier
    can be judged from it.
    """
    now = now or datetime.now(timezone.utc)
    meeting = event_to_meeting(event)
    if meeting is None or event.get("status") == "cancelled":
        return None

    # Over and done: not an action, not shown.
    if now >= meeting.end:
        return None

    response = _my_response(event, email)
    on_my_day = meeting.start - now <= DAY_AHEAD
    if response == "needsAction":
        reason = "calendar_invite"
    elif on_my_day:
        reason = "calendar_meeting"
    else:
        # Accepted and more than a day out: context on the ruler, not the feed.
        return None

    organizer = (event.get("organizer") or {}).get("email") or ""
    return RawEvent(
        source="calendar",
        source_ref=f"calendar:{event.get('id', '')}",
        reason=reason,
        subject_type="Event",
        title=meeting.title,
        url=event.get("htmlLink") or "",
        repo="",
        context_chip=meeting.start.strftime("%H:%M"),
        # The description and location, so the card can say what the meeting is
        # rather than only when it is.
        body="\n".join(
            part
            for part in (
                event.get("description"),
                f"Location: {meeting.location}" if meeting.location else None,
                f"Join: {meeting.conference_url}" if meeting.conference_url else None,
                f"{meeting.start:%H:%M} to {meeting.end:%H:%M}",
            )
            if part
        ),
        actor=Actor(login=organizer, display_name=organizer.split("@")[0] or None),
        deadline=meeting.end,
        occurred_at=meeting.start,
        is_blocking=reason == "calendar_invite",
        raw=event,
    )


def starting_soon_to_raw_event(data: dict[str, Any]) -> RawEvent | None:
    """GOOGLECALENDAR_EVENT_STARTING_SOON_TRIGGER -> a feed item.

    The trigger fires when a meeting is minutes out, which is the one calendar
    event that cannot be handled later. Its payload is flatter than the events
    list (a ``start_timestamp`` rather than a ``start`` object), so it has its
    own mapper. The tier is settled by the ``calendar_starting`` band, not here.
    """
    event_id = data.get("event_id") or data.get("id")
    if not event_id:
        return None
    start = _parse(data.get("start_timestamp") or data.get("start_time") or data.get("start"))
    if start is None:
        return None

    summary = data.get("summary") or "(no title)"
    location = data.get("location")
    conference = data.get("hangout_link") or data.get("hangoutLink")
    body = "\n".join(
        part
        for part in (
            data.get("description"),
            f"Location: {location}" if location else None,
            f"Join: {conference}" if conference else None,
            f"Starts {start:%H:%M}",
        )
        if part
    )
    organizer = data.get("organizer_email") or data.get("creator_email") or ""
    # The starting-soon payload carries no end time, so estimate one hour out.
    # ``deadline`` is the meeting's end (used to drop it once it is over), and
    # ``occurred_at`` is the start (used to judge the tier).
    end = _parse(data.get("end_timestamp") or data.get("end_time")) or (
        start + STARTING_SOON
    )
    return RawEvent(
        source="calendar",
        source_ref=f"calendar:{event_id}",
        reason="calendar_starting",
        subject_type="Event",
        title=summary,
        url=data.get("html_link") or data.get("htmlLink") or "",
        repo="",
        context_chip=start.strftime("%H:%M"),
        body=body,
        actor=Actor(login=organizer, display_name=organizer.split("@")[0] or None)
        if organizer
        else None,
        deadline=end,
        occurred_at=start,
        is_blocking=False,
        raw=data,
    )


class ComposioCalendarService:
    """Reads the calendar. Never writes without an explicit user action."""

    def __init__(
        self,
        composio: Any,
        user_id: str,
        version: str = CALENDAR_TOOLKIT_VERSION,
        email: str | None = None,
    ) -> None:
        self._composio = composio
        self._user_id = user_id
        self._version = version
        self._own_email = email

    @property
    def _email(self) -> str:
        """Which attendee row is ours. Asked once and remembered, because an
        RSVP that patched the wrong attendee would answer for someone else.

        Only a real address is cached: an empty result (the account not yet
        readable) is left unresolved so the next call retries, rather than
        freezing an empty ``self._own_email`` for the life of the process.
        """
        if self._own_email:
            return self._own_email
        data = self._execute("GOOGLECALENDAR_GET_CALENDAR", {"calendar_id": "primary"})
        resolved = str(data.get("id") or "")
        if resolved:
            self._own_email = resolved
        return resolved

    def _execute(self, slug: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._composio.tools.execute(
            slug, user_id=self._user_id, arguments=arguments, version=self._version
        )
        if isinstance(result, dict):
            return result.get("data") or {}
        return getattr(result, "data", {}) or {}

    def _events(self, start: datetime, end: datetime) -> list[dict[str, Any]]:
        data = self._execute(
            "GOOGLECALENDAR_EVENTS_LIST",
            {
                "calendarId": "primary",
                "timeMin": start.isoformat().replace("+00:00", "Z"),
                "timeMax": end.isoformat().replace("+00:00", "Z"),
                "singleEvents": True,
                "orderBy": "startTime",
                "maxResults": 50,
            },
        )
        return data.get("items") or data.get("events") or []

    def respond(self, source_ref: str, accepted: bool) -> None:
        """Accept or decline, which is one call with a different answer in it.

        Only this user's own attendee row moves. Patching the event itself
        would be answering on everyone's behalf.
        """
        event_id = source_ref.split(":", 1)[-1]
        self._execute(
            "GOOGLECALENDAR_UPDATE_EVENT",
            {
                "calendar_id": "primary",
                "event_id": event_id,
                "attendees": [
                    {
                        "email": self._email,
                        "responseStatus": "accepted" if accepted else "declined",
                        "self": True,
                    }
                ],
            },
        )

    def day_window(self, now: datetime | None = None) -> list[Meeting]:
        """Meetings around the present moment, for the ruler.

        A wide window from last night through tomorrow, deliberately not
        filtered to "today" here: the server does not reliably know the user's
        timezone, and at 00:15 local it is still yesterday in UTC. The client
        knows its own calendar day and filters to it, so this only has to
        return enough to choose from.
        """
        now = now or datetime.now(timezone.utc)
        start = now - timedelta(hours=18)
        meetings = [
            event_to_meeting(event)
            for event in self._events(start, now + timedelta(hours=30))
        ]
        return sorted(
            (m for m in meetings if m is not None), key=lambda m: m.start
        )

    def today(self, now: datetime | None = None) -> list[Meeting]:
        """The ruler's data. Read live on every open, never cached."""
        now = now or datetime.now(timezone.utc)
        start = now - timedelta(hours=now.hour + 6)
        meetings = [
            event_to_meeting(event)
            for event in self._events(start, start + timedelta(days=1, hours=12))
        ]
        today = now.date()
        return sorted(
            (
                m
                for m in meetings
                if m is not None and m.start.astimezone(now.tzinfo).date() == today
            ),
            key=lambda m: m.start,
        )

    def window_meetings(self, now: datetime | None = None) -> list[dict[str, Any]]:
        """Every meeting in the last 30 days as {title, minutes}, for grouping
        into a frequency breakdown on the dashboard."""
        now = now or datetime.now(timezone.utc)
        events = self._events(now - timedelta(days=30), now)
        out = []
        for event in events:
            meeting = event_to_meeting(event)
            if meeting is None or event.get("status") == "cancelled":
                continue
            minutes = round((meeting.end - meeting.start).total_seconds() / 60)
            if minutes <= 0:
                continue
            out.append({"title": meeting.title, "minutes": minutes})
        return out

    def window_summary(
        self, now: datetime | None = None
    ) -> tuple[int, float]:
        """(meetings, hours) attended in the last 30 days, for the dashboard."""
        now = now or datetime.now(timezone.utc)
        events = self._events(now - timedelta(days=30), now)
        meetings = [m for m in (event_to_meeting(e) for e in events) if m is not None]
        hours = sum((m.end - m.start).total_seconds() / 3600 for m in meetings)
        return len(meetings), hours

    def pending(
        self, email: str | None = None, now: datetime | None = None
    ) -> list[RawEvent]:
        now = now or datetime.now(timezone.utc)
        events = self._events(now - timedelta(hours=12), now + timedelta(days=14))
        found = [event_to_raw_event(e, email=email, now=now) for e in events]
        return [event for event in found if event is not None]
