# Weather Integration (Phase 7) — Design

**Date:** 2026-06-24
**Status:** Design approved
**Author:** Anand (with Claude)

## Goal

Fill the header's `--°` placeholder with live weather: a condition icon, current
temperature, and today's high/low. Zero-config out of the box (auto-detect
location), no API key, matching the project's self-hosted, low-friction ethos.

## Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Source | Open-Meteo | Free, no API key, no account |
| Display | icon + current temp + today's H/L | "At a glance" planning value; H/L is free in the same call |
| Location | Auto by IP, manual override | Zero-config default; override for VPN / wrong detection |
| IP geolocation | `ip-api.com` (free, no key) | No account; city-level accuracy is right for a home dashboard |
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

New / changed pieces:

- **`server/app/weather/`** — new isolated package:
  - `source.py` — resolve location (manual `WEATHER_LAT/LON`, else IP geolocate,
    cached); fetch current temp + today's high/low + WMO code from Open-Meteo
    (stdlib `urllib`, bounded timeout). Pure parsers for both JSON payloads.
  - `sync.py` — daemon thread (mirrors `calendar/sync.py`): poll every 30 min,
    then `renderer.render_if_changed()`.
- **`store.py`** — reuse the existing `meta` table: `set_meta('weather', json)`,
  `set_meta('weather_loc', json)`. No new schema (weather is one current snapshot).
- **`renderer.py`** — header right block reads weather and draws icon + temp + H/L;
  falls back to the existing `--°` placeholder when there's no data.
- **`app/weathericons.py`** (core) — WMO code -> category + glyph drawing.
- **`app/weatherview.py`** (core) — pure parse of `meta['weather']` -> display strings.
- **`main.py`** — start the weather poller alongside glasses + calendar.

**Dependencies:** none new — stdlib `urllib` + `json`.

## Config keys

| Key | Default | Purpose |
|-----|---------|---------|
| `WEATHER_ENABLED` | `true` | Master switch; false -> poller off, header shows `--°`. |
| `WEATHER_LAT` | `""` | Manual latitude override (with LON, skips IP lookup). |
| `WEATHER_LON` | `""` | Manual longitude override. |
| `WEATHER_UNITS` | `fahrenheit` | `fahrenheit` or `celsius`. |
| `WEATHER_POLL_MINUTES` | `30` | Fetch cadence. |

## Location resolution (once, cached)

1. If `WEATHER_LAT` and `WEATHER_LON` are set -> use them; skip IP lookup.
2. Else -> `GET http://ip-api.com/json` -> `lat`/`lon`/`city`; cache in
   `meta['weather_loc']` so transient IP-lookup failures don't wipe a known-good
   location and we don't re-geolocate every poll.

## Fetch

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude={lat}&longitude={lon}
    &current=temperature_2m,weather_code
    &daily=temperature_2m_max,temperature_2m_min
    &temperature_unit={fahrenheit|celsius}&timezone=auto
```

Stored snapshot: `meta['weather'] = {"temp","high","low","code","city","updated_utc"}`.

## Failure handling (keep last-good, like calendar)

- IP geolocation fails, no cached location, no manual override -> skip this cycle,
  log, retry next tick. Header shows `--°`.
- Open-Meteo fetch fails / non-200 / bad JSON / timeout -> keep last-good
  `meta['weather']`, log, never crash the thread. Bounded `urllib` timeout.
- `WEATHER_ENABLED=false` -> poller never starts; header shows `--°`.
- Snapshot carries `updated_utc`; v1 does not render it (header space), but stale
  data ages silently — logged for debugging.

## Header rendering

WMO code -> icon category (`weathericons.py`):

| Category | WMO codes | Glyph |
|----------|-----------|-------|
| clear | 0 | sun (circle + rays) |
| partly | 1, 2 | small sun + cloud |
| cloudy | 3, 45, 48 | cloud |
| rain | 51-67, 80-82 | cloud + diagonal rain lines |
| snow | 71-77, 85, 86 | cloud + dots |
| thunder | 95-99 | cloud + lightning bolt |

Unknown code -> cloudy (safe default). All glyphs drawn as primitives in INK.

Layout — weather joins the existing right-side header block, replacing `--°`:

```
Week 26 / 52      (icon) 72°  H78 L61
```

The right group is right-aligned by measuring total width (week text + gap + icon
box + temp + H/L) and drawing left-to-right from `W - pad - total`. Works in both
the single-band header and the two-band header (with the calendar banner) — weather
stays on the top/date band. No weather data -> renders exactly as today.

## Testing

- **Unit — `weathericons.category(code)`**: representative codes per bucket + unknown -> cloudy.
- **Unit — `weatherview` parse**: valid blob -> formatted strings; missing/garbage -> None.
- **Unit — `weather/source` parsers**: sample Open-Meteo JSON -> snapshot (temp/high/low/code,
  unit handling); sample `ip-api` JSON -> lat/lon/city. No network.

## Out of scope (this phase)

- Hourly forecast / multi-day outlook (header is one slot).
- "Feels like", humidity, wind, sunrise/sunset.
- Geocoding a city-name string (manual lat/lon + IP auto cover it).
- Showing the last-updated time in the header.
