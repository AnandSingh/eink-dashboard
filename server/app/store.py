"""Source of truth: SQLite for queries + a Markdown mirror for humans/git.

Every mutation bumps a monotonic `version` integer. The Pi polls that version
and only re-displays the PNG when it changes.
"""
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


# TODO: add_tasks(), mark_done(), log_habit(), add_to_review(), and the
#       Markdown mirror writer (data/tasks.md, data/habits.md).
