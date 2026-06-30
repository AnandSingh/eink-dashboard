"""Tests for quarter progress + month weekday helpers — pure date arithmetic."""
import datetime as dt

from app import quarter


# --- quarter_info ---

def test_q1_start():
    info = quarter.quarter_info(dt.date(2026, 1, 1))
    assert info["quarter"] == 1
    assert info["fraction"] == 0.0
    assert info["days_left"] == 90  # Jan 1 – Mar 31 = 90 days in 2026


def test_q1_end():
    info = quarter.quarter_info(dt.date(2026, 3, 31))
    assert info["quarter"] == 1
    assert info["days_left"] == 1  # last day of quarter, 1 day left (today)


def test_q2_start():
    info = quarter.quarter_info(dt.date(2026, 4, 1))
    assert info["quarter"] == 2
    assert info["fraction"] == 0.0


def test_q4_mid():
    info = quarter.quarter_info(dt.date(2026, 11, 15))
    assert info["quarter"] == 4


def test_leap_year_q1():
    info = quarter.quarter_info(dt.date(2028, 2, 15))
    assert info["quarter"] == 1
    # Q1 2028 = 91 days (Jan 31 + Feb 29 + Mar 31), Feb 15 = day 45
    assert info["days_left"] == 91 - 45


# --- month_weekdays ---

def test_june_2026_weekdays():
    info = quarter.month_weekdays(dt.date(2026, 6, 1))
    assert info["month"] == "June"
    assert info["weekdays_total"] == 22  # June 2026: 22 weekdays


def test_february_2028_leap_year():
    info = quarter.month_weekdays(dt.date(2028, 2, 1))
    assert info["month"] == "February"
    assert info["weekdays_total"] == 21  # Feb 2028 leap: 21 weekdays


def test_weekdays_left_includes_today_if_weekday():
    # June 1, 2026 is a Monday — 22 weekdays left (all of them, including today).
    info = quarter.month_weekdays(dt.date(2026, 6, 1))
    assert info["weekdays_left"] == 22


def test_weekdays_left_on_last_day():
    # June 30, 2026 is a Tuesday — 1 weekday left (today).
    info = quarter.month_weekdays(dt.date(2026, 6, 30))
    assert info["weekdays_left"] == 1


def test_weekdays_left_on_weekend():
    # June 27, 2026 is a Saturday — weekdays left = Mon 29 + Tue 30 = 2.
    info = quarter.month_weekdays(dt.date(2026, 6, 27))
    assert info["weekdays_left"] == 2


def test_weekdays_left_on_sunday():
    # June 28, 2026 is a Sunday — weekdays left = Mon 29 + Tue 30 = 2.
    info = quarter.month_weekdays(dt.date(2026, 6, 28))
    assert info["weekdays_left"] == 2
