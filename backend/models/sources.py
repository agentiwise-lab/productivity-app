"""The source catalogue.

Every source this product supports is listed here whether or not the user has
connected it. Sources is a menu, not a report: a list built from what happens to
be connected can never show you what you are missing, and it was exactly that
mistake that made the app claim only GitHub existed.

Composio's toolkit slugs differ from our source names (``googlecalendar`` versus
``calendar``), so the mapping lives here rather than being spelled out at each
call site.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class Source(str, Enum):
    GITHUB = "github"
    SLACK = "slack"
    CALENDAR = "calendar"
    LINEAR = "linear"
    GMAIL = "gmail"
    GOOGLE_DOCS = "google_docs"


class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"
    ERROR = "error"


class SourceInfo(BaseModel):
    source: Source
    label: str
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    # Live items from this source, so Sources can show what each one is asking.
    count: int = 0
    urgent: int = 0
    connected_account_id: str | None = None


#: Display order. Deliberately fixed rather than sorted by count, so the list
#: does not reshuffle under the user every time the feed changes.
CATALOGUE: list[tuple[Source, str, str]] = [
    (Source.GITHUB, "GitHub", "github"),
    (Source.SLACK, "Slack", "slack"),
    (Source.CALENDAR, "Google Calendar", "googlecalendar"),
    (Source.LINEAR, "Linear", "linear"),
    (Source.GMAIL, "Gmail", "gmail"),
    (Source.GOOGLE_DOCS, "Google Docs", "googledocs"),
]

TOOLKIT_TO_SOURCE: dict[str, Source] = {
    toolkit: source for source, _, toolkit in CATALOGUE
}
SOURCE_TO_TOOLKIT: dict[Source, str] = {
    source: toolkit for source, _, toolkit in CATALOGUE
}
LABELS: dict[Source, str] = {source: label for source, label, _ in CATALOGUE}
