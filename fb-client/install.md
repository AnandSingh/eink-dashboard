# fb-client — x86 / framebuffer display client

For an x86 mini-PC (or any Linux box with KMS graphics) driving an e-ink HDMI
monitor (e.g. Boox Mira Pro). Writes the dashboard PNG **straight to
`/dev/fb0`** as raw BGRA — no X, no browser, **no `fbi`**.

## Why not fbi / a browser
- `fbi` draws on a black background and does its own VT/refresh management, which
  renders badly on e-ink (dark/ghosty). A **direct framebuffer write** gives a
  clean full-frame update the panel refreshes cleanly.
- A browser (Chromium kiosk) repaints constantly — bad for e-ink ghosting.
- Change-gated: only redraws when the dashboard `/version` changes.
- E-ink shows **dark-on-light** best (no backlight), so keep the render normal
  (black text on white); do NOT invert. Enable `EINK_MODE` on the server for
  higher contrast.

## Install (Ubuntu/Debian)
```bash
sudo apt-get install -y imagemagick curl
sudo install -m0755 dashboard-fb.sh /usr/local/bin/dashboard-fb.sh
sudo install -m0644 dashboard-fb.service /etc/systemd/system/dashboard-fb.service
# free tty1 so no login prompt fights the framebuffer
sudo systemctl disable --now getty@tty1.service
sudo systemctl mask getty@tty1.service
sudo systemctl daemon-reload
sudo systemctl enable --now dashboard-fb.service
```
Set the server URL if not the default: `DASHBOARD_SERVER=https://dash.plexlab.site`
(env in the service). The framebuffer resolution is read from
`/sys/class/graphics/fb0/virtual_size`; the image is resized to match 1:1.

Requires a kernel new enough to drive the GPU via KMS (e.g. Intel Jasper Lake
needs 5.10+; the framebuffer must report the panel's native resolution).
