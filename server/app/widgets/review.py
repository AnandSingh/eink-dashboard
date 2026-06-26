"""SUNDAY REVIEW zone — wins/misses this week + next-week focus.

Drawn into the bottom-left zone on Sundays (see renderer._render_bottom_left).
Pure layout; all content comes precomputed from app.review.build_review().
"""
import math

from .. import theme


def _star(draw, cx, cy, r, fill) -> None:
    """A small filled 5-point star primitive (font-safe; no emoji on e-ink)."""
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.42
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def render(draw, box, data) -> None:
    """Draw the weekly review.

    data = {"review": {"wins": [str], "misses": [str], "rocks": [str]}}
    """
    x, y, w, h = box
    pad = 28
    rv = data.get("review", {})
    avail = w - 2 * pad

    # Header: star + "THIS WEEK"
    _star(draw, x + pad + 12, y + pad + 16, 15, theme.STRONG)
    draw.text((x + pad + 36, y + pad), "THIS WEEK",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    bf = theme.font(30)
    ty = y + pad + 64

    def line(label, items):
        nonlocal ty
        text = f"{label}: " + (" · ".join(items) if items else "—")
        draw.text((x + pad, ty), theme.truncate(draw, text, bf, avail),
                  font=bf, fill=theme.INK)
        ty += 46

    line("Wins", rv.get("wins", []))
    line("Misses", rv.get("misses", []))

    # Divider, then the lookahead block.
    ty += 6
    draw.line([x + pad, ty, x + w - pad, ty], fill=theme.FAINT, width=2)
    ty += 22
    draw.text((x + pad, ty), "NEXT WEEK — focus",
              font=theme.font(30, bold=True), fill=theme.STRONG)
    ty += 46

    rocks = rv.get("rocks", [])
    if not rocks:
        draw.text((x + pad, ty), "Set goals to see focus", font=bf, fill=theme.MUTED)
        return
    for i, rock in enumerate(rocks, 1):
        text = theme.truncate(draw, f"{i}. {rock}", bf, avail)
        draw.text((x + pad, ty), text, font=bf, fill=theme.INK)
        ty += 42
