# eink-dashboard

A self-hosted **productivity magic mirror** for a 32" Boox e-ink monitor.

Write tasks in a paper notebook → photograph them with Meta Ray-Ban AI glasses →
AI extracts them → they appear on an always-on, glare-free e-ink dashboard showing
your **day / week / month** at a glance.

Fully self-hosted: a homelab server does all the work; a Raspberry Pi is a dumb
display client driving the Boox over HDMI.

> Full design: [`docs/plans/2026-06-10-eink-dashboard-design.md`](docs/plans/2026-06-10-eink-dashboard-design.md)

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

🟢 **Phase 2 complete** — the render path works: store → renderer → `dashboard.png`,
served by the API. Demo data seeds on first run so you see a real dashboard.
Phases 3+ (glasses capture, voice bot) are stubbed and marked `TODO`.

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
2. ⬜ Render path: store → PNG → api → Pi
3. ⬜ Capture path: watcher → classifier → tasks extractor
4. ⬜ Voice write-back bot
5. ⬜ Add-on widgets (week-of-year, life-in-weeks, …)
