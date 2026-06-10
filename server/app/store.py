"""Source of truth: SQLite for queries + a Markdown mirror for humans/git.

Every mutation bumps a monotonic `version` integer. The Pi polls that version
and only re-displays the PNG when it changes.
"""
import datetime as dt
import sqlite3

from .config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'todo',     -- todo | done
    source_photo TEXT,
    confidence REAL,
    created_at TEXT NOT NULL,
    done_at TEXT
);
CREATE TABLE IF NOT EXISTS habit (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    cadence TEXT NOT NULL DEFAULT 'daily',
    target_per_week INTEGER
);
CREATE TABLE IF NOT EXISTS habit_log (
    id INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS goal (
    id INTEGER PRIMARY KEY,
    text TEXT NOT NULL,
    horizon TEXT NOT NULL DEFAULT 'month',    -- month | quarter
    progress REAL NOT NULL DEFAULT 0,
    due TEXT
);
CREATE TABLE IF NOT EXISTS photo (
    id INTEGER PRIMARY KEY,
    hash TEXT UNIQUE NOT NULL,
    type TEXT,
    status TEXT,
    processed_at TEXT
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT OR IGNORE INTO meta(key, value) VALUES ('version', '0')"
        )


def get_version() -> int:
    with connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key='version'").fetchone()
        return int(row["value"]) if row else 0


def bump_version() -> int:
    """Increment the render version and trigger a re-render.

    TODO: after bumping, call renderer.render() to refresh dashboard.png.
    """
    with connect() as conn:
        new = get_version() + 1
        conn.execute("UPDATE meta SET value=? WHERE key='version'", (str(new),))
        conn.commit()
    return new


# --- Reads (used by the renderer) ---------------------------------------


def get_tasks() -> list[dict]:
    """Today's tasks, todo first then done, in insertion order."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT text, status, confidence FROM task "
            "ORDER BY (status='done'), id"
        ).fetchall()
    return [dict(r) for r in rows]


def get_habits() -> list[dict]:
    """Habits with a 7-element week of completion (Mon..Sun).

    Each slot is True (done), False (missed, past), or None (future).
    """
    today = dt.date.today()
    monday = today - dt.timedelta(days=today.weekday())
    week_dates = [monday + dt.timedelta(days=i) for i in range(7)]

    habits = []
    with connect() as conn:
        for h in conn.execute("SELECT id, name, target_per_week FROM habit ORDER BY id"):
            logs = {
                r["date"]
                for r in conn.execute(
                    "SELECT date FROM habit_log WHERE habit_id=?", (h["id"],)
                )
            }
            week = []
            for d in week_dates:
                if d > today:
                    week.append(None)
                else:
                    week.append(d.isoformat() in logs)
            # streak: consecutive done days ending today/yesterday
            streak = 0
            cursor = today
            while cursor.isoformat() in logs:
                streak += 1
                cursor -= dt.timedelta(days=1)
            done = sum(1 for x in week if x)
            habits.append(
                {
                    "name": h["name"],
                    "week": week,
                    "done": done,
                    "target": h["target_per_week"],
                    "streak": streak,
                }
            )
    return habits


def get_goals() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT text, progress, due FROM goal ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def is_empty() -> bool:
    with connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM task").fetchone()["c"]
    return n == 0


# --- Demo seed (Phase 2: gives the renderer something to draw) -----------


def seed_demo() -> None:
    """Populate sample data so the dashboard renders something real.

    Safe to call only when the DB is empty (see api startup).
    """
    today = dt.date.today()
    with connect() as conn:
        conn.executemany(
            "INSERT INTO task(text, status, confidence, created_at) VALUES (?,?,?,?)",
            [
                ("Ship dashboard v1", "todo", 0.98, today.isoformat()),
                ("Standup notes", "done", 0.95, today.isoformat()),
                ("Call dentist", "todo", 0.71, today.isoformat()),
                ("Review PRs", "todo", 0.99, today.isoformat()),
            ],
        )
        cur = conn.cursor()
        habits = [("Gym", 5), ("Read", 5), ("Water", 7)]
        for name, target in habits:
            cur.execute(
                "INSERT INTO habit(name, cadence, target_per_week) VALUES (?, 'daily', ?)",
                (name, target),
            )
            hid = cur.lastrowid
            # log a few recent days so streaks/grids look alive
            for back in (3, 2, 1, 0):
                if name == "Water" and back == 0:
                    continue  # skip today for one habit, to show a gap
                d = today - dt.timedelta(days=back)
                cur.execute(
                    "INSERT INTO habit_log(habit_id, date, count) VALUES (?,?,1)",
                    (hid, d.isoformat()),
                )
        conn.executemany(
            "INSERT INTO goal(text, horizon, progress, due) VALUES (?,?,?,?)",
            [
                ("Q2 goal: ship side project", "quarter", 0.6, None),
                ("Trip planning", "month", 0.25, (today + dt.timedelta(days=18)).isoformat()),
            ],
        )
        conn.commit()


# TODO (later phases): add_tasks(), mark_done(), log_habit(), add_to_review(),
#       and the Markdown mirror writer (data/tasks.md, data/habits.md).
