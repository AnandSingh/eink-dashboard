"""WMO weather-code -> category, and font-safe drawn glyphs for the header.

Core helper: owns the code table AND the drawing. Must NOT import app/weather/
(the weather package stores only the raw integer code). Glyphs are filled INK
silhouettes, which read best on grayscale e-ink.
"""
from . import theme


def category(code: int) -> str:
    """Map a WMO weather code to a drawable category (range-based)."""
    if code == 0:
        return "clear"
    if code in (1, 2):
        return "partly"
    if code in (3, 45, 48):
        return "cloudy"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "rain"
    if 71 <= code <= 77 or code in (85, 86):
        return "snow"
    if 95 <= code <= 99:
        return "thunder"
    return "cloudy"  # safe default for unknown codes


def _sun(draw, x, y, w, h, fill, r_frac=0.30):
    cx, cy = x + w / 2, y + h / 2
    r = min(w, h) * r_frac
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    ray = r * 0.9
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1),
                   (0.7, 0.7), (-0.7, 0.7), (0.7, -0.7), (-0.7, -0.7)]:
        draw.line([cx + dx * (r + 3), cy + dy * (r + 3),
                   cx + dx * (r + 3 + ray), cy + dy * (r + 3 + ray)],
                  fill=fill, width=3)


def _cloud(draw, x, y, w, h, fill):
    """Filled cloud silhouette within the rect."""
    base_y = y + h * 0.78
    r = h * 0.30
    draw.ellipse([x, base_y - r, x + 2 * r, base_y + r * 0.7], fill=fill)            # left puff
    draw.ellipse([x + w - 2 * r, base_y - r, x + w, base_y + r * 0.7], fill=fill)    # right puff
    draw.ellipse([x + w * 0.22, y + h * 0.18, x + w * 0.82, y + h * 0.78], fill=fill)  # top puff
    draw.rectangle([x + r, base_y - r * 0.5, x + w - r, base_y + r * 0.7], fill=fill)  # base


def draw(d, box, code: int, fill=theme.INK) -> None:
    """Draw the glyph for `code` inside box=(x,y,w,h)."""
    x, y, w, h = box
    cat = category(code)

    if cat == "clear":
        _sun(d, x, y, w, h, fill, r_frac=0.34)
        return

    if cat == "partly":
        _sun(d, x, y, w * 0.6, h * 0.6, fill, r_frac=0.34)
        _cloud(d, x + w * 0.28, y + h * 0.20, w * 0.72, h * 0.72, fill)
        return

    # cloudy / rain / snow / thunder all share the cloud body
    _cloud(d, x, y, w, h * 0.78, fill)
    below_y = y + h * 0.80

    if cat == "rain":
        for i in range(3):
            sx = x + w * (0.28 + i * 0.22)
            d.line([sx, below_y, sx - w * 0.06, below_y + h * 0.18], fill=fill, width=3)
    elif cat == "snow":
        for i in range(3):
            sx = x + w * (0.28 + i * 0.22)
            r = max(2, w * 0.04)
            d.ellipse([sx - r, below_y + h * 0.04 - r, sx + r, below_y + h * 0.04 + r], fill=fill)
    elif cat == "thunder":
        cx = x + w * 0.5
        d.polygon([
            (cx + w * 0.04, below_y),
            (cx - w * 0.10, below_y + h * 0.14),
            (cx, below_y + h * 0.14),
            (cx - w * 0.06, below_y + h * 0.22),
            (cx + w * 0.12, below_y + h * 0.08),
            (cx + w * 0.02, below_y + h * 0.08),
        ], fill=fill)
