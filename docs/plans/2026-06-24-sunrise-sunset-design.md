# Sunrise / Sunset + Daylight Remaining — Design

**Date:** 2026-06-24
**Status:** ✅ Built (phase 9) — implemented as designed (pure `daylight.py` helper +
`weatherview.parse_sun` + footer segment with drawn sun/moon glyphs)
**Author:** Anand (with Claude)

## Goal

Add a footer segment showing today's **sunrise/sunset** plus **daylight
remaining**, reusing the weather feature's Open-Meteo connection. Fits the
footer's existing "time remaining / progress" theme (year %, week-of-year, life
lived).

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Placement | Footer strip segment | Header is full; footer is the "remaining" zone |
| Content | sunrise/sunset + daylight remaining | Static times + on-theme dynamic "remaining" |
| Source | Open-Meteo `daily.sunrise`/`sunset` | Already wired for weather; no new source/key |
| Sun glyph | Drawn primitive in INK | Font-safe, like the weather icons |

Display (day): `(sun) 6:12–20:45 · 4h12m left`
Night states: before sunrise -> `(sun) rises 6:12`; after sunset -> `(moon/sun) set 20:45`.

## Architecture

Extends the existing **weather** feature — no new package.

- **`weather/source.py`** — add `sunrise`,`sunset` to the Open-Meteo request
  (`daily=...,sunrise,sunset`) and to the stored snapshot. Open-Meteo returns
  these as local ISO timestamps when `timezone=auto`; store them as-is (local) or
  normalized — pick one and parse defensively (guard short/missing arrays).
- **`app/weatherview.py`** (core) — extend the parsed view with `sunrise`/`sunset`
  (or a sibling pure helper `daylight.py`) that, given sunrise/sunset + now,
  returns the formatted segment string and the day/night state. Pure + testable.
- **`renderer.py` `_draw_footer`** — add a segment that draws a small sun glyph +
  the daylight text, only when the data is present (graceful absence otherwise).
- **`weathericons.py`** or a small footer helper — a `sun`/`moon` glyph sized for
  the footer.

No new config (rides on `WEATHER_ENABLED` + location). No new dependency.

## Data flow

```
Open-Meteo daily.sunrise/sunset -> weather snapshot (meta['weather']) -> footer segment (computed at render time)
```

"Daylight remaining" is computed at render time from sunset - now (in the
location's local tz), so it advances with the existing render ticks; the weather
poll only needs to refresh the daily sunrise/sunset once per day.

## Edge cases

- Missing/short sunrise/sunset arrays -> omit the segment (keep last-good weather).
- Polar day/night (no sunrise or sunset) -> show a sensible fallback or omit.
- Timezone: compute "remaining" in the location's tz (Open-Meteo `timezone=auto`
  aligns the daily values); be explicit about parsing tz-aware vs naive ISO.

## Testing

- **Pure daylight helper**: given (sunrise, sunset, now) -> correct segment string
  and state for before-sunrise, daytime (remaining), after-sunset, and missing data.
- **weather/source parser**: sample Open-Meteo JSON including `daily.sunrise/sunset`
  -> snapshot carries them; short/missing arrays handled.

## Out of scope

- Golden-hour / civil twilight, moon phase (separate roadmap item), UV index.
