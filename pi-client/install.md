# Raspberry Pi client setup

The Pi just fetches the dashboard PNG and shows it fullscreen on the Boox.

## 1. Connect hardware

- Pi → HDMI → Boox 32" e-ink monitor.
- Set the Pi's HDMI output to the Boox's native resolution (match `PANEL_WIDTH`
  / `PANEL_HEIGHT` in the server `.env`).

## 2. Install dependencies

```bash
sudo apt update
sudo apt install -y python3 feh      # feh = fullscreen image viewer (X)
# Pure framebuffer (no desktop)? Use fbi instead:
# sudo apt install -y fbi
```

## 3. Get the client

```bash
git clone <your-repo-url> ~/eink-dashboard
```

## 4. Point it at your homelab

Edit `eink-dashboard.service` (or the env in step 5) so `DASHBOARD_SERVER`
matches your server, e.g. `http://homelab.local:8080`.

## 5. Run on boot

```bash
sudo cp ~/eink-dashboard/pi-client/eink-dashboard.service \
        /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now eink-dashboard
```

Check it:

```bash
systemctl status eink-dashboard
journalctl -u eink-dashboard -f
```

## Notes

- **Server down?** The client keeps showing the last image — never blank.
- **E-ink ghosting:** trigger a full clear refresh from the Boox settings, or
  add a daily full-refresh cycle later.
- **No desktop / framebuffer only:** replace the `feh` call in `display.py` with
  `fbi -d /dev/fb0 -T 1 -noverbose -a <img>` and drop `DISPLAY=:0`.
