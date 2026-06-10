"""Route a classified photo to the correct extractor."""
import logging

from .. import renderer, store
from .classifier import classify, PhotoType
from .extractors import tasks, notes, receipt

log = logging.getLogger(__name__)

_HANDLERS = {
    PhotoType.TASKS: tasks.extract,
    PhotoType.NOTES: notes.extract,
    PhotoType.RECEIPT: receipt.extract,
    # EVENT → calendar extractor (phase 5)
}


def route(image_path: str, photo_hash: str) -> None:
    """Classify and dispatch a single photo, then refresh the dashboard."""
    photo_type, confidence = classify(image_path)
    log.info("photo %s classified as %s (%.2f)", photo_hash[:8], photo_type, confidence)

    handler = _HANDLERS.get(photo_type)
    if handler is None:
        # Unknown / unsupported → recorded for the on-screen review queue,
        # never silently dropped. (Review widget lands in a later phase.)
        store.record_photo(photo_hash, photo_type.value, status="review")
        log.info("photo %s → review queue", photo_hash[:8])
        return

    try:
        handler(image_path, photo_hash, confidence)
        store.record_photo(photo_hash, photo_type.value, status="processed")
    except Exception:
        log.exception("handler failed for %s", photo_hash[:8])
        store.record_photo(photo_hash, photo_type.value, status="error")
        return

    # State changed → re-render the PNG and bump the version so the Pi refreshes.
    store.bump_version()
    renderer.render()
