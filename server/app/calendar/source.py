"""Fetch + parse a personal .ics into normalized, UTC event records.

`icalendar` parses the file; `recurring_ical_events` expands RRULE occurrences
within a window (icalendar alone does not expand recurrences). All times are
normalized to UTC; floating (tz-naive) times are interpreted in `tz`.
"""
import datetime as dt
import logging
import urllib.request

import icalendar
import recurring_ical_events

log = logging.getLogger(__name__)

_FETCH_TIMEOUT = 20  # seconds — bound it so the poller thread can't hang


def fetch_ics(url: str) -> str:
    """GET the .ics text. Raises on network/HTTP error or non-calendar payload."""
    req = urllib.request.Request(url, headers={"User-Agent": "eink-dashboard"})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in raw:
        raise ValueError("response is not an iCalendar document")
    return raw


def _to_utc(value, tz) -> dt.datetime:
    """Normalize a date/datetime to an aware UTC datetime.

    Naive datetimes are treated as floating → interpreted in `tz`.
    Dates (all-day) become local midnight, then UTC.
    """
    if isinstance(value, dt.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=tz)
        return value.astimezone(dt.timezone.utc)
    return dt.datetime.combine(value, dt.time.min, tzinfo=tz).astimezone(dt.timezone.utc)


def _is_all_day(value) -> bool:
    return isinstance(value, dt.date) and not isinstance(value, dt.datetime)


def parse_events(ics_text: str, tz, now: dt.datetime | None = None,
                 window_days: int = 1) -> list[dict]:
    """Expand occurrences in [today - window, today + window] (local) → event dicts."""
    now = now or dt.datetime.now(tz)
    today = now.astimezone(tz).date()
    start = dt.datetime.combine(today - dt.timedelta(days=window_days), dt.time.min, tzinfo=tz)
    end = dt.datetime.combine(today + dt.timedelta(days=window_days), dt.time.max, tzinfo=tz)

    cal = icalendar.Calendar.from_ical(ics_text)
    occurrences = recurring_ical_events.of(cal).between(start, end)

    events: list[dict] = []
    for comp in occurrences:
        dtstart = comp.get("DTSTART")
        if dtstart is None:
            continue
        start_val = dtstart.dt
        all_day = _is_all_day(start_val)

        dtend = comp.get("DTEND")
        if dtend is not None:
            end_val = dtend.dt
        else:
            # No DTEND: a date is a 1-day all-day event; a datetime is zero-length.
            end_val = (start_val + dt.timedelta(days=1)) if all_day else start_val

        start_utc = _to_utc(start_val, tz)
        end_utc = _to_utc(end_val, tz)
        uid = str(comp.get("UID", "")) or "nouid"
        events.append({
            "key": f"{uid}@{start_utc.isoformat()}",
            "uid": uid,
            "title": str(comp.get("SUMMARY", "")).strip(),
            "start_utc": start_utc.isoformat(),
            "end_utc": end_utc.isoformat(),
            "all_day": 1 if all_day else 0,
            "location": str(comp.get("LOCATION", "")).strip(),
        })
    return events
