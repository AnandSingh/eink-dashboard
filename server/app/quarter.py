"""Quarter progress + month weekday stats.

Pure computation, no I/O. Drawing lives in widgets/quarter.py.
"""
import calendar
import datetime as dt


def quarter_info(today: dt.date) -> dict:
    """Return {"quarter": int, "fraction": float, "days_left": int}."""
    q = (today.month - 1) // 3 + 1
    q_start = dt.date(today.year, (q - 1) * 3 + 1, 1)
    q_end_month = q * 3 + 1
    q_end_year = today.year
    if q_end_month > 12:
        q_end_month = 1
        q_end_year += 1
    q_end = dt.date(q_end_year, q_end_month, 1)
    total = (q_end - q_start).days
    elapsed = (today - q_start).days
    return {
        "quarter": q,
        "fraction": elapsed / total if total else 0.0,
        "days_left": total - elapsed,
    }


def month_weekdays(today: dt.date) -> dict:
    """Return {"month": str, "weekdays_left": int, "weekdays_total": int}.

    Weekdays = Mon–Fri. "Left" includes today if today is a weekday.
    """
    month_name = today.strftime("%B")  # full name: "June"
    cal = calendar.monthcalendar(today.year, today.month)
    total = sum(1 for week_row in cal for d in week_row[:5] if d != 0)
    left = sum(
        1 for week_row in cal for i, d in enumerate(week_row)
        if i < 5 and d != 0 and d >= today.day
    )
    return {"month": month_name, "weekdays_left": left, "weekdays_total": total}
