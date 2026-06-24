"""Unit tests for the pure Now/Next selector — no network, frozen clock."""
import datetime as dt
from zoneinfo import ZoneInfo

from app import agenda

UTC = dt.timezone.utc


def ev(title, start, end, all_day=0):
    """start/end are 'HH:MM' on 2026-06-24 UTC unless they are full ISO strings."""
    def iso(t):
        if "T" in t:
            return t
        h, m = t.split(":")
        return f"2026-06-24T{h}:{m}:00+00:00"
    return {
        "key": f"{title}@{start}", "uid": title, "title": title,
        "start_utc": iso(start), "end_utc": iso(end),
        "all_day": all_day, "location": "",
    }


NOW = dt.datetime(2026, 6, 24, 9, 30, tzinfo=UTC)  # 09:30 UTC


def test_in_meeting_with_next():
    events = [ev("Standup", "09:00", "10:00"), ev("1:1", "11:30", "12:00")]
    assert agenda.banner_text(events, NOW, UTC) == (
        "Now: Standup until 10:00     ·     Next: 1:1 at 11:30"
    )
    assert agenda.has_now(events, NOW, UTC) is True


def test_in_meeting_nothing_after():
    events = [ev("Standup", "09:00", "10:00")]
    assert agenda.banner_text(events, NOW, UTC) == "Now: Standup until 10:00     ·     Nothing after"


def test_free_now_more_today():
    events = [ev("1:1", "11:30", "12:00")]
    assert agenda.banner_text(events, NOW, UTC) == "Next: 1:1 at 11:30"
    assert agenda.has_now(events, NOW, UTC) is False


def test_nothing_left_today():
    events = [ev("Early", "07:00", "08:00")]
    assert agenda.banner_text(events, NOW, UTC) == "No more events today"


def test_no_events_hides_band():
    assert agenda.banner_text([], NOW, UTC) is None


def test_all_day_only_is_ignored():
    events = [ev("PTO", "00:00", "23:59", all_day=1)]
    assert agenda.banner_text(events, NOW, UTC) is None
    assert agenda.has_now(events, NOW, UTC) is False


def test_overlap_picks_soonest_ending():
    events = [ev("Long", "09:00", "11:00"), ev("Short", "09:00", "09:45")]
    now_ev, _ = agenda.select_now_next(events, NOW, UTC)
    assert now_ev["title"] == "Short"


def test_next_does_not_leak_into_tomorrow():
    events = [ev("Tomorrow", "2026-06-25T08:00:00+00:00", "2026-06-25T09:00:00+00:00")]
    # only event is tomorrow → no "now", no "next today", no timed event today
    assert agenda.banner_text(events, NOW, UTC) is None


def test_midnight_spanning_event_with_tz():
    la = ZoneInfo("America/Los_Angeles")
    now = dt.datetime(2026, 6, 24, 7, 30, tzinfo=UTC)  # 00:30 local (PDT)
    # 23:00 prev local (06:00Z) -> 01:00 local (08:00Z)
    events = [ev("Redeye", "2026-06-24T06:00:00+00:00", "2026-06-24T08:00:00+00:00")]
    now_ev, _ = agenda.select_now_next(events, now, la)
    assert now_ev["title"] == "Redeye"
    assert agenda.banner_text(events, now, la) == "Now: Redeye until 01:00     ·     Nothing after"


def test_title_truncation():
    long = "A" * 50
    events = [ev(long, "11:30", "12:00")]
    text = agenda.banner_text(events, NOW, UTC)
    assert "…" in text and len(text) < 60
