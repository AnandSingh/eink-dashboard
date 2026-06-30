# Phase 11: Ekadashi Countdown + Quarter Progress — Design (v2)

**Date:** 2026-06-30
**Status:** Designed
**Author:** Anand (with Claude)

## Changes from previous version

| # | Issue | What changed |
|---|-------|-------------|
| C1 | Elongation range misses Ekadashis (sunrise-only sample skips tithis that start and end between consecutive sunrises) | Dropped Observer/sunrise entirely. Now sample elongation at **four fixed UTC times** per day (00:00, 06:00, 12:00, 18:00) — if *any* sample falls in the 120-132 / 300-312 range, the day qualifies. This catches tithis that transit the window between sunrises while staying simple and deterministic. Also eliminates the lat/lon dependency (solves C3 and S2 simultaneously). |
| C2 | Footer cursor not advanced after moon phase text — Ekadashi text would overlap | Design now documents this as a **pre-existing bug fix**: advance `cursor` after drawing the moon phase name+illum text, before the new Ekadashi segment. |
| C3 | `next_ekadashi` API takes `lat, lon` but they may be empty strings | Eliminated: the observer-free approach uses only `ephem.Date` + `ephem.Sun`/`ephem.Moon` (same pattern as `moon.py`). No lat/lon parameters in the API at all. |
| S1 | `now_utc` variable doesn't exist in `_draw_footer` | Renderer snippet now uses `dt.datetime.now(dt.timezone.utc)` inline, consistent with the moon phase call on the same line. |
| S3 | Double-detection on consecutive days (e.g., May 25-26) | Multi-sample approach makes doubles more likely; addressed by returning only the **first day** of any consecutive run. `next_ekadashi` scans forward and, when it finds a qualifying day, checks whether the *previous* day also qualified — if so, skips to the next qualifying day. |
| S4 | Quarter widget density — check actual zone size | Measured: zone is ~1280x330px at default 2560x1440. Removed the thin separator and merged month weekdays into a single compact stat line below the quarter progress bar. Layout now uses the same vertical density as `render_year_progress()`. |
| S5 | Month name format inconsistency (`month` returns "Jun" but widget shows "June") | `month_weekdays()` now returns the **full** month name ("June"). Widget uses it directly. |
| S6 | Import pattern alignment | Design now shows `from .widgets import quarter as quarter_widget`, matching the existing `countdown` import pattern. |

## Goal

Two additions to the dashboard:

1. **Ekadashi countdown** — a footer segment showing days until the next Ekadashi,
   computed offline from `ephem` (no `.ics` feed, no network dependency).
2. **Quarter progress + weekdays left** — a bottom-left widget showing quarter
   progress bar + weekdays remaining in the current month.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Ekadashi source | Compute tithi from `ephem` | Fully offline; `ephem` already installed (phase 10); avoids separate `.ics` feed, sync daemon, and storage table. |
| Ekadashi computation | Observer-free, multi-sample (4 UTC times/day) | Matches `moon.py` pattern. No lat/lon dependency, no sunrise computation. Four samples per day catches tithis that transit the 12-degree window between any two consecutive checks. |
| Ekadashi accuracy | ~24/24 per year vs. Drik Panchang, with possible +/-1 day on 1-2 boundary cases | Multi-sample approach eliminates the missed-Ekadashi gap. For a "days until" countdown, +/-1 day on a rare boundary case is acceptable. |
| Double-day suppression | Return only the first day of a consecutive run | Prevents "Ekadashi today" from showing two days in a row. |
| Ekadashi display | "Ekadashi 3d" / "Ekadashi today" — minimal, next one only | User wants it uncluttered. No Shukla/Krishna qualifier, no glyph. |
| Ekadashi placement | Footer segment after moon phase | Lunar concept pairs naturally with moon phase; uses the `segment()` cursor pattern. |
| Ekadashi config | Gated on `MOON_ENABLED` | Both are lunar; rarely want one without the other. No new env var. |
| Quarter/weekdays placement | Bottom-left widget (`BOTTOM_LEFT_WIDGET=quarter`) | Footer is already dense (6+ segments after Ekadashi). A widget zone gives room for a visual progress bar. |
| Workdays vs weekdays | Weekdays (Mon-Fri) only | Pure compute, no holiday calendar dependency. Good enough for a glance. |

## Architecture

### A. Ekadashi countdown

#### `app/ekadashi.py` — pure helper (sibling to `moon.py`, `daylight.py`)

**API:**

```python
def next_ekadashi(now_utc: dt.datetime) -> dict | None:
    """Return {"days": int, "date": date} for the next Ekadashi, or None."""
```

No `lat`/`lon` parameters. Observer-free, like `moon.py`.

**Algorithm:**

1. For each day from `today` up to `today + 32` days:
   a. Compute Moon-Sun elongation at **four UTC times**: 00:00, 06:00, 12:00, 18:00.
   b. If *any* of the four samples has elongation in 120-132 (Shukla) or 300-312 (Krishna), mark the day as an Ekadashi candidate.
2. Collect all candidates into a list.
3. **Consecutive-run filter**: walk the candidates; if a candidate's previous calendar day is also a candidate, skip it (keep only the first day of each run).
4. Return the first remaining candidate: `{"days": (date - today).days, "date": date}`.
5. Return `None` if no candidate in the 32-day window (should not happen; max gap is ~15 days).

**Why four samples works**: The Moon gains ~12-13 degrees of elongation per day. A 12-degree tithi window that starts after one sample and ends before the next could be missed if sampling only once. With 6-hour intervals, the Moon moves ~3 degrees between samples — well under the 12-degree window width, so at least one sample always lands inside.

**Implementation pattern** (follows `moon.py`):

```python
import datetime as dt
import math
import ephem

_SHUKLA = (120, 132)
_KRISHNA = (300, 312)
_SAMPLES_PER_DAY = [0, 6, 12, 18]  # hours UTC


def _elongation(d: ephem.Date) -> float:
    sun, m = ephem.Sun(d), ephem.Moon(d)
    return (math.degrees(ephem.Ecliptic(m).lon)
            - math.degrees(ephem.Ecliptic(sun).lon)) % 360


def _is_ekadashi(elong: float) -> bool:
    return (_SHUKLA[0] <= elong <= _SHUKLA[1]
            or _KRISHNA[0] <= elong <= _KRISHNA[1])


def _day_is_ekadashi(day: dt.date) -> bool:
    for h in _SAMPLES_PER_DAY:
        d = ephem.Date(dt.datetime(day.year, day.month, day.day, h))
        if _is_ekadashi(_elongation(d)):
            return True
    return False


def next_ekadashi(now_utc: dt.datetime) -> dict | None:
    today = now_utc.date() if isinstance(now_utc, dt.datetime) else now_utc
    prev_was_ekadashi = False
    for offset in range(33):
        day = today + dt.timedelta(days=offset)
        if _day_is_ekadashi(day):
            if prev_was_ekadashi:
                # second day of a consecutive run — skip it
                continue
            return {"days": offset, "date": day}
        prev_was_ekadashi = _day_is_ekadashi(day)  # never True here
        prev_was_ekadashi = False
    return None
```

Wait — the consecutive-run logic above has a flaw: `prev_was_ekadashi` is reset to False in the `else` branch, so it cannot track properly. Here is the corrected logic:

```python
def next_ekadashi(now_utc: dt.datetime) -> dict | None:
    today = now_utc.date() if isinstance(now_utc, dt.datetime) else now_utc
    prev_hit = False
    for offset in range(33):
        day = today + dt.timedelta(days=offset)
        hit = _day_is_ekadashi(day)
        if hit and not prev_hit:
            return {"days": offset, "date": day}
        prev_hit = hit
    return None
```

This returns the *first* day of each consecutive run. If today is already the second day of a run (e.g., yesterday was Ekadashi, today still reads in-range), it correctly skips today and finds the *next* Ekadashi. Edge case: if `offset == 0` is hit, `prev_hit` is False (initialized), so "Ekadashi today" works correctly for the first day.

Special case for `offset == 0`: we do not have yesterday's data in the forward scan. To handle this, we pre-check whether yesterday was also Ekadashi:

```python
def next_ekadashi(now_utc: dt.datetime) -> dict | None:
    today = now_utc.date() if isinstance(now_utc, dt.datetime) else now_utc
    # Check if yesterday was Ekadashi to detect "today is second day of a run"
    prev_hit = _day_is_ekadashi(today - dt.timedelta(days=1))
    for offset in range(33):
        day = today + dt.timedelta(days=offset)
        hit = _day_is_ekadashi(day)
        if hit and not prev_hit:
            return {"days": offset, "date": day}
        prev_hit = hit
    return None
```

This is the final algorithm. Cost: up to 34 days x 4 samples = 136 `ephem` evaluations per call. Each is sub-millisecond; total is well under 100ms.

#### Renderer — in `_draw_footer()`, after the moon phase segment

**Bug fix (C2):** First, advance the cursor after the existing moon phase text. This is a pre-existing omission that is harmless today (nothing follows the moon segment) but becomes a bug the moment Ekadashi is added.

```python
# Moon phase segment (existing code, lines 248-249)
draw.text((cursor, cy - 16), f"{mp['name']} {mp['illum']}%",
          font=f, fill=theme.INK)
# BUG FIX: advance cursor past the moon phase text
cursor += draw.textlength(f"{mp['name']} {mp['illum']}%", font=f) + 24
```

**New Ekadashi segment** (immediately after, still inside `if config.moon_enabled` and `if mp`):

```python
        # Ekadashi countdown — observer-free, like the moon.phase() call above.
        try:
            ek = ekadashi.next_ekadashi(dt.datetime.now(dt.timezone.utc))
        except Exception:
            ek = None
        if ek:
            label = "Ekadashi today" if ek["days"] == 0 else f"Ekadashi {ek['days']}d"
            segment(label)
```

Notes:
- Uses `dt.datetime.now(dt.timezone.utc)` inline (S1 fix — no `now_utc` variable exists in `_draw_footer`).
- Wrapped in `try/except` matching the defensive pattern used for `moon.phase()` on line 241.
- Placed inside the `if mp:` block so the Ekadashi segment only appears when the moon phase segment is also drawn (lunar concepts pair together).

**Import:** Add `from . import ekadashi` to the import block at the top of `renderer.py`, alongside the existing `from . import … moon …` import.

### B. Quarter progress + weekdays left

#### `app/quarter.py` — pure helper (sibling to `countdown.py`)

```python
"""Quarter progress + month weekday stats.

Pure computation, no I/O. Drawing lives in widgets/quarter.py.
"""
import calendar
import datetime as dt


def quarter_info(today: dt.date) -> dict:
    """Return {"quarter": int, "fraction": float, "days_left": int}."""
    q = (today.month - 1) // 3 + 1
    q_start_month = (q - 1) * 3 + 1
    q_start = dt.date(today.year, q_start_month, 1)
    q_end_month = q * 3 + 1
    q_end_year = today.year
    if q_end_month > 12:
        q_end_month = 1
        q_end_year += 1
    q_end = dt.date(q_end_year, q_end_month, 1)
    total = (q_end - q_start).days
    elapsed = (today - q_start).days
    return {
        "quarter": q,
        "fraction": elapsed / total if total else 0.0,
        "days_left": total - elapsed,
    }


def month_weekdays(today: dt.date) -> dict:
    """Return {"month": str, "weekdays_left": int, "weekdays_total": int}."""
    month_name = today.strftime("%B")  # full name: "June", not "Jun"
    cal = calendar.monthcalendar(today.year, today.month)
    total = sum(1 for week_row in cal for d in week_row[:5] if d != 0)
    left = sum(
        1 for week_row in cal for i, d in enumerate(week_row)
        if i < 5 and d != 0 and d >= today.day
    )
    return {"month": month_name, "weekdays_left": left, "weekdays_total": total}
```

#### `app/widgets/quarter.py` — `render(draw, box, ctx)`

Layout (fits the ~1280x330px bottom-left zone, verified against `render_year_progress` which uses roughly half the vertical space):

```
QUARTER                             (header, themed like "COUNTDOWN")

Q3                                  (large bold, like year-progress year number)
[████████████░░░░░░░░] 41%          (progress bar, year-progress style)
38 days left                        (muted subtext)

June · 7 / 22 weekdays left        (compact month stat, no separator needed)
```

No thin separator between quarter and month — the sections are visually distinct via the progress bar without one (S4 fix). The month stat is a single line using the bullet separator pattern from the footer.

```python
"""QUARTER zone — quarter progress + month weekday stats.

Bottom-left slot when BOTTOM_LEFT_WIDGET=quarter. Content is precomputed by
app.quarter; this only lays it out.
"""
from .. import theme


def render(draw, box, data) -> None:
    """data = {"quarter", "fraction", "days_left", "month", "weekdays_left", "weekdays_total"}"""
    x, y, w, h = box
    pad = 28

    # Header
    draw.text((x + pad, y + pad), "QUARTER",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    # Quarter number (large, like year in year-progress)
    q_label = f"Q{data['quarter']}"
    draw.text((x + pad, y + pad + 70), q_label,
              font=theme.font(96, bold=True), fill=theme.INK)

    # Progress bar (same style as render_year_progress)
    bar_x = x + pad
    bar_y = y + pad + 200
    bar_w = w - 2 * pad
    bar_h = 34
    frac = data["fraction"]
    draw.rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
                   outline=theme.INK, width=3)
    draw.rectangle([bar_x, bar_y, bar_x + int(bar_w * frac), bar_y + bar_h],
                   fill=theme.INK)

    # Days left + percentage
    draw.text((bar_x, bar_y + bar_h + 18),
              f"{int(frac * 100)}% · {data['days_left']} days left",
              font=theme.font(30), fill=theme.MUTED)

    # Month weekdays stat (compact single line)
    month_txt = f"{data['month']} · {data['weekdays_left']} / {data['weekdays_total']} weekdays left"
    draw.text((x + pad, bar_y + bar_h + 66), month_txt,
              font=theme.font(30), fill=theme.INK)
```

#### Renderer — in `_render_bottom_left()`, new branch

```python
elif choice == "quarter":
    from .widgets import quarter as quarter_widget
    ctx = {**quarter.quarter_info(today_date), **quarter.month_weekdays(today_date)}
    quarter_widget.render(draw, box, ctx)
```

Actually, to follow the existing import pattern (S6), the import should be at the top of `renderer.py`:

```python
from .widgets import quarter as quarter_widget
```

And the branch becomes:

```python
elif choice == "quarter":
    ctx = {**quarter.quarter_info(today_date), **quarter.month_weekdays(today_date)}
    quarter_widget.render(draw, box, ctx)
```

The `quarter` (pure helper) import is also at the top:

```python
from . import agenda, countdown, daylight, ekadashi, moon, quarter, review, store, theme, weathericons, weatherview
```

#### Config — `BOTTOM_LEFT_WIDGET=quarter` as a new valid choice

Update the comment in `config.py` line 25:

```python
# Which widget fills the bottom-left zone: week | life | weekofyear | yearprogress | countdown | quarter
```

No new env vars. No validation change (unknown values fall through to default `week`).

### Tests

#### `tests/test_ekadashi.py`

- **Known-date checks**: Pin `now_utc` to dates with known Ekadashis in 2026 (cross-reference Drik Panchang). Verify `next_ekadashi()` returns the correct date and day count.
- **Full-year scan**: Iterate all 365 days of 2026, collect all Ekadashis returned. Verify count is 24 (12 Shukla + 12 Krishna). Verify no gap exceeds 16 days.
- **Consecutive-day suppression**: For the May 2026 case (May 25-26 both in range), verify only May 25 is returned.
- **Today is Ekadashi**: Pin `now_utc` to a known Ekadashi date, verify `days == 0`.
- **Today is second day of a double**: Pin `now_utc` to May 26, verify it skips to the next Ekadashi (not "today").
- **Returns `None` only if no Ekadashi in 33-day window**: This should never happen in practice (max gap ~15d), but test the boundary.

#### `tests/test_quarter.py`

- **Quarter boundaries**: Jan 1 (Q1, fraction ~0), Mar 31 (Q1, fraction ~1.0), Apr 1 (Q2, fraction ~0).
- **Mid-quarter**: Feb 15 in a leap year vs. non-leap year.
- **Days left**: Known dates at start, middle, end of quarter.
- **Month weekdays**: June 2026 (22 weekdays total), February 2028 (leap, 21 weekdays).
- **Weekdays left**: June 30 (Monday) -> 1 weekday left (today counts). June 28 (Saturday) -> 2 weekdays left (Mon 29, Tue 30).
- **Month name**: Verify full name ("June", not "Jun").

## Files changed / created

| File | Action |
|------|--------|
| `server/app/ekadashi.py` | Create — observer-free tithi computation, multi-sample |
| `server/app/quarter.py` | Create — quarter + weekday helpers |
| `server/app/widgets/quarter.py` | Create — quarter widget renderer |
| `server/app/renderer.py` | Edit — (1) fix cursor after moon phase text, (2) add Ekadashi footer segment, (3) add quarter widget branch + imports |
| `server/app/config.py` | Edit — document `quarter` as a `BOTTOM_LEFT_WIDGET` choice |
| `server/tests/test_ekadashi.py` | Create |
| `server/tests/test_quarter.py` | Create |
| `docs/ROADMAP.md` | Edit — move items to Done |

## Out of scope

- Shukla/Krishna qualifier in the display.
- Custom Ekadashi glyph.
- Holiday-aware workday counting.
- Ekadashi via `.ics` feed (the originally deferred approach; superseded by `ephem`).
- Observer-based sunrise computation (eliminated in v2; observer-free approach is simpler and sufficient).
