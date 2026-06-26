"""Moon phase via the offline `ephem` astronomy library.

phase(now_utc) -> {name, illum, waxing}. Deterministic given a time, so the
footer can compute it at render time and tests can pin known phase instants.
The drawing (a phase-accurate glyph) lives in renderer._draw_footer.
"""
import datetime as dt
import math

import ephem

# 8 phases, 45°-wide buckets centered on elongation 0 / 45 / … / 315.
_NAMES = [
    "New", "Waxing Crescent", "First Quarter", "Waxing Gibbous",
    "Full", "Waning Gibbous", "Last Quarter", "Waning Crescent",
]


def _to_utc_naive(when: dt.datetime) -> dt.datetime:
    """ephem treats datetimes as UTC; normalize aware ones and drop tzinfo."""
    if when.tzinfo is not None:
        when = when.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return when


def phase(now_utc: dt.datetime) -> dict:
    """Return {name, illum (0–100 % illuminated), waxing (bool)}."""
    d = ephem.Date(_to_utc_naive(now_utc))
    sun, m = ephem.Sun(d), ephem.Moon(d)
    elong = (math.degrees(ephem.Ecliptic(m).lon)
             - math.degrees(ephem.Ecliptic(sun).lon)) % 360
    idx = int(((elong + 22.5) % 360) // 45)
    return {"name": _NAMES[idx], "illum": round(m.phase), "waxing": elong < 180}
