"""Parse/expand tests for the .ics source — no network."""
import datetime as dt
from zoneinfo import ZoneInfo

from app.calendar import source

UTC = dt.timezone.utc
NY = ZoneInfo("America/New_York")

ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//test//test//EN
BEGIN:VEVENT
UID:timed-utc
SUMMARY:UTC Meeting
DTSTART:20260624T150000Z
DTEND:20260624T160000Z
END:VEVENT
BEGIN:VEVENT
UID:floating
SUMMARY:Floating Lunch
DTSTART:20260624T120000
DTEND:20260624T123000
END:VEVENT
BEGIN:VEVENT
UID:allday
SUMMARY:Holiday
DTSTART;VALUE=DATE:20260624
DTEND;VALUE=DATE:20260625
END:VEVENT
BEGIN:VEVENT
UID:daily
SUMMARY:Daily Standup
DTSTART:20260620T090000Z
DTEND:20260620T091500Z
RRULE:FREQ=DAILY
END:VEVENT
END:VCALENDAR
"""

NOW = dt.datetime(2026, 6, 24, 16, 0, tzinfo=UTC)  # 12:00 in New York


def _by_title(events):
    return {e["title"]: e for e in events}


def test_parse_window_and_normalization():
    events = source.parse_events(ICS, NY, now=NOW, window_days=1)
    by = _by_title(events)

    # zoned UTC stays UTC
    assert by["UTC Meeting"]["start_utc"].startswith("2026-06-24T15:00:00")
    assert by["UTC Meeting"]["all_day"] == 0

    # floating time is interpreted in the configured tz (NY 12:00 -> 16:00Z)
    assert by["Floating Lunch"]["start_utc"].startswith("2026-06-24T16:00:00")

    # all-day flagged
    assert by["Holiday"]["all_day"] == 1


def test_recurrence_expanded_with_distinct_keys():
    events = source.parse_events(ICS, NY, now=NOW, window_days=1)
    standups = [e for e in events if e["title"] == "Daily Standup"]
    # window is today +/- 1 day -> at least 2-3 daily occurrences
    assert len(standups) >= 2
    # synthetic keys are unique per occurrence
    assert len({s["key"] for s in standups}) == len(standups)
    # each occurrence keeps the 09:00Z wall time
    assert all("T09:00:00" in s["start_utc"] for s in standups)
