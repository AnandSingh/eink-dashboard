"""Banked add-on widgets — drop into any free zone when you want them.

These are intentionally tiny and self-contained. Implement as desired.
"""


def render_week_of_year(draw, box, data) -> None:
    """`Week 24 / 52` with a 52-dot grid, current week filled. TODO."""
    raise NotImplementedError


def render_year_progress(draw, box, data) -> None:
    """`2026 ████████░░░░ 44%`. TODO."""
    raise NotImplementedError


def render_life_in_weeks(draw, box, data) -> None:
    """90-year (4680-dot) life grid, today highlighted. TODO.

    data = {"birthdate": "YYYY-MM-DD"}
    """
    raise NotImplementedError
