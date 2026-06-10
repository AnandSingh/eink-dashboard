"""Vision AI photo classifier (Option A: smart classify).

Given a photo, decide what it is so the router can pick an extractor.
"""
from enum import Enum


class PhotoType(str, Enum):
    TASKS = "tasks"        # a notebook to-do list page
    NOTES = "notes"        # whiteboard / freeform notes
    RECEIPT = "receipt"    # an expense
    EVENT = "event"        # a poster/invite with a date
    UNKNOWN = "unknown"    # → on-screen review queue


def classify(image_path: str) -> tuple[PhotoType, float]:
    """Return (type, confidence 0..1).

    TODO: call the vision model with a classification prompt and parse the
    JSON result. Low confidence → PhotoType.UNKNOWN so it lands in review.
    """
    raise NotImplementedError("classify — phase 3")
