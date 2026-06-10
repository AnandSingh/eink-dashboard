"""Raspberry Pi display client.

Dumb on purpose: poll the server's /version; when it changes, download
/dashboard.png and show it fullscreen on the Boox over HDMI.

Uses `feh` for fullscreen image display (lightweight, X-based). For a pure
framebuffer setup (no X), swap in `fbi` instead — see install.md.
"""
import os
import subprocess
import time
import urllib.request

SERVER = os.getenv("DASHBOARD_SERVER", "http://homelab.local:8080")
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "60"))
IMG_PATH = "/tmp/dashboard.png"


def get_version() -> int | None:
    try:
        with urllib.request.urlopen(f"{SERVER}/version", timeout=10) as r:
            import json
            return int(json.load(r)["version"])
    except Exception:
        return None  # server down → keep showing last good image


def download_png() -> bool:
    try:
        urllib.request.urlretrieve(f"{SERVER}/dashboard.png", IMG_PATH)
        return True
    except Exception:
        return False


def show(path: str) -> None:
    # feh: fullscreen, no decorations, auto-zoom to screen.
    subprocess.Popen(
        ["feh", "--fullscreen", "--hide-pointer", "--zoom", "fill", path]
    )


def main() -> None:
    last = None
    while True:
        v = get_version()
        if v is not None and v != last and download_png():
            show(IMG_PATH)
            last = v
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
