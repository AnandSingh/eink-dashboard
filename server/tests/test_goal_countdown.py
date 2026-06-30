"""Tests for goal countdown format — due date → days left/overdue."""
import datetime as dt


def test_future_due():
    from app.widgets.month import _due_text
    assert _due_text("2026-07-12", dt.date(2026, 6, 30)) == "12d left"


def test_due_today():
    from app.widgets.month import _due_text
    assert _due_text("2026-06-30", dt.date(2026, 6, 30)) == "due today"


def test_past_due():
    from app.widgets.month import _due_text
    assert _due_text("2026-06-27", dt.date(2026, 6, 30)) == "3d overdue"


def test_no_due():
    from app.widgets.month import _due_text
    assert _due_text(None, dt.date(2026, 6, 30)) is None
    assert _due_text("", dt.date(2026, 6, 30)) is None


def test_unparseable_due():
    from app.widgets.month import _due_text
    assert _due_text("July", dt.date(2026, 6, 30)) == "due July"
    assert _due_text("2026", dt.date(2026, 6, 30)) == "due 2026"


def test_one_day_left():
    from app.widgets.month import _due_text
    assert _due_text("2026-07-01", dt.date(2026, 6, 30)) == "1d left"


def test_one_day_overdue():
    from app.widgets.month import _due_text
    assert _due_text("2026-06-29", dt.date(2026, 6, 30)) == "1d overdue"
