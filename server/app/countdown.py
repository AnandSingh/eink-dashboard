"""Pure core for the countdown widget.

Parses the user's COUNTDOWNS config ("label:YYYY-MM-DD;…") and computes the
soonest-first list of upcoming events with days remaining. No I/O → unit-tested
in tests/test_countdown.py. Drawing lives in widgets/countdown.py.
"""
import datetime as dt

_MAX = 8  # rows that fit the bottom-left zone


def parse(raw: str | None) -> list[dict]:
    """"label:YYYY-MM-DD;…" -> [{label, date}], skipping malformed entries."""
    if not raw:
        return []
    out = []
    for chunk in raw.split(";"):
        chunk = chunk.strip()
        if ":" not in chunk:
            continue
        label, date_str = chunk.rsplit(":", 1)  # labels may contain ':'
        label = label.strip()
        try:
            d = dt.date.fromisoformat(date_str.strip())
        except (ValueError, TypeError):
            continue
        if label:
            out.append({"label": label, "date": d})
    return out


def _fmt(days: int) -> str:
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"{days}d"


def build(entries: list[dict], today: dt.date) -> list[dict]:
    """Soonest-first upcoming events: drop past, sort, format, cap to _MAX."""
    rows = []
    for e in entries:
        days = (e["date"] - today).days
        if days < 0:
            continue
        rows.append({"label": e["label"], "days": days, "text": _fmt(days)})
    rows.sort(key=lambda r: r["days"])
    return rows[:_MAX]
