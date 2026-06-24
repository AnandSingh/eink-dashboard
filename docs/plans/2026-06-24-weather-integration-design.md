# Weather Integration (Phase 7) — Design

**Date:** 2026-06-24
**Status:** Design approved (revised after review 1)
**Author:** Anand (with Claude)

## Changes from review 2

- **Render-lock deadlock fixed.** Round 2 caught that having both `render()` and
  `render_if_changed()` acquire a plain `threading.Lock` self-deadlocks, since
  `render_if_changed()` calls `render()` on the same thread. Fix: an internal
  **unlocked** `_render_unlocked()` does the actual draw+save; the public functions
  hold the lock and call it (no re-acquire). See the revised Concurrency section.
- Minor: `busy_timeout` is set per-connection; WAL is set once (idempotent). WAL
  sidecar files (`-wal`/`-shm`) live in `DATA_DIR`, which is not Syncthing-synced
  (only the photo inbox is), so no sync hazard. The concurrency test asserts
  **forward progress** (version increments by exactly N) so a deadlock would surface.

## Changes from previous version (review 1)

Addresses the three critical issues from `weather-integration-design-review-1.md`:

1. **Concurrency / render safety is now specified** (new section below). A third
   timer-driven render thread turns a latent race into a live one, so this phase
   hardens the shared render path: a module-level render lock, atomic PNG write
   (`os.replace`), single-statement version bump, and SQLite `busy_timeout` + WAL.
   This also fixes the pre-existing calendar/glasses race.
2. **Import boundary pinned** — the WMO table + icon drawing live entirely in core
   `weathericons.py`; `weather/source.py` only stores the raw integer code, so core
   never imports `weather/` and nothing is shared across the boundary.
3. **Header right-block rewrite specified** — segmented left-to-right drawing with
   `ICON_W`/gap constants and a defined icon vertical anchor.

Also folds in suggestions: ip-api HTTP caveat + manual-override recommendation,
location-cache soft TTL, defensive per-field parsing, float-parsed override keys.

## Goal

Fill the header's `--°` placeholder with live weather: a drawn condition icon +
current temperature + today's high/low. Zero-config out of the box (auto-detect
location), no API key.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Source | Open-Meteo | Free, no API key, no account |
| Display | icon + current temp + today's H/L | At-a-glance planning; H/L free in same call |
| Location | Auto by IP, manual override | Zero-config default; override for VPN / accuracy |
| IP geolocation | `ip-api.com` (free, no key) | No account; city-level is right for home |
| Units | Configurable, default fahrenheit | Matches the header mockup (`72°`) |
| Refresh | Poll every 30 min | Weather changes slowly; e-ink is slow |
| Icons | Drawn primitives in INK | Font-safe, like the calendar dot |

## Architecture

Weather follows the **same pattern as calendar**: a removable `weather/` package
fetches data into the store; the core header reads + draws it. The core never
imports `weather/`.

```
(IP geolocate -> lat/lon) -> Open-Meteo --poll(30m)--> weather/sync -> store(meta 'weather' JSON) -> render_if_changed() -> header
```

- **`server/app/weather/`** — isolated package:
  - `source.py` — resolve location (manual override else IP geolocate, cached);
    fetch from Open-Meteo (stdlib `urllib`, bounded timeout). Pure parsers for both
    JSON payloads. **Stores only raw values** incl. the integer WMO `code` — it does
    NOT map codes to categories.
  - `sync.py` — daemon thread (mirrors `calendar/sync.py`): poll every 30 min,
    then `renderer.render_if_changed()`.
- **`store.py`** — reuse the `meta` table: `meta['weather']`, `meta['weather_loc']`.
  Plus the concurrency hardening below.
- **`renderer.py`** — right block reads weather and draws icon + temp + H/L; falls
  back to `--°` when there's no data. Plus the render-lock + atomic-write hardening.
- **`app/weathericons.py`** (core) — owns the WMO-code -> category table AND the
  glyph drawing. **Must not import `app/weather/`.**
- **`app/weatherview.py`** (core) — pure parse of `meta['weather']` -> display
  strings (or None). **Must not import `app/weather/`.**
- **`main.py`** — start the weather poller alongside glasses + calendar.

**Dependencies:** none new — stdlib `urllib` + `json`.

## Concurrency & render safety (resolves critical issue #1)

With weather there are **three daemon threads** (glasses watcher, calendar sync,
weather sync) plus the FastAPI `/dashboard.png` handler, all able to touch the
render/store path. The current primitives are unsafe under overlap; this phase
fixes them in **core** (benefiting calendar/glasses too):

- **Serialize renders (no self-deadlock).** Add a module-level `threading.Lock` in
  `renderer.py` plus an internal **unlocked** `_render_unlocked()` that does the
  actual draw+save. The public entry points hold the lock and call the unlocked
  core — they never re-acquire:
  ```
  _LOCK = threading.Lock()
  def _render_unlocked(): ...        # draw + atomic save; no locking
  def render():
      with _LOCK: _render_unlocked()
  def render_if_changed():
      with _LOCK:
          _render_unlocked()
          # hash png + atomic bump if changed
  ```
  (Tick rates are minutes apart; contention is negligible.)
- **Atomic PNG write.** `render()` writes to `config.png_path + ".tmp"` then
  `os.replace(tmp, png_path)` (atomic rename on POSIX) so the Pi / `FileResponse`
  never reads a half-written file.
- **Atomic version bump.** Replace the read-modify-write in `store.bump_version()`
  with a single statement:
  `UPDATE meta SET value = CAST(value AS INTEGER) + 1 WHERE key='version'`.
- **SQLite waits instead of failing.** In `connect()`: `PRAGMA busy_timeout=5000`
  and `PRAGMA journal_mode=WAL`, so concurrent `set_meta`/bump wait rather than
  raising `database is locked`.

## Config keys

| Key | Default | Purpose |
|-----|---------|---------|
| `WEATHER_ENABLED` | `true` | Master switch; false -> poller off, header `--°`. |
| `WEATHER_LAT` | `""` | Manual latitude override (with LON, skips IP lookup). |
| `WEATHER_LON` | `""` | Manual longitude override. |
| `WEATHER_UNITS` | `fahrenheit` | `fahrenheit` or `celsius`. |
| `WEATHER_POLL_MINUTES` | `30` | Fetch cadence. |

Override keys are parsed to float with try/except; the override engages only when
**both** parse successfully, otherwise fall back to IP geolocation.

## Location resolution (cached, soft TTL)

1. If both `WEATHER_LAT`/`WEATHER_LON` parse -> use them; skip IP lookup.
2. Else read `meta['weather_loc']`; if present and fresher than **7 days** -> use it.
3. Else `GET http://ip-api.com/json` -> `lat`/`lon`/`city`; cache to
   `meta['weather_loc']` with a timestamp. On failure, fall back to the cached
   value even if stale; if none, skip weather this cycle.

> **Privacy/HTTP caveat:** `ip-api.com` is plain HTTP and is a third party that
> sees the server's public IP; a network observer could tamper the response. For a
> home dashboard this is an acceptable tradeoff. Set `WEATHER_LAT/LON` to avoid the
> lookup entirely.

## Fetch & parse

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude={lat}&longitude={lon}
    &current=temperature_2m,weather_code
    &daily=temperature_2m_max,temperature_2m_min
    &temperature_unit={fahrenheit|celsius}&timezone=auto
```

`timezone=auto` aligns `daily[0]` to the location's local day. The parser reads
`current.temperature_2m`, `current.weather_code`, `daily.temperature_2m_max[0]`,
`daily.temperature_2m_min[0]` **defensively** (guard empty/short arrays, non-numeric
values). If any required field is missing -> return no snapshot and **keep last-good**
rather than storing a half-snapshot.

Stored: `meta['weather'] = {"temp","high","low","code","city","updated_utc"}`.

## Failure handling (keep last-good)

- IP geolocation fails + no cache + no override -> skip cycle, log, retry. Header `--°`.
- Open-Meteo fails / non-200 / bad JSON / timeout / missing field -> keep last-good
  `meta['weather']`, log, never crash the thread. Bounded `urllib` timeout.
- `WEATHER_ENABLED=false` -> poller never starts; header `--°`.

## Header rendering (resolves critical issue #3)

WMO code -> category (`weathericons.py`, **range-based** so freezing variants 56/57,
66/67 are covered):

| Category | WMO codes | Glyph |
|----------|-----------|-------|
| clear | 0 | sun (circle + rays) |
| partly | 1, 2 | small sun + cloud |
| cloudy | 3, 45, 48 | cloud |
| rain | 51-67, 80-82 | cloud + diagonal rain lines |
| snow | 71-77, 85, 86 | cloud + dots |
| thunder | 95-99 | cloud + lightning bolt |

Unknown code -> cloudy. All glyphs drawn as primitives in INK.

**Right-block rewrite.** The current code draws one text string and right-aligns via
`textlength`. Because the group now contains a drawn icon, it becomes segmented:
- Constants: `ICON_W = 40`, `GAP = 18`.
- Compute `total = textlen("Week N / 52") + GAP + ICON_W + GAP + textlen(temp) + GAP + textlen("H78 L61")`.
- Start at `x0 = W - pad - total`; draw each segment left-to-right, advancing the cursor.
- Icon vertical anchor: centered on the text cap-height at `right_y` (icon box
  `[cursor, right_y + cap/2 - ICON_W/2 ...]`) so it aligns with the 32px text, in
  both single-band (`right_y = y + h//2 - 18`) and two-band (`right_y = y + 24`) cases.
- No weather data -> draw the literal `Week N / 52   --°` exactly as today.

Horizontal room is ample at 2560px (left date and right group never approach center).

**`weatherview.py`** (pure, core): parse `meta['weather']` -> `{temp_txt, hl_txt,
category}` or `None` if missing/garbage/any required field non-numeric.

## Testing

- **Concurrency**: a test spawning N threads calling `render_if_changed()` /
  `bump_version()` concurrently asserts no lost version bumps and no exceptions.
- **`weathericons.category(code)`**: representative codes per bucket + unknown -> cloudy.
- **`weatherview` parse**: valid blob -> strings; missing/garbage/short -> None.
- **`weather/source` parsers**: sample Open-Meteo JSON -> snapshot (units, short
  `daily` guard); sample `ip-api` JSON -> lat/lon/city. No network.

## Out of scope (this phase)

- Hourly/multi-day forecast; "feels like", humidity, wind, sunrise/sunset.
- City-name geocoding (manual lat/lon + IP auto cover it).
- Showing last-updated time in the header.
