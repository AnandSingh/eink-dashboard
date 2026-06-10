"""THIS MONTH zone — goals / big rocks with progress bars."""
from .. import theme


def render(draw, box, data) -> None:
    """Draw monthly/quarterly goals with progress bars and due dates.

    data = {"goals": [{"text", "progress", "due"}], ...}
    """
    x, y, w, h = box
    pad = 28
    draw.text((x + pad, y + pad), "THIS MONTH",
              font=theme.font(34, bold=True), fill=theme.STRONG)

    f = theme.font(30)
    df = theme.font(22)
    pct_room = 90               # leave space for the trailing "NN%" label
    bar_w = w - 2 * pad - pct_room
    bar_h = 22
    ty = y + pad + 64
    for goal in data.get("goals", []):
        draw.text((x + pad, ty), "▸ " + goal["text"], font=f, fill=theme.INK)
        if goal.get("due"):
            due_txt = "due " + goal["due"][5:]  # MM-DD
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
