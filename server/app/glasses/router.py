"""Route a classified photo to the correct extractor."""
from .classifier import classify, PhotoType
from .extractors import tasks, notes, receipt


_HANDLERS = {
    PhotoType.TASKS: tasks.extract,
    PhotoType.NOTES: notes.extract,
    PhotoType.RECEIPT: receipt.extract,
    # EVENT → calendar extractor (phase 5)
}


def route(image_path: str, photo_hash: str) -> None:
    """Classify and dispatch a single photo."""
    photo_type, confidence = classify(image_path)

    handler = _HANDLERS.get(photo_type)
    if handler is None:
        # Unknown / unsupported → review queue, shown on-screen, never dropped.
        # TODO: store.add_to_review(image_path, photo_hash, photo_type)
        return

    handler(image_path, photo_hash, confidence)
    # TODO: bump render version so the Pi refreshes (store.bump_version()).
