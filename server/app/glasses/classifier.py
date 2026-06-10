"""Vision AI photo classifier (Option A: smart classify).

Given a photo, decide what it is so the router can pick an extractor.
"""
from enum import Enum

from . import vision


class PhotoType(str, Enum):
    TASKS = "tasks"        # a notebook to-do list page
    NOTES = "notes"        # whiteboard / freeform notes
    RECEIPT = "receipt"    # an expense
    EVENT = "event"        # a poster/invite with a date
    UNKNOWN = "unknown"    # → on-screen review queue


CLASSIFY_PROMPT = """\
Look at this photo and classify it into exactly one category:
  - "tasks": a handwritten or printed to-do / task list (e.g. a notebook page)
  - "notes": freeform notes, a whiteboard, or a diagram
  - "receipt": a purchase receipt or invoice
  - "event": a poster, invite, or flyer with a date/time
  - "unknown": none of the above, or you can't tell
Return the category and your confidence (0..1).
"""

# Below this confidence we treat the classification as unknown → review queue.
_MIN_CONFIDENCE = 0.5


def classify(image_path: str) -> tuple[PhotoType, float]:
    """Return (type, confidence 0..1)."""
    result = vision.classify(image_path, CLASSIFY_PROMPT)
    try:
        photo_type = PhotoType(result.type)
    except ValueError:
        photo_type = PhotoType.UNKNOWN

    if result.confidence < _MIN_CONFIDENCE:
        photo_type = PhotoType.UNKNOWN
    return photo_type, result.confidence
