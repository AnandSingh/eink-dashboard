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
