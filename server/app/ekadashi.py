"""Ekadashi (11th lunar day) countdown via the offline `ephem` library.

Observer-free, multi-sample approach: checks Moon–Sun elongation at four UTC
times per day (00:00, 06:00, 12:00, 18:00). If any sample falls in the
Ekadashi tithi range, the day qualifies. Consecutive qualifying days are
suppressed to return only the first.

Same pattern as moon.py — deterministic given a time, no lat/lon needed.
"""
import datetime as dt
import math

import ephem

_SHUKLA = (120, 132)   # Shukla Ekadashi — 11th waxing tithi
_KRISHNA = (300, 312)  # Krishna Ekadashi — 11th waning tithi
_SAMPLES = (0, 6, 12, 18)  # hours UTC — ~3° Moon motion between samples


def _elongation(d: ephem.Date) -> float:
    """Moon–Sun ecliptic longitude difference in degrees [0, 360)."""
    sun, m = ephem.Sun(d), ephem.Moon(d)
    return (math.degrees(ephem.Ecliptic(m).lon)
            - math.degrees(ephem.Ecliptic(sun).lon)) % 360


def _is_ekadashi(elong: float) -> bool:
    return (_SHUKLA[0] <= elong <= _SHUKLA[1]
            or _KRISHNA[0] <= elong <= _KRISHNA[1])


def _day_is_ekadashi(day: dt.date) -> bool:
    """True if any of the four daily samples falls in an Ekadashi range."""
    for h in _SAMPLES:
        d = ephem.Date(dt.datetime(day.year, day.month, day.day, h))
        if _is_ekadashi(_elongation(d)):
            return True
    return False


def next_ekadashi(now_utc: dt.datetime) -> dict | None:
    """Return {"days": int, "date": date} for the next Ekadashi, or None.

    Scans up to 33 days forward. If two consecutive days both qualify, only
    the first is returned. If today is the *second* day of a consecutive run,
    it is skipped and the next Ekadashi is found.
    """
    if isinstance(now_utc, dt.datetime):
        today = now_utc.date()
    else:
        today = now_utc  # accept bare date too
    # Pre-check yesterday to detect "today is second day of a run".
    prev_hit = _day_is_ekadashi(today - dt.timedelta(days=1))
    for offset in range(33):
        day = today + dt.timedelta(days=offset)
        hit = _day_is_ekadashi(day)
        if hit and not prev_hit:
            return {"days": offset, "date": day}
        prev_hit = hit
    return None
