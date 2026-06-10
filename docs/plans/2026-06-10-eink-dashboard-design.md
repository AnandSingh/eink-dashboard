# E-ink Productivity Dashboard — Design

**Date:** 2026-06-10
**Status:** Design approved, scaffold created
**Author:** Anand (with Claude)

## Goal

Turn a 32" Boox e-ink monitor into an always-on, glare-free **productivity magic mirror**
that shows your day / week / month at a glance, fed by:

- A **paper notebook** photographed with **Meta Ray-Ban AI glasses** → AI extracts tasks
- Voice commands via the glasses (WhatsApp/Messenger) → check things off, log habits
- Your own data (weather, calendar later, habits, goals)

The system is **fully self-hosted** on a homelab server; the Boox is driven by a cheap
Raspberry Pi acting as a dumb display client.

## Architecture

```
✍️ notebook ──photo──┐
                     │  👓 "Hey Meta, take a picture"
                     ▼
              📱 Android phone (Meta AI app saves photo)
                     │  Syncthing mirrors the photo folder
                     ▼
   ┌─────────────────────────────────────────────┐
   │  HOMELAB SERVER (Docker)                      │
   │                                               │
   │  watcher → classifier → router → extractors   │
   │                          │                    │
   │  bot listener (WhatsApp) ┘                    │
   │                          ▼                    │
   │                       store (SQLite + .md)    │
   │                          ▼                    │
   │                       renderer → dashboard.png│
   │                          ▼                    │
   │                       api (serves PNG + version)│
   └─────────────────────────────────────────────┘
                     │  HTTP pull every N min / on version bump
                     ▼
              🖥️ Raspberry Pi (display.py, fullscreen)
                     │  HDMI
                     ▼
              📊 Boox 32" e-ink monitor
```

### Why this shape

- **Server does everything** — API calls, vision AI, rendering. Easy to change, fully in your control.
- **Pi is disposable** — just fetches a PNG and shows it. Dies? Swap for $50, zero reconfig.
- **No Meta API needed** — the glasses have no open API, so we bridge through the phone's
  photo folder (Syncthing) and a self-hosted messaging bot for voice write-back.

## Components (server)

| Component        | Responsibility |
|------------------|----------------|
| `watcher`        | Detects new photos in the synced folder, enqueues them |
| `classifier`     | Vision AI tags each photo: `tasks` / `notes` / `receipt` / `event` / `unknown` |
| `router`         | Dispatches each photo to the right extractor; `unknown` → on-screen review queue |
| `extractors/*`   | Photo type → structured records (tasks extractor is the MVP) |
| `bot`            | Receives voice/text commands ("done: gym") → mutates store |
| `store`          | Source of truth: **SQLite** (queries) + **Markdown mirror** (git-friendly, human-readable) |
| `renderer`       | Composes widget zones into a single grayscale PNG sized for the Boox panel |
| `widgets/*`      | Independent, pluggable zones (today, habits, month, extras) |
| `api`            | Serves `dashboard.png` + a monotonic `version` integer |

> **Code separation:** the Meta AI glasses integration (`watcher`, `classifier`,
> `router`, `extractors`, `bot`) lives under `server/app/glasses/`. The core
> (`config`, `store`, `theme`, `renderer`, `widgets`, `api`) is Meta-agnostic and
> never imports from `glasses/`, so the integration can be swapped or removed
> without touching the dashboard.

### Components (Pi client)

| Component                  | Responsibility |
|----------------------------|----------------|
| `display.py`               | Polls `api` for `version`; when it bumps, downloads + shows PNG fullscreen |
| `eink-dashboard.service`   | systemd unit to keep `display.py` running on boot |

## Capture loop (the killer feature)

1. Write today's tasks in your notebook.
2. "Hey Meta, take a picture" of the page.
3. Photo syncs to homelab via Syncthing.
4. `classifier` decides it's a `tasks` photo (**Option A: smart classify** — any photo type routes itself).
5. `tasks` extractor → structured JSON, deduped against existing tasks.
6. Store updates → `version` bumps → Pi re-displays.

**Write-back:** glasses send a WhatsApp message to a self-hosted bot ("done: gym",
"add: call dentist") → bot updates the store. Voice → text → action, no typing.

## Dashboard layout

Three always-visible time horizons (zones, not screens):

```
┌────────────────────────────────────────────────────────┐
│  Tuesday, June 10        ☀ 72°        06:00 → 22:00     │  header
├──────────────────────────┬─────────────────────────────┤
│  TODAY                    │  HABITS (this week)          │
│  ☐ Ship dashboard v1      │  Gym   ▣▣▣☐▢▢▢  3/5          │
│  ☑ Standup notes          │  Read  ▣▣▣▣▢▢▢  4/5          │
│  ☐ Call dentist           │  STREAKS 🔥 Gym 12d          │
├──────────────────────────┼─────────────────────────────┤
│  WEEK AT A GLANCE         │  THIS MONTH                  │
│  M ▓▓░ T ▓▓▓ W ▓░░ ...     │  ▸ Q2 goal 60% ████░░        │
├──────────────────────────┴─────────────────────────────┤
│  daily focus quote                                      │
└────────────────────────────────────────────────────────┘
```

## E-ink refresh strategy

E-ink is slow, grayscale, ghosts over time. So:

- Header/clock: light refresh hourly.
- Task/habit zones: refresh on change only.
- Full ghosting-clear refresh: 1–2× per day.
- Pi displays a new image **only when `version` changes** → no needless flicker.

## Failure handling

- Vision AI unsure → record lands in an on-screen **⚠️ review zone**, never silently dropped.
- Low-confidence handwriting reads → shown with a `?`, fixable by voice.
- Server down → Pi keeps showing the **last good image** (never blank).
- Duplicate photo of same page → dedup by content hash + fuzzy task matching.

## Data model (initial)

```
task(id, text, status, source_photo, confidence, created_at, done_at)
habit(id, name, cadence, target_per_week)
habit_log(id, habit_id, date, count)
goal(id, text, horizon[month|quarter], progress, due)
photo(id, hash, type, processed_at, status)
```

SQLite is the query engine; a Markdown mirror (`data/tasks.md`, `data/habits.md`)
is written alongside so the state is human-readable and git-committable.

## Future add-ons (banked, pluggable widgets)

- **Week of the year** (`Week 24 / 52`) and **year progress bar**
- **Life in weeks** (90-year dot grid, today highlighted)
- **Time-of-day completion heatmap** (find your real peak hours)
- **Daily one-line journal** (dictated) + "1 year ago today"
- **Sunday weekly-review mode** (wins / misses / next 3 big rocks)
- **Goal → habit linkage** (each goal shows the habits feeding it)
- **Now/Next focus banner** (from calendar, once calendar is integrated)
- **Habit over-commitment warning**

Each is a self-contained widget the renderer can drop into a zone — no Pi changes needed.

## Tech choices

- **Language:** Python (server + Pi client)
- **Vision AI:** pluggable — Claude API (default), or a local VLM later for full self-hosting
- **Containers:** Docker Compose on the homelab
- **Photo bridge:** Syncthing (phone → server), no cloud
- **Voice write-back:** self-hosted WhatsApp/Messenger bot (later phase)

## Build phases

1. **Skeleton** (this commit) — structure, stubs, compose file, design doc.
2. **Render path** — store → renderer → PNG → api → Pi display. Get *something* on the Boox.
3. **Capture path** — watcher → classifier → tasks extractor → store.
4. **Write-back** — bot listener for voice commands.
5. **Add-ons** — pull widgets from the banked list as desired.

## Out of scope (YAGNI for now)

- Real-time / sub-minute updates (e-ink can't and shouldn't)
- Multi-user
- Calendar integration (phase 5+)
- Color (panel is grayscale)
