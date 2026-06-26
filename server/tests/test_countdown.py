"""Unit tests for the pure countdown core — no I/O, frozen today."""
import datetime as dt

from app import countdown

TODAY = dt.date(2026, 6, 28)


def test_parse_valid():
    raw = "Trip:2026-07-19;Q3 ends:2026-09-30"
    assert countdown.parse(raw) == [
        {"label": "Trip", "date": dt.date(2026, 7, 19)},
        {"label": "Q3 ends", "date": dt.date(2026, 9, 30)},
    ]


def test_parse_skips_malformed():
    # "Trip" has no colon; "Bad:nope" has an unparseable date — both dropped.
    raw = "Trip;Bad:nope;Real:2026-08-01"
    assert countdown.parse(raw) == [{"label": "Real", "date": dt.date(2026, 8, 1)}]


def test_parse_empty_and_whitespace():
    assert countdown.parse("") == []
    assert countdown.parse("   ") == []
    assert countdown.parse(None) == []


def test_parse_label_may_contain_colon():
    # rsplit on the last ':' so labels with colons survive.
    assert countdown.parse("Q3: wrap:2026-09-30") == [
        {"label": "Q3: wrap", "date": dt.date(2026, 9, 30)},
    ]


def test_build_sorts_and_formats():
    entries = [
        {"label": "Q3 ends", "date": dt.date(2026, 9, 30)},
        {"label": "Tomorrow thing", "date": dt.date(2026, 6, 29)},
        {"label": "Today thing", "date": dt.date(2026, 6, 28)},
    ]
    assert countdown.build(entries, TODAY) == [
        {"label": "Today thing", "days": 0, "text": "today"},
        {"label": "Tomorrow thing", "days": 1, "text": "tomorrow"},
        {"label": "Q3 ends", "days": 94, "text": "94d"},
    ]


def test_build_drops_past():
    entries = [
        {"label": "Past", "date": dt.date(2026, 6, 1)},
        {"label": "Future", "date": dt.date(2026, 7, 5)},
    ]
    assert [e["label"] for e in countdown.build(entries, TODAY)] == ["Future"]


def test_build_caps_to_max():
    entries = [{"label": f"E{i}", "date": TODAY + dt.timedelta(days=i + 1)}
               for i in range(20)]
    out = countdown.build(entries, TODAY)
    assert len(out) == countdown._MAX
    assert out[0]["label"] == "E0"  # soonest kept
