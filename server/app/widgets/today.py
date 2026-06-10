"""TODAY zone — today's tasks (from the notebook), with checkboxes."""
from .. import theme


def render(draw, box, data) -> None:
    """Draw today's task list.

    data = {"tasks": [{"text", "status", "confidence"}], ...}
    ☑ done, ☐ todo, trailing '?' for low-confidence reads.
    """
    x, y, w, h = box
    pad = 28
    draw.text((x + pad, y + pad), "TODAY", font=theme.font(34, bold=True), fill=theme.STRONG)

    line_h = 56
    box_sz = 30
    ty = y + pad + 60
    f = theme.font(32)
    for task in data.get("tasks", []):
        done = task["status"] == "done"
        bx = x + pad
        # checkbox
        draw.rectangle([bx, ty, bx + box_sz, ty + box_sz], outline=theme.INK, width=3)
        if done:
            draw.line([bx + 5, ty + box_sz // 2, bx + box_sz // 2, ty + box_sz - 6],
                      fill=theme.INK, width=4)
            draw.line([bx + box_sz // 2, ty + box_sz - 6, bx + box_sz - 4, ty + 5],
                      fill=theme.INK, width=4)

        text = task["text"]
        if task.get("confidence", 1.0) < 0.8:
            text += "  ?"          # low-confidence handwriting read
        fill = theme.MUTED if done else theme.INK
        draw.text((bx + box_sz + 18, ty - 2), text, font=f, fill=fill)

        if done:  # strike-through
            tw = draw.textlength(text, font=f)
            sy = ty + box_sz // 2
            draw.line([bx + box_sz + 18, sy, bx + box_sz + 18 + tw, sy],
                      fill=theme.MUTED, width=2)
        ty += line_h
