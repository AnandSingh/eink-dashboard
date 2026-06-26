"""Shared look & feel for e-ink rendering: fonts + grayscale palette.

E-ink is 8-bit grayscale ("L" mode): 0 = black, 255 = white. We use a few
ink levels for hierarchy; avoid mid-greys for small text (they smear on e-ink).
"""
from functools import lru_cache

from PIL import ImageFont

# Grayscale "ink" levels
INK = 0        # primary text / borders
STRONG = 40    # headings
MUTED = 110    # secondary text
FAINT = 180    # hints, future/empty cells
BG = 255       # paper

# Font candidates (DejaVu ships in the Docker image; fall back gracefully).
_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    "DejaVuSans.ttf",
]
_FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]


@lru_cache(maxsize=64)
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = _FONT_CANDIDATES_BOLD if bold else _FONT_CANDIDATES
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def truncate(draw, text: str, font, max_w: float) -> str:
    """Trim text with an ellipsis so it fits within max_w pixels.

    Shared by the renderer and widgets; lives here (not in renderer) so widgets
    can use it without a widget→renderer back-import cycle.
    """
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"
