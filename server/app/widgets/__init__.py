"""Pluggable dashboard widgets.

Each widget renders one zone onto a PIL drawing context within a given box.
Add new widgets (week-of-year, life-in-weeks, …) without touching the Pi.

Convention:
    def render(draw, box, data) -> None
        draw: PIL.ImageDraw.ImageDraw
        box:  (x, y, w, h) the zone's rectangle
        data: dict the widget needs from the store
"""
