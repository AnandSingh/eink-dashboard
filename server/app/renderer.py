"""Compose widget zones into a single grayscale PNG sized for the Boox panel."""
import datetime as dt
import hashlib
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image, ImageDraw

from . import agenda, store, theme
from .config import config
from .widgets import today, habits, month, week, extras


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


def _calendar_tz():
    try:
        return ZoneInfo(config.calendar_tz)
    except (ZoneInfoNotFoundError, ValueError):
        return dt.timezone.utc


def _draw_header(draw, box) -> None:
    x, y, w, h = box
    pad = 28
    d = dt.date.today()
    date_txt = d.strftime("%A, %B %-d")

    # The Now/Next banner occupies a second band only when calendar is configured
    # and there's something to show; otherwise the date stays vertically centered
    # (zero visual change when the feature is off).
    banner = None
    has_now = False
    if config.calendar_ics_url:
        tz = _calendar_tz()
        now = dt.datetime.now(dt.timezone.utc)
        events = store.get_events()
        banner = agenda.banner_text(events, now, tz)
        has_now = agenda.has_now(events, now, tz)

    if banner is None:
        # Single centered band — original layout.
        date_y = y + h // 2 - 26
        right_y = y + h // 2 - 18
    else:
        # Two bands: date on top, banner beneath.
        date_y = y + 18
        right_y = y + 24

    draw.text((x + pad, date_y), date_txt,
              font=theme.font(40, bold=True), fill=theme.INK)

    # right side: weather (placeholder until integrated) + week-of-year
    woy = d.isocalendar().week
    right = f"Week {woy} / 52      --°"
    rfont = theme.font(32)
    tw = draw.textlength(right, font=rfont)
    draw.text((x + w - pad - tw, right_y), right, font=rfont, fill=theme.MUTED)

    if banner is not None:
        _draw_banner(draw, x + pad, y + 86, w - 2 * pad, banner, dot=has_now)


def _draw_banner(draw, x, y, max_w, text, dot: bool) -> None:
    """Draw the Now/Next line. The 'now' indicator is a drawn dot (font-safe);
    the text is ASCII + '·' (present in DejaVu, which the deploy ships)."""
    bfont = theme.font(30)
    cx = x
    if dot:
        r = 8
        cyc = y + 18
        draw.ellipse([cx, cyc - r, cx + 2 * r, cyc + r], fill=theme.INK)
        cx += 2 * r + 12
    # Truncate to the remaining width with an ellipsis.
    avail = x + max_w - cx
    text = _truncate(draw, text, bfont, avail)
    draw.text((cx, y), text, font=bfont, fill=theme.STRONG)


def _truncate(draw, text, font, max_w) -> str:
    if draw.textlength(text, font=font) <= max_w:
        return text
    while text and draw.textlength(text + "…", font=font) > max_w:
        text = text[:-1]
    return text + "…"


def _parse_date(s: str):
    try:
        return dt.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _render_bottom_left(draw, box, today_date, load, n_habits) -> None:
    """Dispatch the configurable bottom-left zone (week / life / weekofyear / yearprogress)."""
    choice = config.bottom_left_widget
    birth = _parse_date(config.birthdate)
    if choice == "life" and birth:
        extras.render_life_in_weeks(
            draw, box,
            {"birthdate": birth, "years": config.life_years, "today": today_date},
        )
    elif choice == "weekofyear":
        extras.render_week_of_year(draw, box, {"today": today_date})
    elif choice == "yearprogress":
        extras.render_year_progress(draw, box, {"today": today_date})
    else:
        week.render(draw, box, {"load": load, "max": max(1, n_habits)})


def _draw_footer(draw, box) -> None:
    """A thin time-awareness strip: year progress · week-of-year · life lived."""
    x, y, w, h = box
    pad = 40
    cy = y + h // 2
    today_date = dt.date.today()
    f = theme.font(26)
    fb = theme.font(26, bold=True)

    cursor = x + pad
    # year + mini progress bar
    yr = str(today_date.year)
    draw.text((cursor, cy - 16), yr, font=fb, fill=theme.INK)
    cursor += draw.textlength(yr, font=fb) + 14
    frac = extras.year_fraction(today_date)
    bar_w, bar_h = 240, 18
    by = cy - bar_h // 2
    draw.rectangle([cursor, by, cursor + bar_w, by + bar_h], outline=theme.INK, width=2)
    draw.rectangle([cursor, by, cursor + int(bar_w * frac), by + bar_h], fill=theme.INK)
    cursor += bar_w + 12
    pct = f"{int(frac * 100)}%"
    draw.text((cursor, cy - 16), pct, font=f, fill=theme.MUTED)
    cursor += draw.textlength(pct, font=f) + 40

    def segment(label):
        nonlocal cursor
        draw.text((cursor, cy - 16), "·", font=f, fill=theme.FAINT)
        cursor += draw.textlength("·", font=f) + 24
        draw.text((cursor, cy - 16), label, font=f, fill=theme.INK)
        cursor += draw.textlength(label, font=f) + 24

    woy = min(52, today_date.isocalendar().week)
    segment(f"Week {woy} / 52")

    birth = _parse_date(config.birthdate)
    if birth:
        lived_weeks = max(0, (today_date - birth).days // 7)
        total_weeks = config.life_years * 52
        segment(f"Life {int(lived_weeks / total_weeks * 100)}% · age {lived_weeks // 52}")


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

    today_date = dt.date.today()
    _draw_header(draw, zones["header"])

    habit_data = store.get_habits()
    # derive per-day week load from habit completions
    load = [sum(1 for hb in habit_data if hb["week"][i] is True) for i in range(7)]

    today.render(draw, zones["today"], {"tasks": store.get_tasks()})
    habits.render(draw, zones["habits"], {"habits": habit_data})
    _render_bottom_left(draw, zones["week"], today_date, load, len(habit_data))
    month.render(draw, zones["month"], {"goals": store.get_goals()})

    _separators(draw, zones)
    _draw_footer(draw, zones["footer"])

    img.save(config.png_path)
    return config.png_path


def render_if_changed() -> bool:
    """Render, then bump the version only if the PNG bytes actually changed.

    Lets time-driven callers (e.g. the calendar poller) re-render frequently
    without forcing needless e-ink refreshes. Returns True if the version bumped.
    """
    render()
    with open(config.png_path, "rb") as f:
        new_hash = hashlib.sha256(f.read()).hexdigest()
    if new_hash != store.get_meta("png_hash"):
        store.set_meta("png_hash", new_hash)
        store.bump_version()
        return True
    return False
