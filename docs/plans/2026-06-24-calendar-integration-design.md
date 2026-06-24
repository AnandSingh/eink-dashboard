# Calendar Integration (Phase 6) — Design

**Date:** 2026-06-24
**Status:** Design approved
**Author:** Anand (with Claude)

## Goal

Add the user's **personal calendar** to the always-on dashboard so it shows not
just tasks / habits / goals but *what's happening now and what's next* — the
"Now/Next focus banner" banked in the original design doc.

Scope for this phase: **a Now/Next banner only**, fed by a single **`.ics` URL**
(personal calendar), polled every **15 minutes**. A full agenda widget is
deferred.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Source | Single `.ics` URL | Simplest, fully self-hosted, no cloud API/OAuth |
| Scope | One personal calendar | One `.ics` = nothing to filter |
| Refresh | Poll every 15 min | Calendars change rarely; e-ink is slow + ghosts |
| Display | Now/Next banner only | Highest signal-per-pixel; banked feature; agenda later |
| Placement | Second line in the header | No zone resize, no Pi change, reuses header whitespace |
| All-day events | Excluded from Now/Next | Would read as "Now" all day and drown out meetings |

## Architecture

Calendar is its **own pluggable source package**, mirroring how `glasses/` is
isolated. The core renderer never learns where events come from — it reads them
from the store.

```
.ics URL ──poll(15m)──▶ calendar/sync ──▶ store (event table) ──▶ renderer header banner ──▶ dashboard.png
```

New / changed pieces:

- **`server/app/calendar/`** — new isolated package:
  - `source.py` — fetch the `.ics` over HTTP, parse it, normalize to event records.
  - `sync.py` — background poller (every 15 min); refresh the event table, then
    re-render and **bump `version` only if the rendered PNG content hash changed**
    (no needless e-ink refresh).
- **`store.py`** — gains an `event` table + `get_todays_events()` / `replace_events()`.
- **`renderer.py`** — header gains a Now/Next sub-line (the only render change).
- **`main.py`** (composition root) — starts the calendar poller alongside the
  glasses watcher. The **core never imports `calendar/`**; it plugs in here, so
  it's removable, exactly like `glasses/`.

**New dependency:** `icalendar` (parses `.ics` / VEVENT / recurrence). Fetch via
`httpx` (already transitively present) or stdlib `urllib`.

## Data model

```
event(
  uid        TEXT PRIMARY KEY,   -- VEVENT UID (+ recurrence-id for repeats)
  title      TEXT,
  start_utc  TEXT,               -- ISO8601, normalized to UTC
  end_utc    TEXT,
  all_day    INTEGER,            -- 0/1
  location   TEXT
)
```

## Sync behavior (`calendar/sync.py`)

1. Every 15 min: fetch the `.ics` URL.
2. Parse with `icalendar`; **expand recurring events** for a small window
   (today ± 1 day — enough for a Now/Next banner; no year-long expansion).
3. Normalize all times to **UTC** for storage; convert to local only at render time.
4. `store.replace_events(...)` — wipe + repopulate (table is tiny + display-only,
   so no incremental diffing needed).
5. Re-render; bump `version` only if the PNG content hash changed.

### Timezone

`.ics` times come in three flavors: zoned (`TZID=…`), UTC (`Z`), and "floating"
(no zone). We store UTC; floating times are interpreted in **`CALENDAR_TZ`**
(IANA name, e.g. `America/Los_Angeles`), which also drives "what is now" at
render time.

### Failure handling

Matches the original doc's "never silently drop / keep last good state":

- Fetch/parse fails → **keep the previously-synced events**, log a warning, don't
  crash the poller. Banner keeps showing last-known data rather than going blank.
- Empty calendar / no URL configured → banner hides; header reverts to date-only.

## Now/Next banner logic

Computed at render time using `CALENDAR_TZ` for "now":

- **Now** = event with `start ≤ now < end` (timed only); on overlap, the one
  ending soonest.
- **Next** = earliest timed event with `start > now` **today**.

Rendering — header sub-line under the date:

```
● Now: Standup → 10:00    ·    Next: 1:1 at 11:30
```

- "Now" shows title + **end** time; "Next" shows title + **start** time.
- Local TZ, `%-I:%M` formatting; long titles truncated with `…` to fit width.
- Symbol: a filled circle `●` drawn in INK (not the `🔴` emoji, which the DejaVu
  fallback font won't render on grayscale e-ink).

### Banner states

| Situation | Banner |
|-----------|--------|
| In a meeting, more after | `● Now: Standup → 10:00 · Next: 1:1 at 11:30` |
| In a meeting, none after | `● Now: Standup → 10:00 · Nothing after` |
| Free now, more today | `Next: 1:1 at 11:30` |
| Nothing left today | `✓ No more events today` |
| No events / no URL | (banner hidden; header = date only) |

## Config keys

| Key | Default | Purpose |
|-----|---------|---------|
| `CALENDAR_ICS_URL` | `""` | The personal `.ics` URL. Empty = feature off. |
| `CALENDAR_TZ` | system / `UTC` | IANA zone for "now" + floating events. |
| `CALENDAR_POLL_MINUTES` | `15` | Poll cadence. |

## Testing

- **Unit** — pure now/next selector with a frozen `now` and synthetic event lists:
  in-meeting, gap, end-of-day, all-day-only, overlap, empty. No network.
- **Parse** — one test against a sample `.ics` fixture (timed + recurring + all-day).

## Out of scope (this phase)

- Full agenda / timeline widget (banked for later — the `event` table already
  supports it).
- Multiple calendars / work calendar.
- Writing to the calendar (display-only).
- Weather in the header (separate banked item).
