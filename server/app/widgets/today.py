"""TODAY zone — today's tasks (from the notebook), with checkboxes."""


def render(draw, box, data) -> None:
    """Draw today's task list.

    data = {"tasks": [{"text", "status", "confidence"}], ...}
    Render ☑ for done, ☐ for todo, and a trailing '?' for low confidence.
    TODO: implement with PIL text + checkbox glyphs.
    """
    raise NotImplementedError("today widget — phase 2")
