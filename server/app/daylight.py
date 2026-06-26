"""Pure helper: format today's daylight as a footer segment.

Given sunrise/sunset (naive-local ISO strings from Open-Meteo) and a naive-local
'now', return (text, glyph) where glyph is "sun" (day / pre-dawn) or "moon"
(after sunset), or None when the data is missing/unparseable (so the footer
gracefully omits the segment). No I/O → unit-tested in tests/test_daylight.py.
"""
import datetime as dt


def _parse(s: str | None) -> dt.datetime | None:
    """Parse an ISO timestamp, treating its wall-clock time as local (drop tz)."""
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s).replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def _hm(t: dt.datetime) -> str:
    return f"{t.hour}:{t.minute:02d}"


def _dur(delta: dt.timedelta) -> str:
    total_min = max(0, int(delta.total_seconds() // 60))
    h, m = divmod(total_min, 60)
    return f"{h}h{m:02d}m" if h else f"{m}m"


def segment(sunrise: str | None, sunset: str | None,
            now_local: dt.datetime) -> tuple[str, str] | None:
    sr, ss = _parse(sunrise), _parse(sunset)
    if sr is None or ss is None or ss <= sr:  # missing or polar day/night
        return None
    if now_local < sr:
        return (f"rises {_hm(sr)}", "sun")
    if now_local >= ss:
        return (f"set {_hm(ss)}", "moon")
    return (f"{_hm(sr)}–{_hm(ss)} · {_dur(ss - now_local)} left", "sun")
