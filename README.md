# eink-dashboard

A self-hosted **productivity magic mirror** for a 32" Boox e-ink monitor.

Write tasks in a paper notebook → photograph them with Meta Ray-Ban AI glasses →
AI extracts them → they appear on an always-on, glare-free e-ink dashboard showing
your **day / week / month** at a glance.

Fully self-hosted: a homelab server does all the work; a Raspberry Pi is a dumb
display client driving the Boox over HDMI.

> Full design: [`docs/plans/2026-06-10-eink-dashboard-design.md`](docs/plans/2026-06-10-eink-dashboard-design.md)
> Deploy on real hardware: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)

## Architecture

```
notebook → 👓 glasses photo → 📱 phone → (Syncthing) → 🖥️ homelab server
                                                            │
                              watcher → classifier → router → extractors → store
                                                            │
                                          renderer → dashboard.png → api
                                                            │  (HTTP pull)
                                                            ▼
                                              🖥️ Raspberry Pi → HDMI → 📊 Boox 32"
```

## Layout

```
server/      Docker service: ingest photos, store state, render the dashboard PNG
  app/
    # --- core (Meta-agnostic) ---
    config.py         env-driven config
    store.py          SQLite + Markdown source of truth
    theme.py          fonts + grayscale palette
    renderer.py       compose widgets → grayscale PNG
    widgets/          pluggable dashboard zones (today, habits, week, month, extras)
    api.py            serve dashboard.png + a version number
    # --- Meta AI glasses integration (kept separate) ---
    glasses/
      watcher.py      watch the synced photo folder
      classifier.py   vision AI: what kind of photo is this?
      router.py       route photo → extractor
      extractors/     photo type → structured records (tasks is the MVP)
      bot.py          voice/text write-back ("done: gym")
pi-client/   Runs on the Raspberry Pi: fetch the PNG, show it fullscreen
docs/        Design docs
data/        Runtime state (gitignored)
```

> **Note:** everything Meta-glasses-specific lives under `server/app/glasses/`.
> The core never imports from it, so the glasses integration can be swapped or
> removed without touching the dashboard.

## Status

🟢 **Phases 2–5 complete.**
- **Render path** — store → renderer → `dashboard.png`, served by the API.
- **Capture path** — `glasses/` watches the synced photo folder → vision AI
  classifies + extracts tasks → store → dashboard re-renders, version bumps.
- **Voice write-back** — `/bot` webhook accepts voice/text commands and updates
  the dashboard:
  - `add <task>` — add a task
  - `done <task or habit>` — check off a task (falls back to logging a habit)
  - `log <habit>` — log a habit for today

  Understands both a generic `{"text","sender"}` body and the WhatsApp Cloud API
  payload (with the verification handshake), so the glasses can drive it by voice.

- **Add-on widgets** — a time-awareness footer strip (year progress · week-of-year ·
  life lived) plus a selectable bottom-left zone via `BOTTOM_LEFT_WIDGET`:
  `week` (default) · `weekofyear` · `yearprogress` · `life` (life-in-weeks grid,
  needs `BIRTHDATE`).

Runs **without an API key** out of the box: set `VISION_PROVIDER=mock` (or leave
`ANTHROPIC_API_KEY` empty) and the pipeline uses canned vision results so you can
exercise the whole flow. Set a real key to read actual notebook photos.

All five build phases are complete. 🎉

![dashboard preview](docs/dashboard-preview.png)

## Quick start (homelab server)

```bash
cp .env.example .env        # fill in vision AI key + paths
docker compose up -d --build
```

## Quick start (Raspberry Pi)

See [`pi-client/install.md`](pi-client/install.md).

## Phases

1. ✅ Skeleton (this repo)
2. ✅ Render path: store → PNG → api → Pi
3. ✅ Capture path: watcher → classifier → tasks extractor
4. ✅ Voice write-back bot
5. ✅ Add-on widgets (week-of-year, life-in-weeks, …)
