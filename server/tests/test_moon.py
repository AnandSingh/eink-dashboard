"""Tests for the moon-phase helper. Uses ephem's own phase events as ground
truth to validate our naming / illumination / waxing glue (deterministic)."""
import ephem

from app import moon


def test_full_moon():
    p = moon.phase(ephem.next_full_moon("2026/06/01").datetime())
    assert p["name"] == "Full"
    assert p["illum"] >= 99


def test_new_moon():
    p = moon.phase(ephem.next_new_moon("2026/06/01").datetime())
    assert p["name"] == "New"
    assert p["illum"] <= 1


def test_first_quarter_is_waxing_half():
    p = moon.phase(ephem.next_first_quarter_moon("2026/06/01").datetime())
    assert p["name"] == "First Quarter"
    assert p["waxing"] is True
    assert 47 <= p["illum"] <= 53


def test_last_quarter_is_waning_half():
    p = moon.phase(ephem.next_last_quarter_moon("2026/06/01").datetime())
    assert p["name"] == "Last Quarter"
    assert p["waxing"] is False
    assert 47 <= p["illum"] <= 53


def test_waxing_gibbous_between_fq_and_full():
    # Midpoint between first quarter and the following full moon is gibbous & waxing.
    fq = ephem.next_first_quarter_moon("2026/06/01")
    fm = ephem.next_full_moon(fq)
    mid = ephem.Date((float(fq) + float(fm)) / 2)
    p = moon.phase(mid.datetime())
    assert p["name"] == "Waxing Gibbous"
    assert p["waxing"] is True


def test_accepts_tz_aware_datetime():
    import datetime as dt
    fm = ephem.next_full_moon("2026/06/01").datetime().replace(tzinfo=dt.timezone.utc)
    assert moon.phase(fm)["name"] == "Full"
