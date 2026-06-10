"""Watch the synced photo inbox and enqueue new photos for processing.

Photos arrive from the Android phone via Syncthing. We poll the inbox folder
(simple and robust for synced dirs), hash each file to skip duplicates, and
hand new ones to the router.
"""
import hashlib
import logging
import os
import threading
import time

from ..config import config
from .. import store
from . import router

log = logging.getLogger(__name__)

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
_POLL_SECONDS = 5


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def process_new_photo(path: str) -> None:
    """Entry point for a single newly-arrived photo."""
    photo_hash = _hash_file(path)
    if store.photo_exists(photo_hash):
        return  # already handled (e.g. Syncthing re-touched the file)
    router.route(path, photo_hash)


def _scan_once() -> None:
    for name in sorted(os.listdir(config.inbox_dir)):
        if os.path.splitext(name)[1].lower() not in _IMAGE_EXTS:
            continue
        path = os.path.join(config.inbox_dir, name)
        if not os.path.isfile(path):
            continue
        try:
            process_new_photo(path)
        except Exception:
            log.exception("failed to process %s", name)


def watch() -> None:
    """Long-running loop polling INBOX_DIR for new photos."""
    os.makedirs(config.inbox_dir, exist_ok=True)
    log.info("watching %s for new photos", config.inbox_dir)
    while True:
        _scan_once()
        time.sleep(_POLL_SECONDS)


def start_background() -> None:
    """Launch the watcher in a daemon thread (called from the API on startup)."""
    thread = threading.Thread(target=watch, name="photo-watcher", daemon=True)
    thread.start()
