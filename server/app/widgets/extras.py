"""Banked add-on widgets — time-awareness / motivation.

Each is a self-contained zone widget: render(draw, box, data). Select one for
the bottom-left zone via BOTTOM_LEFT_WIDGET; year-progress + week-of-year also
feed the footer time strip (see renderer.footer_segments).
"""
import datetime as dt

from .. import theme


def year_fraction(today: dt.date) -> float:
    start = dt.date(today.year, 1, 1)
    end = dt.date(today.year + 1, 1, 1)
    return (today - start).days / ((end - start).days)


def render_year_progress(draw, box, data) -> None:
    """A big year number + progress bar + days remaining. data = {"today": date}."""
    x, y, w, h = box
    pad = 28
    today = data["today"]
    draw.text((x + pad, y + pad), "YEAR PROGRESS",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    frac = year_fraction(today)
    draw.text((x + pad, y + pad + 70), str(today.year),
              font=theme.font(96, bold=True), fill=theme.INK)

    bar_x = x + pad
    bar_y = y + pad + 200
    bar_w = w - 2 * pad
    bar_h = 34
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], outline=theme.INK, width=3)
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * frac), bar_y + bar_h], fill=theme.INK)

    days_left = (dt.date(today.year + 1, 1, 1) - today).days
    draw.text((bar_x, bar_y + bar_h + 18),
              f"{int(frac * 100)}% · {days_left} days left",
              font=theme.font(30), fill=theme.MUTED)


def render_week_of_year(draw, box, data) -> None:
    """52-week dot grid, weeks elapsed filled. data = {"today": date}."""
    x, y, w, h = box
    pad = 28
    today = data["today"]
    woy = min(52, today.isocalendar().week)
    draw.text((x + pad, y + pad), "WEEK OF THE YEAR",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    cols, rows = 13, 4
    grid_top = y + pad + 70
    avail_w = w - 2 * pad
    avail_h = (y + h - pad - 60) - grid_top
    pitch = max(8, int(min(avail_w / cols, avail_h / rows)))
    cell = pitch - 8 if pitch > 16 else max(6, pitch - 4)

    for i in range(52):
        r, c = divmod(i, cols)
        x0 = x + pad + c * pitch
        y0 = grid_top + r * pitch
        rect = [x0, y0, x0 + cell, y0 + cell]
        if i + 1 < woy:
            draw.rectangle(rect, fill=theme.INK)
        elif i + 1 == woy:
            draw.rectangle(rect, outline=theme.INK, width=4)
        else:
            draw.rectangle(rect, outline=theme.FAINT, width=2)

    draw.text((x + pad, y + h - pad - 44), f"Week {woy} / 52",
              font=theme.font(34, bold=True), fill=theme.INK)


def render_life_in_weeks(draw, box, data) -> None:
    """The classic life calendar: one dot per week of a ~N-year life.

    data = {"birthdate": date, "years": int, "today": date}
    """
    x, y, w, h = box
    pad = 28
    birth = data["birthdate"]
    years = data["years"]
    today = data["today"]
    weeks = 52

    draw.text((x + pad, y + pad), "LIFE IN WEEKS",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    grid_top = y + pad + 56
    avail_w = w - 2 * pad
    avail_h = (y + h - pad - 44) - grid_top
    pitch = max(3, int(min(avail_w / weeks, avail_h / years)))
    dot = max(2, pitch - 2)  # ~2px gap so the grid reads as individual weeks
    grid_w = weeks * pitch
    start_x = x + (w - grid_w) // 2  # center horizontally in the zone

    lived = max(0, (today - birth).days // 7)
    total = years * weeks
    for i in range(total):
        r, c = divmod(i, weeks)
        x0 = start_x + c * pitch
        y0 = grid_top + r * pitch
        rect = [x0, y0, x0 + dot, y0 + dot]
        if i < lived:
            draw.rectangle(rect, fill=theme.INK)         # weeks lived
        elif i == lived:
            draw.rectangle(rect, fill=theme.MUTED)       # this week
        else:
            draw.rectangle(rect, fill=theme.FAINT)       # weeks ahead

    age_years = lived // weeks
    draw.text((x + pad, y + h - pad - 32),
              f"Year {age_years} of {years}  ·  {int(lived / total * 100)}% lived",
              font=theme.font(26), fill=theme.MUTED)
