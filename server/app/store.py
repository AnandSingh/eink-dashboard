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
CREATE TABLE IF NOT EXISTS event (
    key TEXT PRIMARY KEY,          -- synthetic: uid@occurrence_start (distinct per occurrence)
    uid TEXT,                      -- VEVENT UID (series id)
    title TEXT,
    start_utc TEXT NOT NULL,       -- ISO8601, UTC
    end_utc TEXT NOT NULL,         -- ISO8601, UTC
    all_day INTEGER NOT NULL DEFAULT 0,
    location TEXT
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.db_path)
    conn.row_factory = sqlite3.Row
    # Multiple daemon threads (glasses, calendar, weather) + the API write here.
    # Wait on locks instead of raising "database is locked"; WAL lets a reader
    # (e.g. GET /dashboard.png path) coexist with a writer.
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA journal_mode=WAL")
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
    """Increment the render version. The Pi re-downloads the PNG when it changes.

    Callers render first (or use renderer.render_if_changed, which bumps only when
    the rendered image actually differs).
    """
    with connect() as conn:
        # Single-statement increment: atomic, no lost updates under concurrency.
        conn.execute(
            "UPDATE meta SET value = CAST(value AS INTEGER) + 1 WHERE key='version'"
        )
        conn.commit()
        row = conn.execute("SELECT value FROM meta WHERE key='version'").fetchone()
        return int(row["value"])


def get_meta(key: str) -> str | None:
    with connect() as conn:
        row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None


def set_meta(key: str, value: str) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO meta(key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        conn.commit()


def replace_events(events: list[dict]) -> None:
    """Wipe + repopulate the event table (display-only; tiny; no incremental diff).

    Each event is {"key","uid","title","start_utc","end_utc","all_day","location"}.
    """
    with connect() as conn:
        conn.execute("DELETE FROM event")
        conn.executemany(
            "INSERT OR REPLACE INTO event"
            "(key, uid, title, start_utc, end_utc, all_day, location) "
            "VALUES (:key,:uid,:title,:start_utc,:end_utc,:all_day,:location)",
            events,
        )
        conn.commit()


def get_events() -> list[dict]:
    """All stored events (already windowed to ~today by the sync), earliest first."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT key, uid, title, start_utc, end_utc, all_day, location "
            "FROM event ORDER BY start_utc"
        ).fetchall()
    return [dict(r) for r in rows]


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
            "SELECT id, text, progress, due FROM goal ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


def get_habit_consistency(weeks: int = 4) -> list[dict]:
    """Per-habit weekly target hit/miss for the last N completed weeks.

    Excludes the current (incomplete) week — the 7-day grid covers it.
    Returns list of {"name": str, "weeks": [bool]*N, "hit_rate": int}.
    Habits without target_per_week are skipped.
    """
    today = dt.date.today()
    this_monday = today - dt.timedelta(days=today.weekday())
    oldest_monday = this_monday - dt.timedelta(weeks=weeks)
    # Build ordered list of Monday dates for each completed week
    mondays = [oldest_monday + dt.timedelta(weeks=i) for i in range(weeks)]

    results = []
    with connect() as conn:
        for h in conn.execute(
            "SELECT id, name, target_per_week FROM habit "
            "WHERE target_per_week IS NOT NULL ORDER BY id"
        ):
            logs = {
                r["date"]
                for r in conn.execute(
                    "SELECT date FROM habit_log WHERE habit_id=? AND date>=? AND date<?",
                    (h["id"], oldest_monday.isoformat(), this_monday.isoformat()),
                )
            }
            week_hits = []
            for mon in mondays:
                count = sum(
                    1 for d in logs
                    if mon <= dt.date.fromisoformat(d) < mon + dt.timedelta(days=7)
                )
                week_hits.append(count >= h["target_per_week"])
            hit_rate = round(sum(week_hits) / len(week_hits) * 100) if week_hits else 0
            results.append({
                "name": h["name"],
                "weeks": week_hits,
                "hit_rate": hit_rate,
            })
    return results


def get_tasks_done_this_week(monday: dt.date) -> int:
    """Count tasks completed on/after `monday` (the current ISO week's Monday).

    `done_at` is a naive-local ISO timestamp (set by mark_task_done); `date(done_at)`
    normalizes it to a date so the boundary is exact regardless of the time portion.
    Caller passes the same naive-local Monday the habit week uses.
    """
    with connect() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM task "
            "WHERE status='done' AND done_at IS NOT NULL AND date(done_at) >= ?",
            (monday.isoformat(),),
        ).fetchone()
    return int(row["c"]) if row else 0


def is_empty() -> bool:
    with connect() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM task").fetchone()["c"]
    return n == 0


# --- Writes (used by the glasses capture pipeline) -----------------------


def _norm(text: str) -> str:
    """Normalize task text for fuzzy dedup."""
    return " ".join(text.lower().split())


def photo_exists(photo_hash: str) -> bool:
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM photo WHERE hash=?", (photo_hash,)
        ).fetchone()
    return row is not None


def record_photo(photo_hash: str, photo_type: str, status: str) -> None:
    """Remember we've seen this photo (dedup) and how it was handled."""
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO photo(hash, type, status, processed_at) "
            "VALUES (?,?,?,?)",
            (photo_hash, photo_type, status, dt.datetime.now().isoformat()),
        )
        conn.commit()


def add_tasks(tasks: list[dict], source_photo: str | None = None) -> int:
    """Insert tasks, skipping fuzzy duplicates of existing ones. Returns count added.

    Each task is {"text", "status", "confidence"}.
    """
    today = dt.date.today().isoformat()
    added = 0
    with connect() as conn:
        existing = {
            _norm(r["text"])
            for r in conn.execute("SELECT text FROM task").fetchall()
        }
        for t in tasks:
            key = _norm(t["text"])
            if not key or key in existing:
                continue
            existing.add(key)
            conn.execute(
                "INSERT INTO task(text, status, source_photo, confidence, created_at) "
                "VALUES (?,?,?,?,?)",
                (t["text"], t.get("status", "todo"), source_photo,
                 t.get("confidence"), today),
            )
            added += 1
        conn.commit()
    return added


def _fuzzy_pick(rows, field: str, target: str):
    """Pick the row whose `field` best matches target: exact-normalized, then substring."""
    norm_target = _norm(target)
    for r in rows:
        if _norm(r[field]) == norm_target:
            return r
    for r in rows:
        nf = _norm(r[field])
        if norm_target in nf or nf in norm_target:
            return r
    return None


def mark_task_done(text: str) -> str | None:
    """Mark the best-matching open task done. Returns its text, or None if no match."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, text FROM task WHERE status!='done'"
        ).fetchall()
        match = _fuzzy_pick(rows, "text", text)
        if match is None:
            return None
        conn.execute(
            "UPDATE task SET status='done', done_at=? WHERE id=?",
            (dt.datetime.now().isoformat(), match["id"]),
        )
        conn.commit()
        return match["text"]


def log_habit(name: str) -> str | None:
    """Log today's completion for the best-matching habit. Returns its name, or None."""
    today = dt.date.today().isoformat()
    with connect() as conn:
        rows = conn.execute("SELECT id, name FROM habit").fetchall()
        match = _fuzzy_pick(rows, "name", name)
        if match is None:
            return None
        already = conn.execute(
            "SELECT 1 FROM habit_log WHERE habit_id=? AND date=?",
            (match["id"], today),
        ).fetchone()
        if not already:
            conn.execute(
                "INSERT INTO habit_log(habit_id, date, count) VALUES (?,?,1)",
                (match["id"], today),
            )
            conn.commit()
        return match["name"]


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
