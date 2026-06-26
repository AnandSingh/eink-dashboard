"""Unit tests for the pure daylight segment helper — no network, naive-local clock.

Open-Meteo (timezone=auto) returns sunrise/sunset as naive-local ISO strings; the
renderer derives a naive-local 'now' from utcnow + utc_offset and passes it in.
"""
import datetime as dt

from app import daylight

SR = "2026-06-28T06:12"
SS = "2026-06-28T20:45"


def at(h, m):
    return dt.datetime(2026, 6, 28, h, m)


def test_daytime_shows_range_and_remaining():
    assert daylight.segment(SR, SS, at(16, 33)) == ("6:12–20:45 · 4h12m left", "sun")


def test_before_sunrise():
    assert daylight.segment(SR, SS, at(5, 0)) == ("rises 6:12", "sun")


def test_after_sunset():
    assert daylight.segment(SR, SS, at(21, 30)) == ("set 20:45", "moon")


def test_at_sunrise_is_daytime():
    text, glyph = daylight.segment(SR, SS, at(6, 12))
    assert glyph == "sun" and text.endswith("14h33m left")


def test_remaining_under_an_hour_drops_hours():
    text, _ = daylight.segment(SR, SS, at(20, 13))
    assert text.endswith("· 32m left")


def test_missing_or_unparseable_returns_none():
    assert daylight.segment(None, SS, at(12, 0)) is None
    assert daylight.segment(SR, None, at(12, 0)) is None
    assert daylight.segment("", "", at(12, 0)) is None
    assert daylight.segment("garbage", SS, at(12, 0)) is None


def test_tz_aware_iso_is_handled_as_local():
    # Some feeds include an offset; treat the wall-clock time as local.
    assert daylight.segment("2026-06-28T06:12+00:00", "2026-06-28T20:45+00:00",
                            at(5, 0)) == ("rises 6:12", "sun")
