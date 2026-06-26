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
- ✅ Countdown widget (your marked events) + moon phase via ephem (phase 10)

## Next up (recommended order)

1. **Ekadashi countdown** — deferred from phase 10. Planned route: dedicated
   `EKADASHI_ICS_URL` + a wide-window `.ics` sync, surfaced next to the moon footer.
   See `docs/plans/2026-06-26-countdown-and-moon-design.md` (Deferred section).
2. **Quarter progress** + **weekdays/workdays left in month** — sharper than year %
   (pure compute; see backlog).

### Shipped

- ~~Countdown widget + moon phase~~ — ✅ phase 10.
  `docs/plans/2026-06-26-countdown-and-moon-design.md`
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
