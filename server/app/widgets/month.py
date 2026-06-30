"""THIS MONTH zone — goals / big rocks with progress bars."""
import datetime as dt

from .. import theme


def _due_text(due_str: str | None, today: dt.date) -> str | None:
    """Format a due date as a countdown: '12d left', 'due today', '3d overdue'.

    Returns None if due_str is falsy. Falls back to 'due <raw>' if unparseable.
    """
    if not due_str:
        return None
    try:
        due = dt.date.fromisoformat(due_str)
    except (ValueError, TypeError):
        return f"due {due_str}"
    diff = (due - today).days
    if diff > 0:
        return f"{diff}d left"
    elif diff == 0:
        return "due today"
    else:
        return f"{-diff}d overdue"


def render(draw, box, data) -> None:
    """Draw monthly/quarterly goals with progress bars and due dates.

    data = {"goals": [{"text", "progress", "due"}], "today": date, ...}
    """
    x, y, w, h = box
    pad = 28
    draw.text((x + pad, y + pad), "THIS MONTH",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    today = data.get("today", dt.date.today())
    f = theme.font(30)
    df = theme.font(22)
    pct_room = 90               # leave space for the trailing "NN%" label
    bar_w = w - 2 * pad - pct_room
    bar_h = 22
    ty = y + pad + 64
    for goal in data.get("goals", []):
        draw.text((x + pad, ty), "▸ " + goal["text"], font=f, fill=theme.INK)
        due_txt = _due_text(goal.get("due"), today)
        if due_txt:
            tw = draw.textlength(due_txt, font=df)
            draw.text((x + w - pad - tw, ty + 4), due_txt, font=df, fill=theme.MUTED)
        ty += 44
        # progress bar
        bx = x + pad
        draw.rectangle([bx, ty, bx + bar_w, ty + bar_h], outline=theme.INK, width=2)
        fill_w = int(bar_w * max(0.0, min(1.0, goal.get("progress", 0))))
        if fill_w > 0:
            draw.rectangle([bx, ty, bx + fill_w, ty + bar_h], fill=theme.INK)
        pct = f"{int(goal.get('progress', 0) * 100)}%"
        draw.text((bx + bar_w + 12, ty - 4), pct, font=df, fill=theme.MUTED)
        ty += bar_h + 40
