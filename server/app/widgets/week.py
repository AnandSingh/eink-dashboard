"""WEEK AT A GLANCE zone — per-day activity load as mini bars."""
from .. import theme

_DAYS = ["M", "T", "W", "T", "F", "S", "S"]


def render(draw, box, data) -> None:
    """Draw a 7-day bar chart of activity load.

    data = {"load": [int]*7, "max": int}
    """
    x, y, w, h = box
    pad = 28
    draw.text((x + pad, y + pad), "WEEK AT A GLANCE",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    load = data.get("load", [0] * 7)
    mx = max(1, data.get("max", max(load) if load else 1))

    base_y = y + h - pad - 30
    chart_h = base_y - (y + pad + 64)
    slot = (w - 2 * pad) // 7
    bar_w = int(slot * 0.55)
    f = theme.font(22)
    for i in range(7):
        cx = x + pad + i * slot
        bh = int(chart_h * (load[i] / mx)) if mx else 0
        bx0 = cx + (slot - bar_w) // 2
        # bar
        if bh > 0:
            draw.rectangle([bx0, base_y - bh, bx0 + bar_w, base_y], fill=theme.INK)
        else:
            draw.line([bx0, base_y, bx0 + bar_w, base_y], fill=theme.FAINT, width=2)
        # day label
        draw.text((cx + slot // 2 - 6, base_y + 6), _DAYS[i], font=f, fill=theme.MUTED)
