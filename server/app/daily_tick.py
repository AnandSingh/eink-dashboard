"""Core always-on re-render tick.

The calendar/weather pollers and glasses events are the only other re-render
paths, and all are optional. Without this, with every integration disabled, the
dashboard would never re-render on its own — the header date would freeze and
Sunday-review mode would never activate. This daemon calls render_if_changed()
on a fixed cadence; that path hashes the PNG and only bumps the version on a real
pixel change, so idle ticks cause zero extra e-ink refreshes.

Being core (no feature dependency), it is started from api.py's core startup hook,
not from main.py's optional-integration wiring.
"""
import logging
import threading
import time

from .config import config
from . import renderer

log = logging.getLogger(__name__)


def _loop() -> None:
    interval = max(1, config.daily_tick_minutes) * 60
    while True:
        time.sleep(interval)
        try:
            renderer.render_if_changed()
        except Exception:
            log.exception("daily tick render failed")


def start_background() -> None:
    """Launch the tick in a daemon thread. Always on (core, ungated)."""
    threading.Thread(target=_loop, name="daily-tick", daemon=True).start()
    log.info("daily tick started (every %dm)", config.daily_tick_minutes)
