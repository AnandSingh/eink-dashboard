"""QUARTER zone — quarter progress + month weekday stats.

Bottom-left slot when BOTTOM_LEFT_WIDGET=quarter. Content is precomputed by
app.quarter; this only lays it out.
"""
from .. import theme


def render(draw, box, data) -> None:
    """data = {"quarter", "fraction", "days_left", "month", "weekdays_left", "weekdays_total"}"""
    x, y, w, h = box
    pad = 28

    # Header
    draw.text((x + pad, y + pad), "QUARTER",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    # Quarter number (large, like year in year-progress)
    draw.text((x + pad, y + pad + 70), f"Q{data['quarter']}",
              font=theme.font(96, bold=True), fill=theme.INK)

    # Progress bar (same style as render_year_progress in extras.py)
    bar_x = x + pad
    bar_y = y + pad + 200
    bar_w = w - 2 * pad
    bar_h = 34
    frac = data["fraction"]
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                   outline=theme.INK, width=3)
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * frac), bar_y + bar_h],
                   fill=theme.INK)

    # Percentage + days left
    draw.text((bar_x, bar_y + bar_h + 18),
              f"{int(frac * 100)}% · {data['days_left']} days left",
              font=theme.font(30), fill=theme.MUTED)

    # Month weekdays stat (compact single line)
    month_txt = (f"{data['month']} · {data['weekdays_left']} / "
                 f"{data['weekdays_total']} weekdays left")
    draw.text((x + pad, bar_y + bar_h + 66), month_txt,
              font=theme.font(30), fill=theme.INK)
