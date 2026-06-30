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
        ty += 34

    # consistency dots — per-habit weekly target hit/miss (last N completed weeks)
    consistency = data.get("consistency", [])
    if consistency:
        _CONS_LINE = 36
        needed = len(consistency) * _CONS_LINE + 16
        remaining = (y + h) - ty
        if remaining >= needed:
            ty += 16  # spacing from streak line
            dot_r = 4  # radius
            cf = theme.font(24)
            for row in consistency:
                # habit name
                draw.text((name_x, ty + 2), row["name"], font=cf, fill=theme.INK)
                # dots: filled = hit, outlined = miss
                dot_x = name_x + 160
                dot_cy = ty + 14
                for hit in row["weeks"]:
                    rect = [dot_x - dot_r, dot_cy - dot_r,
                            dot_x + dot_r, dot_cy + dot_r]
                    if hit:
                        draw.ellipse(rect, fill=theme.INK)
                    else:
                        draw.ellipse(rect, outline=theme.FAINT, width=2)
                    dot_x += dot_r * 2 + 8
                # hit rate right-aligned
                rate_txt = f"{row['hit_rate']}%"
                rate_w = draw.textlength(rate_txt, font=cf)
                draw.text((dot_x + 16, ty + 2), rate_txt,
                          font=cf, fill=theme.MUTED)
                ty += _CONS_LINE
