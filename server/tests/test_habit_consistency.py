"""Tests for habit consistency — weekly target hit/miss over completed weeks."""
import datetime as dt
import sqlite3

from app import store


def _fresh_db(tmp_path):
    """Create a temp DB with schema, return path."""
    db = str(tmp_path / "test.db")
    conn = sqlite3.connect(db)
    conn.executescript(store.SCHEMA)
    return db, conn


def _seed(conn, habits, logs):
    """Insert habits and logs. habits = [(name, target)], logs = [(habit_id, date_str)]."""
    for name, target in habits:
        conn.execute("INSERT INTO habit (name, target_per_week) VALUES (?, ?)", (name, target))
    for hid, date_str in logs:
        conn.execute("INSERT INTO habit_log (habit_id, date) VALUES (?, ?)", (hid, date_str))
    conn.commit()


def _patch_db(monkeypatch, db_path):
    """Point store.connect at the given db file."""
    orig_connect = store.connect

    def patched_connect():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    monkeypatch.setattr(store, "connect", patched_connect)


def test_basic_hit_and_miss(tmp_path, monkeypatch):
    """Habit with target 3/week: hit weeks where count >= 3."""
    db, conn = _fresh_db(tmp_path)
    _patch_db(monkeypatch, db)

    # Use a fixed "today" = Thursday 2026-06-25 (week 26).
    # Completed weeks to check: weeks 22, 23, 24, 25 (Mon-Sun each).
    today = dt.date(2026, 6, 25)
    monkeypatch.setattr(dt, "date", type("MockDate", (dt.date,), {"today": classmethod(lambda cls: today)}))

    # Habit "Gym" with target 3/week
    _seed(conn, [("Gym", 3)], [
        # Week 22 (May 25-31): 3 logs → HIT
        (1, "2026-05-25"), (1, "2026-05-26"), (1, "2026-05-27"),
        # Week 23 (Jun 1-7): 2 logs → MISS
        (1, "2026-06-01"), (1, "2026-06-02"),
        # Week 24 (Jun 8-14): 4 logs → HIT
        (1, "2026-06-08"), (1, "2026-06-09"), (1, "2026-06-10"), (1, "2026-06-11"),
        # Week 25 (Jun 15-21): 0 logs → MISS
        # Current week 26 (Jun 22-28): 2 logs (should be EXCLUDED)
        (1, "2026-06-22"), (1, "2026-06-23"),
    ])
    conn.close()

    result = store.get_habit_consistency(weeks=4)
    assert len(result) == 1
    r = result[0]
    assert r["name"] == "Gym"
    assert r["weeks"] == [True, False, True, False]  # weeks 22-25
    assert r["hit_rate"] == 50


def test_no_target_excluded(tmp_path, monkeypatch):
    """Habits without target_per_week are excluded."""
    db, conn = _fresh_db(tmp_path)
    _patch_db(monkeypatch, db)
    today = dt.date(2026, 6, 25)
    monkeypatch.setattr(dt, "date", type("MockDate", (dt.date,), {"today": classmethod(lambda cls: today)}))

    _seed(conn, [("NoTarget", None)], [])
    conn.close()

    result = store.get_habit_consistency(weeks=4)
    assert len(result) == 0


def test_empty_log_all_miss(tmp_path, monkeypatch):
    """Habit with target but no logs returns all-miss weeks."""
    db, conn = _fresh_db(tmp_path)
    _patch_db(monkeypatch, db)
    today = dt.date(2026, 6, 25)
    monkeypatch.setattr(dt, "date", type("MockDate", (dt.date,), {"today": classmethod(lambda cls: today)}))

    _seed(conn, [("Read", 5)], [])
    conn.close()

    result = store.get_habit_consistency(weeks=4)
    assert len(result) == 1
    assert result[0]["weeks"] == [False, False, False, False]
    assert result[0]["hit_rate"] == 0


def test_all_hit(tmp_path, monkeypatch):
    """Habit hitting target every week returns all-True + 100%."""
    db, conn = _fresh_db(tmp_path)
    _patch_db(monkeypatch, db)
    today = dt.date(2026, 6, 25)
    monkeypatch.setattr(dt, "date", type("MockDate", (dt.date,), {"today": classmethod(lambda cls: today)}))

    # target 2/week, 2 logs each week for weeks 22-25
    logs = []
    for week_start in ["2026-05-25", "2026-06-01", "2026-06-08", "2026-06-15"]:
        d = dt.date.fromisoformat(week_start)
        logs.append((1, d.isoformat()))
        logs.append((1, (d + dt.timedelta(days=1)).isoformat()))
    _seed(conn, [("Water", 2)], logs)
    conn.close()

    result = store.get_habit_consistency(weeks=4)
    assert result[0]["weeks"] == [True, True, True, True]
    assert result[0]["hit_rate"] == 100


def test_current_week_excluded(tmp_path, monkeypatch):
    """Log entries in the current week do not affect the dots."""
    db, conn = _fresh_db(tmp_path)
    _patch_db(monkeypatch, db)
    today = dt.date(2026, 6, 25)  # Thursday of week 26
    monkeypatch.setattr(dt, "date", type("MockDate", (dt.date,), {"today": classmethod(lambda cls: today)}))

    # Only log entries in current week 26 — no completed-week data.
    _seed(conn, [("Gym", 1)], [
        (1, "2026-06-22"), (1, "2026-06-23"), (1, "2026-06-24"), (1, "2026-06-25"),
    ])
    conn.close()

    result = store.get_habit_consistency(weeks=4)
    assert result[0]["weeks"] == [False, False, False, False]
    assert result[0]["hit_rate"] == 0
