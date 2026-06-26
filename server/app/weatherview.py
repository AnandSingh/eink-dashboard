"""Pure parsing of the stored weather snapshot into header display strings.

Core display helper (like agenda.py): reads the JSON blob the optional weather/
package deposits in meta['weather']. Must NOT import app/weather/.
"""
import json


def _num(v):
    """Return v as a number, or None if missing/non-numeric."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    return None


def parse(blob: str | None) -> dict | None:
    """meta['weather'] JSON -> {temp_txt, hl_txt, code} or None if unusable.

    Returns None on missing blob, bad JSON, or any missing/non-numeric field, so
    the header falls back to the '--°' placeholder instead of showing 'H-- L--'.
    """
    if not blob:
        return None
    try:
        d = json.loads(blob)
    except (ValueError, TypeError):
        return None
    if not isinstance(d, dict):
        return None

    temp, high, low = _num(d.get("temp")), _num(d.get("high")), _num(d.get("low"))
    code = d.get("code")
    if temp is None or high is None or low is None or not isinstance(code, int):
        return None

    return {
        "temp_txt": f"{round(temp)}°",
        "hl_txt": f"H{round(high)} L{round(low)}",
        "code": code,
    }


def parse_sun(blob: str | None) -> dict | None:
    """meta['weather'] JSON -> {sunrise, sunset, utc_offset} or None.

    Independent of parse(): sunrise/sunset are optional snapshot fields, so the
    daylight footer segment can appear/disappear without affecting the header.
    """
    if not blob:
        return None
    try:
        d = json.loads(blob)
    except (ValueError, TypeError):
        return None
    if not isinstance(d, dict):
        return None
    sr, ss = d.get("sunrise"), d.get("sunset")
    if not isinstance(sr, str) or not isinstance(ss, str):
        return None
    off = d.get("utc_offset")
    return {
        "sunrise": sr,
        "sunset": ss,
        "utc_offset": off if isinstance(off, int) and not isinstance(off, bool) else 0,
    }
