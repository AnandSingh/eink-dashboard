"""Compose widget zones into a single grayscale PNG sized for the Boox panel."""
from PIL import Image, ImageDraw

from .config import config
from .widgets import today, habits, month


def _zones():
    """Return zone boxes (x, y, w, h) for the 3-horizon layout.

    Header across the top, then a 2x2 grid: today | habits / week | month.
    """
    W, H = config.panel_width, config.panel_height
    header_h = int(H * 0.10)
    body_y = header_h
    body_h = H - header_h
    col_w = W // 2
    row_h = body_h // 2
    return {
        "header": (0, 0, W, header_h),
        "today": (0, body_y, col_w, row_h),
        "habits": (col_w, body_y, col_w, row_h),
        "week": (0, body_y + row_h, col_w, row_h),
        "month": (col_w, body_y + row_h, col_w, row_h),
    }


def render() -> str:
    """Render the dashboard to config.png_path. Returns the path.

    "L" mode = 8-bit grayscale, the right space for e-ink.
    TODO: gather data from store, draw header + each widget into its zone.
    """
    img = Image.new("L", (config.panel_width, config.panel_height), color=255)
    draw = ImageDraw.Draw(img)
    zones = _zones()

    # TODO: draw header (date, weather, day bounds) into zones["header"].
    # TODO: today.render(draw, zones["today"], data)
    # TODO: habits.render(draw, zones["habits"], data)
    # TODO: month.render(draw, zones["month"], data)
    _ = (today, habits, month)  # referenced once implemented

    img.save(config.png_path)
    return config.png_path
