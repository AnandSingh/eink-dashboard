"""Pure core for Sunday weekly-review mode.

Given habits / a task-done count / goals / today, produce the strings the
review widget draws. No I/O, no store import → fully unit-testable
(see tests/test_review.py). Drawing lives in widgets/review.py.
"""
import datetime as dt

_MAX_WINS = 3
_MAX_MISSES = 3
_MAX_ROCKS = 3


def _parse_due(due) -> dt.date | None:
    """Parse a goal `due` (ISO date string, possibly with a time part) → date.

    Defensive like renderer._parse_date: any bad/None input → None.
    """
    if not due:
        return None
    try:
        return dt.date.fromisoformat(str(due)[:10])
    except (ValueError, TypeError):
        return None


def _due_suffix(goal: dict, today: dt.date) -> str:
    """Trailing label for a focus goal: relative due if dated, else progress %."""
    d = _parse_due(goal.get("due"))
    if d is None:
        return f"{int(round(goal.get('progress', 0) * 100))}%"
    n = (d - today).days
    if n > 0:
        return f"due {n}d"
    if n == 0:
        return "due today"
    return "overdue"


def build_review(habits: list[dict], tasks_done_count: int,
                 goals: list[dict], today: dt.date) -> dict:
    """Return {"wins": [str], "misses": [str], "rocks": [str]}.

    - wins/misses come from habits with a positive target (done≥target → win,
      else miss), plus an "N tasks done" win when N>0. Each list is capped so it
      renders as a single compact line.
    - rocks are the top goals: those with a parseable due date first (soonest
      first), then undated goals by lowest progress; ties broken by id for a
      deterministic cut (avoids spurious e-ink refreshes).
    """
    # Habits with a usable target, tagged with a stable index for tie-breaks.
    targeted = [
        (i, h) for i, h in enumerate(habits)
        if h.get("target") and h["target"] > 0
    ]

    wins_h = sorted(
        (h for _, h in targeted if h["done"] >= h["target"]),
        key=lambda h: (-(h["done"] / h["target"]), habits.index(h)),
    )
    wins = [f"{h['name']} {h['done']}/{h['target']}" for h in wins_h]
    if tasks_done_count > 0:
        wins.append(f"{tasks_done_count} tasks done")
    wins = wins[:_MAX_WINS]

    misses_h = sorted(
        (h for _, h in targeted if h["done"] < h["target"]),
        key=lambda h: (-(h["target"] - h["done"]), habits.index(h)),
    )
    misses = [f"{h['name']} {h['done']}/{h['target']}" for h in misses_h][:_MAX_MISSES]

    dated, undated = [], []
    for g in goals:
        (dated if _parse_due(g.get("due")) else undated).append(g)
    dated.sort(key=lambda g: (_parse_due(g["due"]), g.get("id", 0)))
    undated.sort(key=lambda g: (g.get("progress", 0), g.get("id", 0)))
    rocks = [
        f"{g['text']} ({_due_suffix(g, today)})"
        for g in (dated + undated)[:_MAX_ROCKS]
    ]

    return {"wins": wins, "misses": misses, "rocks": rocks}
