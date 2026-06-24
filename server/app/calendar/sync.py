"""Background calendar poller.

One daemon thread (mirrors glasses/watcher.py). It re-evaluates the banner every
render-tick (so "now" stays fresh) but only re-fetches the .ics every poll
interval. Rendering goes through renderer.render_if_changed(), so the screen only
refreshes when the image actually changes.
"""
import datetime as dt
import logging
import threading
import time
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..config import config
from .. import renderer, store
from . import source

log = logging.getLogger(__name__)


def _tz():
    try:
        return ZoneInfo(config.calendar_tz)
    except (ZoneInfoNotFoundError, ValueError):
        log.warning("invalid CALENDAR_TZ %r; falling back to UTC", config.calendar_tz)
        return dt.timezone.utc


def fetch_once() -> bool:
    """Fetch + store events. Returns True on success; keeps last-good state on error."""
    try:
        ics = source.fetch_ics(config.calendar_ics_url)
        events = source.parse_events(ics, _tz())
        store.replace_events(events)
        log.info("calendar synced: %d events", len(events))
        return True
    except Exception:
        log.exception("calendar fetch failed; keeping last-good events")
        return False


def _loop() -> None:
    poll = max(1, config.calendar_poll_minutes) * 60
    tick = max(1, config.calendar_render_tick_minutes) * 60
    last_fetch = 0.0
    while True:
        now = time.monotonic()
        if now - last_fetch >= poll:
            # On failure, leave last_fetch unchanged so we retry on the next tick
            # instead of waiting a full poll interval.
            if fetch_once():
                last_fetch = now
        try:
            renderer.render_if_changed()
        except Exception:
            log.exception("render after calendar tick failed")
        time.sleep(tick)


def start_background() -> None:
    """Launch the poller in a daemon thread. No-op if no calendar URL is set."""
    if not config.calendar_ics_url:
        log.info("calendar disabled (CALENDAR_ICS_URL unset)")
        return
    threading.Thread(target=_loop, name="calendar-sync", daemon=True).start()
    log.info("calendar poller started (poll %dm, tick %dm)",
             config.calendar_poll_minutes, config.calendar_render_tick_minutes)
