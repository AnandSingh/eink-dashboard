"""HABITS zone — weekly habit grid + streaks."""
from .. import theme

_DAYS = ["M", "T", "W", "T", "F", "S", "S"]


def render(draw, box, data) -> None:
    """Draw the habit grid (filled = done, outline = missed, faint = future).

    data = {"habits": [{"name", "week":[bool|None]*7, "done", "target", "streak"}]}
    """
    x, y, w, h = box
    pad = 28
    draw.text((x + pad, y + pad), "HABITS  ·  this week",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    habits = data.get("habits", [])
    name_x = x + pad
    grid_x = x + pad + 230
    cell = 34
    gap = 12
    line_h = 58
    ty = y + pad + 64

    # day-of-week header above the grid
    hf = theme.font(20)
    for i, d in enumerate(_DAYS):
        cx = grid_x + i * (cell + gap)
        draw.text((cx + cell // 3, ty - 30), d, font=hf, fill=theme.MUTED)

    f = theme.font(30)
    sf = theme.font(24)
    for hb in habits:
        draw.text((name_x, ty + 2), hb["name"], font=f, fill=theme.INK)
        for i, state in enumerate(hb["week"]):
            cx = grid_x + i * (cell + gap)
            rect = [cx, ty, cx + cell, ty + cell]
            if state is True:
                draw.rectangle(rect, fill=theme.INK)
            elif state is False:
                draw.rectangle(rect, outline=theme.INK, width=3)
            else:  # future
                draw.rectangle(rect, outline=theme.FAINT, width=2)
        # progress count
        tgt = hb.get("target")
        label = f"{hb['done']}/{tgt}" if tgt else str(hb["done"])
        draw.text((grid_x + 7 * (cell + gap) + 10, ty + 4), label,
                  font=sf, fill=theme.MUTED)
        ty += line_h

    # streaks line
    streaks = [f"{hb['name']} {hb['streak']}d" for hb in habits if hb["streak"] >= 2]
    if streaks:
        draw.text((name_x, ty + 8), "STREAK  " + "   ".join(streaks),
                  font=theme.font(26, bold=True), fill=theme.STRONG)
