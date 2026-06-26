"""Resolve location + fetch weather from Open-Meteo.

Pure parsers (parse_ipapi / parse_forecast) are unit-tested without network; the
impure helpers do the HTTP and the location caching.
"""
import datetime as dt
import json
import logging
import urllib.parse
import urllib.request

from ..config import config
from .. import store

log = logging.getLogger(__name__)

_TIMEOUT = 15
_IPAPI_URL = "http://ip-api.com/json"
_OPEN_METEO = "https://api.open-meteo.com/v1/forecast"
_LOC_TTL = dt.timedelta(days=7)


# --- pure parsers --------------------------------------------------------

def _num(v):
    if isinstance(v, bool):
        return None
    return v if isinstance(v, (int, float)) else None


def parse_ipapi(d: dict) -> dict | None:
    """ip-api.com JSON -> {lat, lon, city} or None."""
    if not isinstance(d, dict) or d.get("status") != "success":
        return None
    lat, lon = _num(d.get("lat")), _num(d.get("lon"))
    if lat is None or lon is None:
        return None
    return {"lat": float(lat), "lon": float(lon), "city": str(d.get("city", ""))}


def parse_forecast(d: dict) -> dict | None:
    """Open-Meteo JSON -> {temp, high, low, code} or None (defensive on shape)."""
    if not isinstance(d, dict):
        return None
    cur = d.get("current") or {}
    daily = d.get("daily") or {}
    temp = _num(cur.get("temperature_2m"))
    code = cur.get("weather_code")
    highs = daily.get("temperature_2m_max") or []
    lows = daily.get("temperature_2m_min") or []
    if temp is None or not isinstance(code, int):
        return None
    if not isinstance(highs, list) or not isinstance(lows, list) or not highs or not lows:
        return None
    high, low = _num(highs[0]), _num(lows[0])
    if high is None or low is None:
        return None
    out = {"temp": float(temp), "high": float(high), "low": float(low), "code": int(code)}

    # Optional: today's sunrise/sunset (naive-local ISO when timezone=auto) plus the
    # location's UTC offset, so the footer can compute daylight-remaining. Additive —
    # absence just omits the footer segment; never fails the core weather parse.
    sr = daily.get("sunrise") or []
    ss = daily.get("sunset") or []
    if (isinstance(sr, list) and sr and isinstance(sr[0], str)
            and isinstance(ss, list) and ss and isinstance(ss[0], str)):
        off = d.get("utc_offset_seconds")
        out["sunrise"] = sr[0]
        out["sunset"] = ss[0]
        out["utc_offset"] = int(off) if isinstance(off, int) and not isinstance(off, bool) else 0
    return out


# --- impure: http + caching ---------------------------------------------

def _get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "eink-dashboard"})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _manual_override() -> dict | None:
    try:
        return {"lat": float(config.weather_lat), "lon": float(config.weather_lon), "city": ""}
    except (ValueError, TypeError):
        return None


def _read_cached_location() -> dict | None:
    try:
        d = json.loads(store.get_meta("weather_loc") or "")
    except (ValueError, TypeError):
        return None
    return d if isinstance(d, dict) and "lat" in d and "lon" in d else None


def _fresh(cached: dict) -> bool:
    try:
        ts = dt.datetime.fromisoformat(cached["ts"])
    except (KeyError, ValueError, TypeError):
        return False
    return dt.datetime.now(dt.timezone.utc) - ts < _LOC_TTL


def resolve_location() -> dict | None:
    """Manual override > fresh cache > IP geolocation > stale cache (or None)."""
    override = _manual_override()
    if override:
        return override

    cached = _read_cached_location()
    if cached and _fresh(cached):
        return cached

    try:
        loc = parse_ipapi(_get_json(_IPAPI_URL))
        if loc:
            loc_to_cache = {**loc, "ts": dt.datetime.now(dt.timezone.utc).isoformat()}
            store.set_meta("weather_loc", json.dumps(loc_to_cache))
            return loc
    except Exception:
        log.exception("IP geolocation failed; falling back to cached location")
    return cached  # may be stale, or None if we never resolved one


def fetch_snapshot() -> dict | None:
    """Resolve location + fetch forecast -> snapshot dict, or None on failure."""
    loc = resolve_location()
    if not loc:
        log.warning("no weather location available; skipping")
        return None
    units = "celsius" if config.weather_units.lower().startswith("c") else "fahrenheit"
    qs = urllib.parse.urlencode({
        "latitude": loc["lat"], "longitude": loc["lon"],
        "current": "temperature_2m,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,sunrise,sunset",
        "temperature_unit": units, "timezone": "auto",
    })
    parsed = parse_forecast(_get_json(f"{_OPEN_METEO}?{qs}"))
    if parsed is None:
        return None
    return {
        **parsed,
        "city": loc.get("city", ""),
        "updated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
