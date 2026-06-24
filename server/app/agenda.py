"""Now/Next selection + banner text for the header.

Core, not calendar-specific: reads events from the store (where the optional
calendar/ package deposits them) and decides what to show, exactly like the
renderer reads tasks/habits/goals. The core never imports calendar/.

All stored times are UTC ISO8601. "now" and "today" are evaluated in the
caller-supplied timezone so a meeting near midnight lands on the right day and
DST is handled (the tz is a stdlib zoneinfo.ZoneInfo).
"""
import datetime as dt

_TITLE_MAX = 30


def _parse(s: str) -> dt.datetime:
    """Parse a stored UTC ISO timestamp into an aware UTC datetime."""
    d = dt.datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def _today_window_utc(now: dt.datetime, tz) -> tuple[dt.datetime, dt.datetime]:
    """[start, end] of the local day containing `now`, as aware UTC datetimes."""
    local_date = now.astimezone(tz).date()
    start = dt.datetime.combine(local_date, dt.time.min, tzinfo=tz)
    end = dt.datetime.combine(local_date, dt.time.max, tzinfo=tz)
    return start.astimezone(dt.timezone.utc), end.astimezone(dt.timezone.utc)


def select_now_next(events: list[dict], now: dt.datetime, tz):
    """Return (now_event, next_event), either of which may be None.

    - now_event: a timed event with start <= now < end; on overlap, ends soonest.
    - next_event: the earliest timed event starting after `now`, still today (tz).
    All-day events are ignored (they would read as "Now" all day).
    """
    day_start, day_end = _today_window_utc(now, tz)
    timed = []
    for e in events:
        if e.get("all_day"):
            continue
        start, end = _parse(e["start_utc"]), _parse(e["end_utc"])
        timed.append((start, end, e))

    current = sorted(
        [(s, en, e) for (s, en, e) in timed if s <= now < en],
        key=lambda t: t[1],
    )
    upcoming = sorted(
        [(s, en, e) for (s, en, e) in timed if s > now and s <= day_end],
        key=lambda t: t[0],
    )
    now_ev = current[0][2] if current else None
    next_ev = upcoming[0][2] if upcoming else None
    return now_ev, next_ev


def _has_timed_today(events: list[dict], now: dt.datetime, tz) -> bool:
    day_start, day_end = _today_window_utc(now, tz)
    for e in events:
        if e.get("all_day"):
            continue
        start, end = _parse(e["start_utc"]), _parse(e["end_utc"])
        if start <= day_end and end >= day_start:
            return True
    return False


def _clip(title: str) -> str:
    title = (title or "").strip() or "(untitled)"
    return title if len(title) <= _TITLE_MAX else title[: _TITLE_MAX - 1] + "…"


def _hhmm(d_utc: dt.datetime, tz) -> str:
    return d_utc.astimezone(tz).strftime("%H:%M")


def banner_text(events: list[dict], now: dt.datetime, tz) -> str | None:
    """The Now/Next line, or None when nothing should be drawn.

    None means "no timed events today at all" → the header band is hidden.
    "No more events today" means there were events but all have ended.
    """
    now_ev, next_ev = select_now_next(events, now, tz)

    if now_ev and next_ev:
        return (f"Now: {_clip(now_ev['title'])} until {_hhmm(_parse(now_ev['end_utc']), tz)}"
                f"     ·     Next: {_clip(next_ev['title'])} at {_hhmm(_parse(next_ev['start_utc']), tz)}")
    if now_ev and not next_ev:
        return f"Now: {_clip(now_ev['title'])} until {_hhmm(_parse(now_ev['end_utc']), tz)}     ·     Nothing after"
    if next_ev:
        return f"Next: {_clip(next_ev['title'])} at {_hhmm(_parse(next_ev['start_utc']), tz)}"
    if _has_timed_today(events, now, tz):
        return "No more events today"
    return None


def has_now(events: list[dict], now: dt.datetime, tz) -> bool:
    """Whether there's a current event — the renderer draws the dot only then."""
    now_ev, _ = select_now_next(events, now, tz)
    return now_ev is not None
