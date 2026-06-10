"""Task extractor (MVP) — notebook page photo → structured tasks.

This is the heart of the system: handwriting → checkable tasks on the dashboard.
"""
from .. import vision
from ... import store

# Vision prompt used to pull a clean task list out of a handwritten page.
EXTRACT_PROMPT = """\
You are reading a photo of a handwritten daily to-do list from a notebook.
Return JSON: a list of tasks, each with:
  - text: the task, cleaned up (fix obvious handwriting/spelling)
  - status: "done" if crossed out / checked, else "todo"
  - confidence: 0..1 how sure you are you read it correctly
Ignore doodles, dates, and headers. Only return the tasks.
"""


def extract(image_path: str, photo_hash: str, classify_confidence: float) -> int:
    """Extract tasks from a notebook photo and merge into the store.

    Returns the number of new tasks added (after dedup).
    """
    extracted = vision.extract_tasks(image_path, EXTRACT_PROMPT)
    tasks = [
        {
            "text": t.text,
            "status": t.status if t.status in ("todo", "done") else "todo",
            "confidence": t.confidence,
        }
        for t in extracted
        if t.text.strip()
    ]
    return store.add_tasks(tasks, source_photo=photo_hash)
