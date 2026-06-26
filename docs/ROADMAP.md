# Roadmap — banked widgets & features

Glanceable, grayscale, no-interaction widgets suited to the e-ink dashboard.
Each new widget is a self-contained zone the renderer can drop in (no Pi changes).

## Done

- ✅ Week-of-year, year-progress bar, life-in-weeks (`extras`, selectable via `BOTTOM_LEFT_WIDGET`)
- ✅ Time-awareness footer strip (year % · week-of-year · life lived)
- ✅ Calendar Now/Next header banner (phase 6)
- ✅ Weather: icon + temp + today's high/low (phase 7)
- ✅ Sunday weekly-review mode + core daily-tick (phase 8)
- ✅ Sunrise/sunset + daylight remaining in footer (phase 9)

## Next up (recommended order)

1. **Countdown widget** — configurable target dates ("Trip in 23 days",
   "Q3 ends in 41 days"). Pure compute, trivial, highly motivating.
2. **Quarter progress** + **weekdays/workdays left in month** — sharper than year %
   (pure compute; see backlog).
3. **Moon phase** — computed, no API. Ambient touch (the footer already has a moon
   glyph from phase 9 to reuse).

### Shipped

- ~~Sunrise/sunset + daylight remaining~~ — ✅ phase 9.
  `docs/plans/2026-06-24-sunrise-sunset-design.md`
- ~~Sunday weekly-review mode~~ — ✅ phase 8.
  `docs/plans/2026-06-26-sunday-weekly-review-design.md`

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
