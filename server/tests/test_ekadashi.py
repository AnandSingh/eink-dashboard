"""Tests for the Ekadashi helper — observer-free, multi-sample tithi detection."""
import datetime as dt

from app import ekadashi


def test_known_shukla_ekadashi_2026():
    """2026-01-28 is Shukla Ekadashi (Pausha). next_ekadashi from Jan 26 → 2 days."""
    result = ekadashi.next_ekadashi(dt.datetime(2026, 1, 26))
    assert result is not None
    assert result["date"] == dt.date(2026, 1, 28)
    assert result["days"] == 2


def test_ekadashi_today_returns_zero_days():
    """When called on an Ekadashi day itself, days == 0."""
    result = ekadashi.next_ekadashi(dt.datetime(2026, 1, 28))
    assert result is not None
    assert result["days"] == 0


def test_known_krishna_ekadashi_2026():
    """2026-01-13 is Krishna Ekadashi (Pausha). next_ekadashi from Jan 11 → 2 days."""
    result = ekadashi.next_ekadashi(dt.datetime(2026, 1, 11))
    assert result is not None
    assert result["date"] == dt.date(2026, 1, 13)
    assert result["days"] == 2


def test_full_year_finds_all_24():
    """Scan every day of 2026, collect unique Ekadashi dates — expect 24."""
    seen = set()
    for ordinal in range(365):
        day = dt.date(2026, 1, 1) + dt.timedelta(days=ordinal)
        result = ekadashi.next_ekadashi(dt.datetime(day.year, day.month, day.day))
        if result and result["days"] == 0:
            seen.add(result["date"])
    assert len(seen) == 24, f"Expected 24, got {len(seen)}: {sorted(seen)}"


def test_max_gap_is_reasonable():
    """No gap between consecutive Ekadashis should exceed 16 days."""
    dates = []
    for ordinal in range(365):
        day = dt.date(2026, 1, 1) + dt.timedelta(days=ordinal)
        result = ekadashi.next_ekadashi(dt.datetime(day.year, day.month, day.day))
        if result and result["days"] == 0:
            dates.append(result["date"])
    dates = sorted(set(dates))
    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i - 1]).days
        assert gap <= 16, f"Gap {gap}d between {dates[i-1]} and {dates[i]}"


def test_consecutive_day_suppression():
    """If today is the second of two consecutive Ekadashi days, skip to next."""
    # Find a known Ekadashi and check if the next day also qualifies.
    ek = ekadashi.next_ekadashi(dt.datetime(2026, 5, 1))
    assert ek is not None
    first_date = ek["date"]
    next_day = first_date + dt.timedelta(days=1)
    if ekadashi._day_is_ekadashi(next_day):
        # The next day is in range — next_ekadashi from that day should skip it.
        result = ekadashi.next_ekadashi(
            dt.datetime(next_day.year, next_day.month, next_day.day))
        assert result is not None
        assert result["date"] > next_day, (
            f"Should skip {next_day} (second of consecutive run)")
    else:
        # No consecutive pair from this starting point — test with a broader scan.
        for ordinal in range(365):
            day = dt.date(2026, 1, 1) + dt.timedelta(days=ordinal)
            if ekadashi._day_is_ekadashi(day) and ekadashi._day_is_ekadashi(
                    day + dt.timedelta(days=1)):
                second = day + dt.timedelta(days=1)
                result = ekadashi.next_ekadashi(
                    dt.datetime(second.year, second.month, second.day))
                assert result is not None
                assert result["date"] > second
                return
        # If no consecutive pair exists at all, the test is N/A — pass.


def test_never_returns_none_in_practice():
    """Max Ekadashi gap is ~15d; scanning 33 days should always find one."""
    for ordinal in range(0, 365, 7):  # sample weekly
        day = dt.date(2026, 1, 1) + dt.timedelta(days=ordinal)
        result = ekadashi.next_ekadashi(dt.datetime(day.year, day.month, day.day))
        assert result is not None, f"None returned for {day}"


def test_accepts_aware_datetime():
    """Should handle timezone-aware input like moon.phase() does."""
    result = ekadashi.next_ekadashi(
        dt.datetime(2026, 1, 26, tzinfo=dt.timezone.utc))
    assert result is not None
    assert result["date"] == dt.date(2026, 1, 28)
