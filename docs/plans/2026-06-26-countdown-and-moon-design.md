# Countdown Widget + Moon Phase — Design

**Date:** 2026-06-26
**Status:** ✅ Built (phase 10). Countdown widget + moon phase shipped; Ekadashi deferred.
**Author:** Anand (with Claude)

## Goal

Two small, glanceable additions:

1. **Countdown widget** — a bottom-left list of *only the user's own* marked events
   ("Trip 23d", "Q3 ends 41d"). No festivals or auto-injected dates. Pure compute.
2. **Moon phase** — a footer segment with an accurate, named moon phase + a
   phase-accurate drawn glyph, computed via the `ephem` astronomy library.

**Ekadashi is explicitly deferred** (planned later). When revisited, the chosen
route is a dedicated `.ics` feed (see *Deferred* below) — not part of this phase.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Countdown placement | Bottom-left widget (`BOTTOM_LEFT_WIDGET=countdown`) | Roomy list; reuses the swappable-slot pattern; footer is full. Sunday review still overrides. |
| Countdown content | User-configured dates only | User wants it uncluttered — their planned events, nothing auto-added. |
| Countdown config | `COUNTDOWNS="label:YYYY-MM-DD;…"` env | Matches the env-driven config pattern; no new storage. |
| Moon source | `ephem` library (offline) | Self-contained (no key/network), accurate illumination + phase; small prebuilt wheel. |
| Moon placement | Footer segment | Fits the footer's time/cosmic-awareness theme; reuses the phase-9 glyph idea. |
| Ekadashi | Deferred | User will plan separately; avoids a network/feed pipeline now. |

## Architecture

### A. Countdown widget

- **`app/countdown.py`** — *pure core* (sibling to `review.py`):
  - `parse(raw: str) -> [{label, date}]` — split on `;`, each `label:YYYY-MM-DD`;
    malformed entries skipped defensively (bad date → dropped).
  - `build(entries, today) -> [{label, days, text}]` — `days = (date - today).days`;
    drop past (`days < 0`); sort soonest-first; format `0→"today"`, `1→"tomorrow"`,
    else `f"{days}d"`. Cap to `_MAX` rows (fits the zone; ~8).
- **`app/widgets/countdown.py`** — `render(draw, box, ctx)`: `COUNTDOWN` header +
  one row per entry (`label` left, days right-aligned). Empty → `"No countdowns set"`.
- **`renderer._render_bottom_left`** — add a `choice == "countdown"` branch
  (parse config once, build, render). The Sunday-review override still wins.
- **`config`** — `countdowns: str = os.getenv("COUNTDOWNS", "")`.

### B. Moon phase

- **Dependency** — add `ephem` to `server/requirements.txt`. No new system libs
  (self-contained wheel); the Dockerfile already `pip install`s requirements.
- **`app/moon.py`** — uses `ephem` (deterministic given a time, so unit-testable):
  - `phase(now_utc: datetime) -> {name, illum, waxing}`.
    - elongation = `(moon_ecliptic_lon - sun_ecliptic_lon) % 360`.
    - `waxing = elongation < 180`.
    - `illum = round(ephem.Moon(now).phase)` (0–100, % illuminated).
    - `name` from 8 elongation buckets (New / Waxing Crescent / First Quarter /
      Waxing Gibbous / Full / Waning Gibbous / Last Quarter / Waning Crescent),
      45°-wide, centered on 0/90/180/270.
- **`config`** — `moon_enabled: bool` (env `MOON_ENABLED`, default true).
- **`renderer._draw_footer`** — when `moon_enabled`, append a segment: a drawn
  phase-accurate moon glyph + short name + `f"{illum}%"`. Computed at render time
  (ephem is fast), like the daylight segment. Wrapped in try/except → omit on any
  ephem error (footer keeps working).

### Phase-accurate moon glyph

`_moon_phase_glyph(draw, cx, cy, r, illum, waxing)` — per-scanline terminator fill
(robust at footer size, r≈11):

```
k = illum / 100
for dy in -r..r:
    xc = sqrt(r² - dy²)
    tx = xc * (1 - 2k)            # k=0→right edge, 0.5→center, 1→left edge
    if waxing: lit = [tx, xc]     # illuminated on the right
    else:      lit = [-xc, -tx]   # illuminated on the left
    draw horizontal INK line over the lit span at row dy
draw circle outline (INK) around the disc
```

New → empty outline; Full → filled disc; quarters → half; crescent/gibbous → the
correct sliver on the correct side.

## Data flow

```
COUNTDOWNS env → countdown.parse → countdown.build(today) → widget rows   (render time)
ephem (offline) → moon.phase(now) → footer glyph + name + illum%           (render time)
```

Both are recomputed each render; the existing `render_if_changed()` hash means the
panel only refreshes when the drawn output actually changes. The phase-8 daily-tick
guarantees the moon/countdown advance even with all integrations disabled.

## Edge cases

- **Countdown**: empty/unset `COUNTDOWNS` → `"No countdowns set"`. Malformed entry
  (missing `:`, bad date) → skipped, others still shown. All past → empty list →
  the prompt. More than `_MAX` → cap (soonest kept).
- **Moon**: any `ephem` error → omit the segment (try/except in the footer).
  `MOON_ENABLED=false` → segment absent. Illum at exact new/full handled by buckets.

## Testing

- **`tests/test_countdown.py`** (pure): parse valid/malformed; days math; past
  dropped; today/tomorrow labels; sort order; cap.
- **`tests/test_moon.py`** (uses `ephem`, deterministic): drive `phase()` with
  `ephem.next_full_moon` / `next_new_moon` / `first/last_quarter_moon` instants and
  assert the name, `illum` (~100 at full, ~0 at new), and `waxing` flag. This tests
  our bucketing/glue against ephem's own phase events.

## Out of scope / Deferred

- **Ekadashi** — later phase. Planned route: dedicated `EKADASHI_ICS_URL` + a small
  wide-window `.ics` sync (the personal calendar's `parse_events` uses
  `window_days=1` and `replace_events` wipes the table, so Ekadashi needs its own
  feed + storage), with the next date surfaced in the moon footer. Kept out now to
  avoid a network/feed dependency.
- Days-to-next-full/new-moon, moonrise/set, per-event countdown colors — YAGNI.
