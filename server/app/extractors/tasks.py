"""Task extractor (MVP) — notebook page photo → structured tasks.

This is the heart of the system: handwriting → checkable tasks on the dashboard.
"""

# Vision prompt used to pull a clean task list out of a handwritten page.
EXTRACT_PROMPT = """\
You are reading a photo of a handwritten daily to-do list from a notebook.
Return JSON: a list of tasks, each with:
  - text: the task, cleaned up (fix obvious handwriting/spelling)
  - status: "done" if crossed out / checked, else "todo"
  - confidence: 0..1 how sure you are you read it correctly
Ignore doodles, dates, and headers. Only return the tasks.
"""


def extract(image_path: str, photo_hash: str, classify_confidence: float) -> None:
    """Extract tasks from a notebook photo and merge into the store.

    Steps (TODO):
      1. Call vision model with EXTRACT_PROMPT + the image.
      2. Parse JSON list of {text, status, confidence}.
      3. Dedup against existing open tasks (fuzzy match on text).
      4. store.add_tasks(new_tasks, source_photo=photo_hash).
      5. Low-confidence tasks get flagged with '?' for voice correction.
    """
    raise NotImplementedError("tasks.extract — phase 3")
