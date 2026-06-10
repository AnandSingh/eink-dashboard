"""Watch the synced photo inbox and enqueue new photos for processing.

Photos arrive from the Android phone via Syncthing. We detect new files,
hash them to skip duplicates, and hand each to the router.
"""
import hashlib
import os

from .config import config
from . import router


def _hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def process_new_photo(path: str) -> None:
    """Entry point for a single newly-arrived photo."""
    photo_hash = _hash_file(path)
    # TODO: skip if photo_hash already seen (store.photo_exists)
    router.route(path, photo_hash)


def watch() -> None:
    """Long-running loop watching INBOX_DIR.

    TODO: replace the naive scan with watchdog.Observer for real events.
    """
    os.makedirs(config.inbox_dir, exist_ok=True)
    raise NotImplementedError("watch loop — phase 3")
