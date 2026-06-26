# Roadmap — banked widgets & features

Glanceable, grayscale, no-interaction widgets suited to the e-ink dashboard.
Each new widget is a self-contained zone the renderer can drop in (no Pi changes).

## Done

- ✅ Week-of-year, year-progress bar, life-in-weeks (`extras`, selectable via `BOTTOM_LEFT_WIDGET`)
- ✅ Time-awareness footer strip (year % · week-of-year · life lived)
- ✅ Calendar Now/Next header banner (phase 6)
- ✅ Weather: icon + temp + today's high/low (phase 7)

## Next up (recommended order)

1. **Sunrise / sunset + daylight remaining** — *highest value-per-effort.*
   Open-Meteo already returns `daily.sunrise`/`sunset`; add two fields to the
   existing weather fetch + a footer-strip segment. Complements weather.
   📐 **Designed** (deferred): `docs/plans/2026-06-24-sunrise-sunset-design.md`
2. **Countdown widget** — configurable target dates ("Trip in 23 days",
   "Q3 ends in 41 days"). Pure compute, trivial, highly motivating.
3. **Sunday weekly-review mode** (larger; its own phase) — on Sundays swap a zone
   to a review view: wins / misses this week + space for next week's 3 big rocks.
   A time-aware layout change, not just a widget.
   📐 **Designed**: `docs/plans/2026-06-26-sunday-weekly-review-design.md`

## Backlog

### Time-awareness / "memento" (pure compute, no data source)
- **Quarter progress** + **weekdays/workdays left in month** — sharper than year %.
- **Moon phase** — computed, no API. Ambient touch.

### Leverages data we already have (no new source)
- **Habit consistency heatmap** — GitHub-style grid of habit completions over weeks.
- **Habit over-commitment warning** — flags an unrealistic week (targets vs capacity).
- **Streak board** — biggest current streaks.
- **Today's agenda** — full timeline from the calendar `event` table.

### Leverages goals data (small schema addition)
- **Goal → habit linkage** — show which habits feed each goal.
- **Goal countdown** — days to each goal's due date.

### Needs voice / glasses (heavier)
- **Dictated one-line journal** + **"1 year ago today"**.

## Design principles for new widgets

- Self-contained: render into a single zone box; selectable via a config key.
- Pure/testable core logic; optional data sources isolated in their own package
  (the core never imports them — see `glasses/`, `calendar/`, `weather/`).
- Font-safe glyphs drawn as primitives in INK (no emoji on e-ink).
- Re-render via `render_if_changed()` so the screen only refreshes on real change.
