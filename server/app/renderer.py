"""Compose widget zones into a single grayscale PNG sized for the Boox panel."""
import datetime as dt

from PIL import Image, ImageDraw

from . import store, theme
from .config import config
from .widgets import today, habits, month, week


def _zones():
    """Return zone boxes (x, y, w, h) for the 3-horizon layout.

    Header across the top, then a 2x2 grid: today | habits / week | month,
    with a thin footer for the daily focus line.
    """
    W, H = config.panel_width, config.panel_height
    header_h = int(H * 0.10)
    footer_h = int(H * 0.06)
    body_y = header_h
    body_h = H - header_h - footer_h
    col_w = W // 2
    row_h = body_h // 2
    return {
        "header": (0, 0, W, header_h),
        "today": (0, body_y, col_w, row_h),
        "habits": (col_w, body_y, col_w, row_h),
        "week": (0, body_y + row_h, col_w, row_h),
        "month": (col_w, body_y + row_h, col_w, row_h),
        "footer": (0, H - footer_h, W, footer_h),
    }


def _draw_header(draw, box) -> None:
    x, y, w, h = box
    pad = 28
    d = dt.date.today()
    date_txt = d.strftime("%A, %B %-d")
    draw.text((x + pad, y + h // 2 - 26), date_txt,
              font=theme.font(46, bold=True), fill=theme.INK)

    # right side: weather (placeholder until integrated) + week-of-year
    woy = d.isocalendar().week
    right = f"Week {woy} / 52      ☀ --°"
    tw = draw.textlength(right, font=theme.font(34))
    draw.text((x + w - pad - tw, y + h // 2 - 18), right,
              font=theme.font(34), fill=theme.MUTED)


def _draw_footer(draw, box) -> None:
    x, y, w, h = box
    quote = "“What gets scheduled gets done.”"
    f = theme.font(28)
    tw = draw.textlength(quote, font=f)
    draw.text((x + (w - tw) // 2, y + h // 2 - 16), quote, font=f, fill=theme.MUTED)


def _separators(draw, zones) -> None:
    """Thin grid lines between zones."""
    W = config.panel_width
    hx, hy, hw, hh = zones["header"]
    draw.line([0, hh, W, hh], fill=theme.INK, width=2)
    # vertical split of the body
    tx, ty, tw_, th = zones["today"]
    bx, by, bw, bh = zones["month"]
    draw.line([tw_, ty, tw_, by + bh], fill=theme.FAINT, width=2)
    # horizontal split between rows
    wx, wy, ww, wh = zones["week"]
    draw.line([0, wy, W, wy], fill=theme.FAINT, width=2)
    # footer line
    fx, fy, fw, fh = zones["footer"]
    draw.line([0, fy, W, fy], fill=theme.FAINT, width=2)


def render() -> str:
    """Render the dashboard to config.png_path. Returns the path."""
    img = Image.new("L", (config.panel_width, config.panel_height), color=theme.BG)
    draw = ImageDraw.Draw(img)
    zones = _zones()

    _draw_header(draw, zones["header"])

    habit_data = store.get_habits()
    # derive per-day week load from habit completions
    load = [sum(1 for hb in habit_data if hb["week"][i] is True) for i in range(7)]

    today.render(draw, zones["today"], {"tasks": store.get_tasks()})
    habits.render(draw, zones["habits"], {"habits": habit_data})
    week.render(draw, zones["week"], {"load": load, "max": max(1, len(habit_data))})
    month.render(draw, zones["month"], {"goals": store.get_goals()})

    _separators(draw, zones)
    _draw_footer(draw, zones["footer"])

    img.save(config.png_path)
    return config.png_path
