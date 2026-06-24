"""Background weather poller (mirrors calendar/sync.py).

Polls Open-Meteo every WEATHER_POLL_MINUTES, stores the snapshot, and re-renders
via the change-gated path. Keeps last-good data on any failure.
"""
import json
import logging
import threading
import time

from ..config import config
from .. import renderer, store
from . import source

log = logging.getLogger(__name__)


def fetch_once() -> bool:
    """Fetch + store a weather snapshot. Keeps last-good on failure."""
    try:
        snap = source.fetch_snapshot()
        if snap is None:
            return False
        store.set_meta("weather", json.dumps(snap))
        log.info("weather synced: %s°, code %s, %s",
                 round(snap["temp"]), snap["code"], snap.get("city", ""))
        return True
    except Exception:
        log.exception("weather fetch failed; keeping last-good")
        return False


def _loop() -> None:
    poll = max(1, config.weather_poll_minutes) * 60
    last_fetch = 0.0
    while True:
        now = time.monotonic()
        if now - last_fetch >= poll:
            if fetch_once():
                last_fetch = now
                try:
                    renderer.render_if_changed()
                except Exception:
                    log.exception("render after weather sync failed")
        time.sleep(min(poll, 60))


def start_background() -> None:
    """Launch the poller in a daemon thread. No-op if weather is disabled."""
    if not config.weather_enabled:
        log.info("weather disabled (WEATHER_ENABLED=false)")
        return
    threading.Thread(target=_loop, name="weather-sync", daemon=True).start()
    log.info("weather poller started (poll %dm)", config.weather_poll_minutes)
