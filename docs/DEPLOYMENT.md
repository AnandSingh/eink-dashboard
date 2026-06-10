# Deployment Guide

Getting the e-ink dashboard running on real hardware. Four independent parts —
do them in order; each is verifiable on its own.

```
✍️ notebook → 👓 glasses → 📱 phone ──(B: Syncthing)──▶ 🖥️ homelab (A: Docker)
                                                              │
🗣️ "done: gym" → WhatsApp ──(C: webhook)──────────────────▶  │
                                                              ▼
                                            renders dashboard.png + /version
                                                              │ (D: HTTP pull)
                                                              ▼
                                          🥧 Raspberry Pi → HDMI → 📊 Boox 32"
```

## Prerequisites

- A homelab box that runs Docker (Linux).
- An Android phone paired with the Meta AI glasses.
- A Raspberry Pi (any model with HDMI; Pi 3/4/Zero 2 W all fine).
- The Boox 32" monitor + an HDMI cable.
- (Optional, for voice) a public HTTPS URL to your homelab — see Part C.

---

## Part A — Homelab server (Docker)

1. Clone and configure:

   ```bash
   git clone <your-repo-url> ~/eink-dashboard
   cd ~/eink-dashboard
   cp .env.example .env
   ```

2. Edit `.env`:

   ```ini
   VISION_PROVIDER=anthropic          # or 'mock' to run with no API key
   ANTHROPIC_API_KEY=sk-ant-...       # your key
   PANEL_WIDTH=2560                   # set to your Boox's real resolution
   PANEL_HEIGHT=1440
   # optional add-on widget:
   # BOTTOM_LEFT_WIDGET=life
   # BIRTHDATE=1994-03-15
   ```

3. Point the inbox at the folder Syncthing will write to (Part B). In
   `docker-compose.yml`, set the host path it mounts to `/data/inbox`:

   ```yaml
   volumes:
     - /srv/eink/inbox:/data/inbox     # <- Syncthing target on the host
     - ./data:/data
   ```

   (or set `INBOX_DIR_HOST=/srv/eink/inbox` in `.env` if you wire it that way).

4. Launch:

   ```bash
   docker compose up -d --build
   ```

5. Verify the server is up and rendering:

   ```bash
   curl -s localhost:8080/healthz          # {"ok": true}
   curl -s localhost:8080/version          # {"version": N}
   curl -s localhost:8080/dashboard.png -o /tmp/dash.png && xdg-open /tmp/dash.png
   ```

   On first run it seeds demo data so you see a real dashboard immediately.

---

## Part B — Phone → homelab photo sync (Syncthing)

The glasses save photos to the phone; Syncthing mirrors that folder to the
homelab inbox the watcher polls.

1. **On the homelab**, run Syncthing (uncomment the `syncthing` service in
   `docker-compose.yml`, or install it natively). Open its UI at
   `http://<homelab>:8384`. Add a folder pointed at the **same host path** you
   mounted as `/data/inbox` (e.g. `/srv/eink/inbox`), set to **Receive Only**.

2. **On Android**, install Syncthing (F-Droid or Play Store). Add the homelab as
   a remote device (scan the QR in the homelab UI). Share a folder that contains
   the glasses photos:
   - The Meta AI app saves glasses media into the phone gallery. Point Syncthing
     at that folder (commonly `DCIM/` or a `Meta View` / `Meta AI` subfolder —
     check where your app drops them), set to **Send Only**.
   - Tip: if it dumps into the main camera roll, create a phone-side automation
     (e.g. an app like FolderSync/Tasker) to copy only glasses photos into a
     dedicated `glasses-inbox/` folder, and sync *that* — keeps random selfies
     off your dashboard.

3. **Verify:** take a photo of a notebook page with the glasses → it appears in
   the phone folder → shows up in `/srv/eink/inbox` on the homelab within seconds
   → the watcher logs `photo … classified as tasks` and the dashboard updates.

   ```bash
   docker compose logs -f server | grep photo
   curl -s localhost:8080/version    # should increment after a photo lands
   ```

Supported image types: `.jpg .jpeg .png .webp`. Duplicates (same bytes) are
skipped automatically.

---

## Part C — Voice write-back (WhatsApp → /bot)

Lets you say "Hey Meta, send 'done: gym' to <contact>" and have it check off on
the dashboard. The webhook must be reachable from the public internet over HTTPS.

### 1. Expose the server over HTTPS

Pick one:
- **Cloudflare Tunnel** (recommended, free): `cloudflared tunnel --url http://localhost:8080`
  → gives you a `https://<random>.trycloudflare.com` URL. For a stable URL,
  set up a named tunnel against your domain.
- **Tailscale Funnel**, an existing reverse proxy (Caddy/nginx + Let's Encrypt),
  or ngrok — any HTTPS front end to port 8080 works.

### 2. Set up WhatsApp Cloud API

1. Create a Meta for Developers app → add the **WhatsApp** product (free test
   number to start).
2. Set a verify token of your choosing and add it to `.env`, then restart:

   ```ini
   WHATSAPP_VERIFY_TOKEN=some-long-random-string
   WHATSAPP_TOKEN=<graph-api-token>     # only needed to send replies back
   ```

3. In the app's WhatsApp → Configuration, set the **Callback URL** to
   `https://<your-public-url>/bot` and the **Verify Token** to the same string.
   Subscribe to the `messages` field. Meta calls `GET /bot` to verify — the
   server echoes the challenge automatically.

4. **Verify:** send a WhatsApp message `add buy milk` to your WhatsApp number.
   The webhook fires, the task appears on the dashboard, and `/version` bumps.

   Commands: `add <task>` · `done <task or habit>` · `log <habit>`.

### 3. Drive it from the glasses

"Hey Meta, send a message to <your WhatsApp contact>: done gym." The glasses
dictate it to WhatsApp → your webhook → dashboard.

> No public URL yet? You can still test locally:
> `curl -s localhost:8080/bot -H 'content-type: application/json' -d '{"text":"add buy milk","sender":"me"}'`

---

## Part D — Raspberry Pi client → Boox

The Pi just fetches the PNG and shows it fullscreen. Full steps in
[`pi-client/install.md`](../pi-client/install.md); summary:

1. Connect Pi → HDMI → Boox. Set the Pi's HDMI output to the Boox's native
   resolution (match `PANEL_WIDTH`/`PANEL_HEIGHT`).
2. Install deps and the client:

   ```bash
   sudo apt update && sudo apt install -y python3 feh
   git clone <your-repo-url> ~/eink-dashboard
   ```

3. Point it at the homelab and run on boot:

   ```bash
   # edit DASHBOARD_SERVER in the unit, then:
   sudo cp ~/eink-dashboard/pi-client/eink-dashboard.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now eink-dashboard
   journalctl -u eink-dashboard -f
   ```

The client polls `/version` and only redraws when it changes — no needless
e-ink flicker. If the server is down, it keeps showing the last good image.

---

## End-to-end check

1. Server: `curl /healthz` → ok.
2. Photograph a notebook page → dashboard updates (Part B).
3. WhatsApp `done <task>` → it checks off (Part C).
4. The Boox reflects both within a minute (Part D).

## Troubleshooting

| Symptom | Check |
|---|---|
| Dashboard blank on Boox | Pi HDMI resolution; `journalctl -u eink-dashboard`; is `DASHBOARD_SERVER` reachable? |
| Photos not appearing | Syncthing folder paths match the `/data/inbox` mount; file extension supported; `docker compose logs server` |
| Tasks garbled / missing | Using `mock`? Set `VISION_PROVIDER=anthropic` + a real `ANTHROPIC_API_KEY`; check logs for API errors |
| WhatsApp webhook won't verify | `WHATSAPP_VERIFY_TOKEN` matches the value in the Meta console; callback URL ends in `/bot`; HTTPS reachable |
| E-ink ghosting builds up | trigger a full clear-refresh from the Boox settings (or add a daily full-refresh later) |
