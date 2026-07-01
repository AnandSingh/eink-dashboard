"""Compose widget zones into a single grayscale PNG sized for the Boox panel."""
import datetime as dt
import hashlib
import math
import os
import threading
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PIL import Image, ImageDraw

from . import agenda, countdown, daylight, ekadashi, moon, quarter, review, store, theme, weathericons, weatherview
from .config import config
from .widgets import today, habits, month, week, extras
from .widgets import review as review_widget
from .widgets import countdown as countdown_widget
from .widgets import quarter as quarter_widget


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

    _draw_right_block(draw, x + w - pad, right_y, d.isocalendar().week)

    if banner is not None:
        _draw_banner(draw, x + pad, y + 86, w - 2 * pad, banner, dot=has_now)


_ICON_W = 40
_GAP = 18


def _draw_right_block(draw, right_x, y, woy: int) -> None:
    """Right-aligned: 'Week N / 52' then weather (icon + temp + H/L), or '--°'.

    The group contains a DRAWN icon, so it can't be right-aligned with textlength
    alone — we sum segment widths and draw left-to-right from a computed origin.
    """
    rfont = theme.font(32)
    weather = weatherview.parse(store.get_meta("weather")) if config.weather_enabled else None
    week_txt = f"Week {woy} / 52"
    week_w = draw.textlength(week_txt, font=rfont)

    if weather is None:
        # Original placeholder layout, right-aligned as one string.
        full = f"{week_txt}      --°"
        draw.text((right_x - draw.textlength(full, font=rfont), y), full,
                  font=rfont, fill=theme.MUTED)
        return

    temp_w = draw.textlength(weather["temp_txt"], font=rfont)
    hl_w = draw.textlength(weather["hl_txt"], font=rfont)
    total = week_w + _GAP + _ICON_W + _GAP + temp_w + _GAP + hl_w
    cursor = right_x - total

    draw.text((cursor, y), week_txt, font=rfont, fill=theme.MUTED)
    cursor += week_w + _GAP
    # Icon vertically centered on the 32px text's cap height (~22px from `y`).
    icon_y = y + 11 - _ICON_W // 2 + 6
    weathericons.draw(draw, (cursor, icon_y, _ICON_W, _ICON_W), weather["code"], fill=theme.INK)
    cursor += _ICON_W + _GAP
    draw.text((cursor, y), weather["temp_txt"], font=rfont, fill=theme.INK)
    cursor += temp_w + _GAP
    draw.text((cursor, y), weather["hl_txt"], font=rfont, fill=theme.MUTED)


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
    text = theme.truncate(draw, text, bfont, avail)
    draw.text((cx, y), text, font=bfont, fill=theme.STRONG)


def _parse_date(s: str):
    try:
        return dt.date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _render_bottom_left(draw, box, today_date, load, habit_data, goals) -> None:
    """Dispatch the bottom-left zone.

    On Sundays (when SUNDAY_REVIEW is on) this becomes the weekly-review view;
    otherwise the configured widget (week / life / weekofyear / yearprogress).
    """
    if config.sunday_review and today_date.weekday() == 6:  # Sunday
        monday = today_date - dt.timedelta(days=today_date.weekday())
        tasks_done = store.get_tasks_done_this_week(monday)
        rv = review.build_review(habit_data, tasks_done, goals, today_date)
        review_widget.render(draw, box, {"review": rv})
        return

    n_habits = len(habit_data)
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
    elif choice == "countdown":
        rows = countdown.build(countdown.parse(config.countdowns), today_date)
        countdown_widget.render(draw, box, {"rows": rows})
    elif choice == "quarter":
        ctx = {**quarter.quarter_info(today_date), **quarter.month_weekdays(today_date)}
        quarter_widget.render(draw, box, ctx)
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

    # Daylight segment: drawn sun/moon glyph + today's sunrise/sunset & time left.
    # Only when the weather snapshot carries sun data (graceful absence otherwise).
    if config.weather_enabled:
        sun = weatherview.parse_sun(store.get_meta("weather"))
        if sun:
            now_local = (dt.datetime.now(dt.timezone.utc)
                         + dt.timedelta(seconds=sun["utc_offset"])).replace(tzinfo=None)
            seg = daylight.segment(sun["sunrise"], sun["sunset"], now_local)
            if seg:
                text, glyph = seg
                draw.text((cursor, cy - 16), "·", font=f, fill=theme.FAINT)
                cursor += draw.textlength("·", font=f) + 22
                if glyph == "sun":
                    _sun_glyph(draw, cursor + 9, cy, 7)
                else:
                    _moon_glyph(draw, cursor + 9, cy, 8)
                cursor += 30
                draw.text((cursor, cy - 16), text, font=f, fill=theme.INK)
                cursor += draw.textlength(text, font=f) + 24

    # Moon phase segment: phase-accurate drawn glyph + named phase + illumination.
    if config.moon_enabled:
        try:
            mp = moon.phase(dt.datetime.now(dt.timezone.utc))
        except Exception:
            mp = None
        if mp:
            draw.text((cursor, cy - 16), "·", font=f, fill=theme.FAINT)
            cursor += draw.textlength("·", font=f) + 22
            _moon_phase_glyph(draw, cursor + 11, cy, 11, mp["illum"], mp["waxing"])
            cursor += 36
            draw.text((cursor, cy - 16), f"{mp['name']} {mp['illum']}%",
                      font=f, fill=theme.INK)
            cursor += draw.textlength(f"{mp['name']} {mp['illum']}%", font=f) + 24

        # Ekadashi countdown — observer-free, like the moon.phase() call above.
        try:
            ek = ekadashi.next_ekadashi(dt.datetime.now(dt.timezone.utc))
        except Exception:
            ek = None
        if ek:
            label = ("Ekadashi today" if ek["days"] == 0
                     else f"Ekadashi {ek['days']}d")
            segment(label)


def _moon_phase_glyph(draw, cx, cy, r, illum, waxing) -> None:
    """Phase-accurate moon: per-scanline terminator fill, then an outline disc.

    illum 0→empty outline, 100→filled; the lit side follows `waxing` (right when
    waxing). The terminator x at row dy is xc·(1−2k), giving the correct sliver.
    """
    k = max(0.0, min(1.0, illum / 100))
    for dy in range(-r, r + 1):
        xc = math.sqrt(max(0.0, r * r - dy * dy))
        tx = xc * (1 - 2 * k)
        x0, x1 = (tx, xc) if waxing else (-xc, -tx)
        if x1 > x0:
            draw.line([cx + x0, cy + dy, cx + x1, cy + dy], fill=theme.INK)
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=theme.INK, width=2)


def _sun_glyph(draw, cx, cy, r) -> None:
    """Small filled sun: disc + 8 short rays (font-safe primitive)."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=theme.INK)
    for i in range(8):
        a = i * math.pi / 4
        draw.line([cx + math.cos(a) * (r + 3), cy + math.sin(a) * (r + 3),
                   cx + math.cos(a) * (r + 7), cy + math.sin(a) * (r + 7)],
                  fill=theme.INK, width=2)


def _moon_glyph(draw, cx, cy, r) -> None:
    """Small crescent moon: disc with an offset BG disc carved out."""
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=theme.INK)
    draw.ellipse([cx - r + 5, cy - r, cx + r + 5, cy + r], fill=theme.BG)


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


# Serializes the render path: three daemon threads (glasses/calendar/weather) plus
# the API can all render concurrently. The public entry points hold this lock and
# call the unlocked core — they never re-acquire (so no self-deadlock).
_RENDER_LOCK = threading.Lock()


def _render_unlocked() -> str:
    """Draw the dashboard and atomically write config.png_path. Caller holds the lock."""
    img = Image.new("L", (config.panel_width, config.panel_height), color=theme.BG)
    draw = ImageDraw.Draw(img)
    zones = _zones()

    today_date = dt.date.today()
    _draw_header(draw, zones["header"])

    habit_data = store.get_habits()
    # derive per-day week load from habit completions
    load = [sum(1 for hb in habit_data if hb["week"][i] is True) for i in range(7)]

    goals = store.get_goals()
    today.render(draw, zones["today"], {"tasks": store.get_tasks()})
    consistency = store.get_habit_consistency()
    habits.render(draw, zones["habits"], {"habits": habit_data, "consistency": consistency})
    _render_bottom_left(draw, zones["week"], today_date, load, habit_data, goals)
    month.render(draw, zones["month"], {"goals": goals, "today": today_date})

    _separators(draw, zones)
    _draw_footer(draw, zones["footer"])

    # E-ink contrast pass: crisper text, less mid-grey smear on the panel.
    if config.eink_mode and config.eink_contrast != 1.0:
        img = img.point(theme.eink_lut(config.eink_contrast))

    # Atomic write: render to a temp file then rename, so a concurrent reader
    # (GET /dashboard.png) never sees a half-written PNG.
    tmp = config.png_path + ".tmp"
    img.save(tmp, format="PNG")  # explicit: the .tmp extension can't infer it
    os.replace(tmp, config.png_path)
    return config.png_path


def render() -> str:
    """Render the dashboard to config.png_path. Returns the path."""
    with _RENDER_LOCK:
        return _render_unlocked()


def render_if_changed() -> bool:
    """Render, then bump the version only if the PNG bytes actually changed.

    Lets time-driven callers (e.g. the calendar/weather pollers) re-render
    frequently without forcing needless e-ink refreshes. Returns True if bumped.
    """
    with _RENDER_LOCK:
        _render_unlocked()
        with open(config.png_path, "rb") as f:
            new_hash = hashlib.sha256(f.read()).hexdigest()
        if new_hash != store.get_meta("png_hash"):
            store.set_meta("png_hash", new_hash)
            store.bump_version()
            return True
        return False
