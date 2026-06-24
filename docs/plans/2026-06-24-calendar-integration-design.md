# Calendar Integration (Phase 6) — Design

**Date:** 2026-06-24
**Status:** Design approved (revised after review 1)
**Author:** Anand (with Claude)

## Changes from previous version (review 1)

Addresses the three critical issues from `calendar-integration-design-review-1.md`:

1. **Conditional version bump is now a real, core mechanism** — a new
   `render_if_changed()` helper in core (not in the removable calendar package),
   reused by startup, glasses, and calendar. See "Refresh model".
2. **Header placement now has measured coordinates** — the header is restructured
   into two bands with explicit y-positions and a width budget; the banner only
   appears when calendar is configured.
3. **Banner symbols are font-safe** — the "now" dot is drawn as a filled ellipse
   primitive; all other text is ASCII. DejaVu is relied on only for normal text.

Also folds in suggestions: stdlib `urllib` for fetch (no httpx dep),
`recurring-ical-events` for RRULE expansion, `CALENDAR_TZ` via stdlib `zoneinfo`,
a render tick decoupled from the data poll, and explicit edge-case handling.

## Goal

Add the user's **personal calendar** to the always-on dashboard so it shows not
just tasks / habits / goals but *what's happening now and what's next* — the
"Now/Next focus banner" banked in the original design doc.

Scope: **a Now/Next banner only**, fed by a single **`.ics` URL** (personal
calendar). A full agenda widget is deferred.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Source | Single `.ics` URL | Simplest, fully self-hosted, no cloud API/OAuth |
| Scope | One personal calendar | One `.ics` = nothing to filter |
| Data poll | Fetch `.ics` every 15 min | Calendars change rarely |
| Render tick | Re-evaluate banner every 5 min | Keeps "now" fresh between data polls |
| E-ink flicker | Bump version only when PNG bytes change | No refresh unless the image differs |
| Display | Now/Next banner only | Highest signal-per-pixel; agenda later |
| Placement | Second band in the header (measured) | No body-zone resize, no Pi change |
| All-day events | Excluded from Now/Next | Would read as "Now" all day |

## Architecture

Calendar is its **own pluggable source package**, mirroring `glasses/`. The core
renderer never learns where events come from — it reads them from the store.

```
.ics URL ──poll(15m)──▶ calendar/sync ──▶ store (event table) ──▶ render_if_changed() ──▶ dashboard.png
```

New / changed pieces:

- **`server/app/calendar/`** — new isolated package:
  - `source.py` — fetch the `.ics` (stdlib `urllib`, with timeout), parse +
    expand recurrences, normalize to event records.
  - `sync.py` — background daemon thread (mirrors `glasses/watcher.py`).
- **`store.py`** — gains an `event` table + `get_todays_events()` /
  `replace_events()`, and a `meta['png_hash']` slot for the change check.
- **`renderer.py`** — header restructured into two bands; new `render_if_changed()`.
- **`main.py`** (composition root) — starts the calendar poller alongside the
  glasses watcher.

> **Hard rule:** the core (`api`, `renderer`, `store`, `config`, `widgets`) must
> **never import `calendar/`**. Wiring lives only in `main.py`, exactly like
> `glasses/`. Do **not** add a calendar startup hook in `api.py`. This keeps the
> package removable.

**Dependencies (pin in `requirements.txt`):** `icalendar` (parse) +
`recurring-ical-events` (expand RRULE — `icalendar` alone does **not** expand
recurrences). Fetch uses stdlib `urllib.request` — no new HTTP dep. TZ uses
stdlib `zoneinfo`.

## Data model

```
event(
  key        TEXT PRIMARY KEY,   -- synthetic: f"{uid}@{occurrence_start_utc}"
  uid        TEXT,               -- VEVENT UID (series id)
  title      TEXT,
  start_utc  TEXT,               -- ISO8601, UTC
  end_utc    TEXT,               -- ISO8601, UTC
  all_day    INTEGER,            -- 0/1
  location   TEXT
)
```

`key` is `uid + occurrence-start` so two occurrences of the same recurring series
don't overwrite each other. Added to the existing `SCHEMA` string via
`CREATE TABLE IF NOT EXISTS` (no migration system exists; new table is created on
next startup). Read with a standalone `get_todays_events()` returning
`list[dict]` — no joins (matches how the renderer reads every other table).

## Refresh model (resolves critical issue #1)

The existing `store.bump_version()` bumps unconditionally and `renderer.render()`
returns no "changed" signal. We add **one core helper** so polling can't cause
needless e-ink refreshes:

```
# renderer.py (core)
def render_if_changed() -> bool:
    render()                                   # writes config.png_path
    new_hash = sha256(open(png_path,'rb').read())
    if new_hash != store.get_meta('png_hash'):
        store.set_meta('png_hash', new_hash)
        store.bump_version()                   # Pi re-downloads
        return True
    return False
```

- Lives in **core**, reused by startup (`api.py`), glasses, and calendar — no
  hash logic leaks into the removable package.
- `store` gains tiny `get_meta()/set_meta()` helpers over the existing `meta`
  key/value table.

**Sync thread (`calendar/sync.py`), one daemon loop, sleeps 5 min:**
1. If ≥15 min since last successful fetch → fetch `.ics`, parse, expand
   recurrences for **today ± 1 day** (in `CALENDAR_TZ`), normalize to UTC,
   `store.replace_events(...)`.
2. Every tick (5 min) → `renderer.render_if_changed()`.

Result: the banner advances in ≤5-min steps (crossing a meeting boundary
re-renders), but the screen only refreshes when the rendered image actually
changes. Data is at most ~15 min stale; "now" is at most ~5 min stale —
documented and acceptable for e-ink.

### Failure handling

- Fetch fails / non-200 / HTML-not-ics / timeout → **keep last-good events**, log
  a warning, never crash the thread (bounded `urllib` timeout so it can't hang).
- Empty calendar / no `CALENDAR_ICS_URL` → poller doesn't start; banner hides;
  header reverts to date-only (current behavior).

## Header layout (resolves critical issue #2)

`header_h = int(H*0.10)` = 144px at 1440. Restructure `_draw_header` into two
explicit bands (coordinates relative to header box `y`, panel width 2560,
`pad=28`):

- **Top band — date + week/weather** (unchanged content, moved up):
  - Date: left at `(pad, y+18)`, font **40 bold** (was 46).
  - Right block `Week N / 52  --°`: right-aligned at `y+24`, font 32.
- **Bottom band — Now/Next banner** (new), only when calendar configured:
  - Drawn at `(pad, y+86)`, font **30**, max width `W - 2*pad`, left-aligned,
    truncated with `…` to fit.

If `CALENDAR_ICS_URL` is unset, the bottom band is skipped and the date stays
vertically centered as today — **zero visual change when the feature is off.**
No body-zone resize; the existing separator line stays at `header_h`.

## Now/Next banner logic

Computed at render time; "now" and "today" are evaluated in **`CALENDAR_TZ`**
(stdlib `zoneinfo`, so DST is handled). Timed events only.

- **Now** = event with `start ≤ now < end`; on overlap, the one ending soonest.
  (Selector compares full UTC timestamps, so a meeting spanning midnight still
  counts as "Now" at 00:30.)
- **Next** = earliest timed event with `start > now`, within today (`CALENDAR_TZ`).

### Rendering (font-safe — resolves critical issue #3)

- The leading indicator is a **filled ellipse drawn in INK** (`draw.ellipse`),
  not a glyph.
- All text is ASCII: `until`, `Next`, `No more events today`. Separator is `·`
  (present in DejaVu; DejaVu ships in the Docker image and is the documented
  requirement — `theme.font()` only falls back to a bitmap font if DejaVu is
  absent, which the deploy guarantees against).

```
(•) Now: Standup  until 10:00     ·     Next: 1:1 at 11:30
```

### Banner states

| Situation | Banner |
|-----------|--------|
| In a meeting, more after | `(•) Now: Standup until 10:00 · Next: 1:1 at 11:30` |
| In a meeting, none after | `(•) Now: Standup until 10:00 · Nothing after` |
| Free now, more today | `Next: 1:1 at 11:30` |
| Nothing left today | `No more events today` |
| No events / no URL | (band hidden; header = date only) |

## Config keys

| Key | Default | Purpose |
|-----|---------|---------|
| `CALENDAR_ICS_URL` | `""` | Personal `.ics` URL. Empty = feature off. |
| `CALENDAR_TZ` | `UTC` | IANA zone (e.g. `America/Los_Angeles`) for "now"/"today"/floating events. |
| `CALENDAR_POLL_MINUTES` | `15` | `.ics` fetch cadence. |
| `CALENDAR_RENDER_TICK_MINUTES` | `5` | Banner re-evaluation cadence. |

## Testing

- **Unit — now/next selector** with frozen `now` + synthetic events: in-meeting,
  gap, end-of-day, all-day-only, overlap, midnight-spanning, empty. No network.
- **Unit — `render_if_changed()`**: returns False + no version bump on identical
  input; True + bump when content differs.
- **Parse — sample `.ics` fixture**: timed + recurring (RRULE expansion) + all-day
  + a `TZID` and a floating event; assert UTC normalization and synthetic keys.

## Out of scope (this phase)

- Full agenda / timeline widget (banked; `event` table already supports it).
- Multiple / work calendars.
- Writing to the calendar (display-only).
- Weather in the header (separate banked item).
- Migrating the deprecated `on_event("startup")` hooks to `lifespan` (codebase-wide
  cleanup; out of scope here — calendar mirrors the existing pattern in `main.py`).
