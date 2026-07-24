"""Later, streamed live from each source.

Later is a mirror, not a record. Nothing here is stored: it asks the provider
what is currently unread, unanswered or open, drops whatever is already on Home,
and yields the rest in batches so the screen fills as the pages arrive rather
than after the last one.

This is a reversal. Later used to be 360 stored rows, which meant keeping a copy
of a month of newsletters to render a list that is different tomorrow anyway.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.models.sources import Source
from backend.services.later import LaterService

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


class _FakeGmail:
    """Two pages, so the batching is visible."""

    def __init__(self, pages=None):
        self.pages = pages if pages is not None else [
            [_mail("m1", "Newsletter one"), _mail("m2", "Newsletter two")],
            [_mail("m3", "Newsletter three")],
        ]
        self.calls = 0

    def unread_pages(self, limit=None):
        for page in self.pages:
            self.calls += 1
            yield page


def _mail(ref, title):
    from backend.models.events import RawEvent

    return RawEvent(
        source="gmail",
        source_ref=f"gmail:{ref}",
        reason="gmail_bulk",
        subject_type="Email",
        title=title,
        url="",
        repo="",
        occurred_at=NOW,
    )


def _service(**kw):
    return LaterService(clock=lambda: NOW, **kw)


def test_rows_arrive_in_batches_rather_than_one_final_list():
    """The point of streaming: the first page renders while the second is still
    in flight. Gmail alone is 37 seconds if you wait for all of it."""
    service = _service(gmail=_FakeGmail())
    batches = list(service.stream("u", Source.GMAIL, on_home=set()))

    assert len(batches) == 2
    assert [row.title for row in batches[0]] == ["Newsletter one", "Newsletter two"]
    assert [row.title for row in batches[1]] == ["Newsletter three"]


def test_anything_already_on_home_is_not_repeated_in_later():
    """Later is what did *not* need you. An item in both places would be the
    two screens disagreeing about the same message."""
    service = _service(gmail=_FakeGmail())
    batches = list(service.stream("u", Source.GMAIL, on_home={"gmail:m2"}))

    titles = [row.title for batch in batches for row in batch]
    assert titles == ["Newsletter one", "Newsletter three"]


def test_the_limit_stops_the_fetch_rather_than_trimming_the_result():
    """A cap that only trims at the end still pays for every page."""
    gmail = _FakeGmail()
    service = _service(gmail=gmail)
    rows = [row for batch in service.stream("u", Source.GMAIL, on_home=set(), limit=2)
            for row in batch]

    assert len(rows) == 2
    assert gmail.calls == 1, "the second page should never have been requested"


def test_a_source_that_is_not_connected_yields_nothing_rather_than_raising():
    service = _service()
    assert list(service.stream("u", Source.GMAIL, on_home=set())) == []


def test_a_failing_source_ends_the_stream_instead_of_breaking_the_screen():
    class _Broken:
        def unread_pages(self, limit=None):
            yield [_mail("m1", "first page arrived")]
            raise RuntimeError("rate limited")

    service = _service(gmail=_Broken())
    batches = list(service.stream("u", Source.GMAIL, on_home=set()))

    # What did arrive is kept: a partial list beats an error screen.
    assert [row.title for row in batches[0]] == ["first page arrived"]


def test_rows_carry_what_a_list_needs_to_render():
    service = _service(gmail=_FakeGmail())
    row = next(iter(service.stream("u", Source.GMAIL, on_home=set())))[0]

    assert row.source is Source.GMAIL
    assert row.source_ref == "gmail:m1"
    assert row.title == "Newsletter one"
    assert row.occurred_at == NOW


def test_html_escapes_are_decoded_rather_than_shown_to_the_reader():
    """Mail subjects and snippets arrive escaped, so a plain apostrophe reaches
    the phone as `&#39;` and a quotation mark as `&quot;`. Rendering those
    verbatim is the app showing its plumbing in the middle of a sentence."""
    from backend.services.later import _to_row
    from backend.models.events import RawEvent

    row = _to_row(
        RawEvent(
            source="gmail",
            source_ref="gmail:m9",
            reason="gmail_unread",
            subject_type="Message",
            title="Substack&#39;s AI Detector",
            url="",
            repo="",
            body="Watch now | &quot;DoN&#39;T&quot; miss it &amp; more",
            occurred_at=NOW,
        )
    )

    assert row.title == "Substack's AI Detector"
    assert row.summary == 'Watch now | "DoN\'T" miss it & more'


# --- every source at once --------------------------------------------------


class _SlowLinear:
    """Answers in one call, like the real one."""

    def assigned_to_me(self):
        return [_issue("AGE-1")]


def _issue(ref):
    from backend.models.events import RawEvent

    return RawEvent(
        source="linear", source_ref=f"linear:{ref}", reason="linear_backlog",
        subject_type="Issue", title=f"{ref} something", url="", repo="",
        occurred_at=NOW,
    )


def test_all_sources_stream_together_and_each_batch_says_which_it_is():
    """One source at a time meant Gmail's ten seconds before anything showed,
    and another ten every time the user tapped a different source."""
    service = _service(gmail=_FakeGmail(), linear=_SlowLinear())
    batches = list(service.stream_all("u", on_home=set()))

    rows = [row for batch in batches for row in batch]
    sources = {row.source for row in rows}
    assert sources == {Source.GMAIL, Source.LINEAR}
    assert len(rows) == 4  # three mails, one issue


def test_a_source_that_fails_does_not_stop_the_others():
    class _Broken:
        def assigned_to_me(self):
            raise RuntimeError("linear is down")

    service = _service(gmail=_FakeGmail(), linear=_Broken())
    rows = [row for batch in service.stream_all("u", on_home=set()) for row in batch]

    assert [row.source for row in rows] == [Source.GMAIL] * 3


def test_home_items_are_excluded_across_every_source():
    service = _service(gmail=_FakeGmail(), linear=_SlowLinear())
    rows = [
        row
        for batch in service.stream_all("u", on_home={"linear:AGE-1", "gmail:m1"})
        for row in batch
    ]
    refs = {row.source_ref for row in rows}
    assert "linear:AGE-1" not in refs and "gmail:m1" not in refs
    assert len(rows) == 2
