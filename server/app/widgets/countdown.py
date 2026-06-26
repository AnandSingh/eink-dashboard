"""COUNTDOWN zone — the user's marked events with days remaining.

Bottom-left slot when BOTTOM_LEFT_WIDGET=countdown. Content is precomputed by
app.countdown.build(); this only lays it out.
"""
from .. import theme


def render(draw, box, data) -> None:
    """data = {"rows": [{"label", "days", "text"}]}"""
    x, y, w, h = box
    pad = 28
    draw.text((x + pad, y + pad), "COUNTDOWN",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    rows = data.get("rows", [])
    f = theme.font(30)
    if not rows:
        draw.text((x + pad, y + pad + 64), "No countdowns set", font=f, fill=theme.MUTED)
        return

    ty = y + pad + 64
    label_max = w - 2 * pad - 130  # leave room for the right-aligned "Nd"
    for r in rows:
        label = theme.truncate(draw, r["label"], f, label_max)
        draw.text((x + pad, ty), label, font=f, fill=theme.INK)
        tw = draw.textlength(r["text"], font=f)
        draw.text((x + w - pad - tw, ty), r["text"], font=f, fill=theme.STRONG)
        ty += 52
