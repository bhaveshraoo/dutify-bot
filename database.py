"""
Database module for DutyBot using SQLite
"""

import sqlite3
import os
from datetime import datetime, date
from typing import Optional


DB_PATH = os.path.join(os.path.dirname(__file__), "dutybot.db")


class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_db(self):
        """Create all tables"""
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    name        TEXT NOT NULL,
                    created_at  TEXT DEFAULT (datetime('now')),
                    timezone    TEXT DEFAULT 'Asia/Kolkata'
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id                INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id           INTEGER NOT NULL REFERENCES users(user_id),
                    title             TEXT NOT NULL,
                    task_date         TEXT NOT NULL,   -- YYYY-MM-DD
                    task_time         TEXT NOT NULL,   -- HH:MM
                    tag               TEXT,
                    reminder_minutes  INTEGER,
                    notes             TEXT,
                    completed         INTEGER DEFAULT 0,
                    created_at        TEXT DEFAULT (datetime('now')),
                    updated_at        TEXT DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_tasks_user_date
                    ON tasks(user_id, task_date);

                CREATE INDEX IF NOT EXISTS idx_tasks_tag
                    ON tasks(user_id, tag);

                CREATE TABLE IF NOT EXISTS reminder_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id     INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    sent_at     TEXT DEFAULT (datetime('now')),
                    status      TEXT DEFAULT 'sent'
                );
            """)

    # ─── USER ───────────────────────────────────────────────

    def ensure_user(self, user_id: int, name: str):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users(user_id, name) VALUES (?, ?)",
                (user_id, name)
            )

    # ─── TASKS ──────────────────────────────────────────────

    def add_task(
        self,
        user_id: int,
        title: str,
        task_date: str,
        task_time: str,
        tag: Optional[str] = None,
        reminder_minutes: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> int:
        with self.get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO tasks
                   (user_id, title, task_date, task_time, tag, reminder_minutes, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (user_id, title, task_date, task_time, tag, reminder_minutes, notes)
            )
            return cur.lastrowid

    def get_tasks_by_date(self, user_id: int, task_date: str) -> list[dict]:
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE user_id = ? AND task_date = ?
                   ORDER BY task_time ASC""",
                (user_id, task_date)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_tasks_by_tag(self, user_id: int, tag: str) -> list[dict]:
        with self.get_conn() as conn:
            today = date.today().strftime("%Y-%m-%d")
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE user_id = ? AND LOWER(tag) = LOWER(?)
                   AND task_date >= ?
                   ORDER BY task_date ASC, task_time ASC""",
                (user_id, tag, today)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_all_tasks_by_tag(self, user_id: int, tag: str) -> list[dict]:
        """Including past tasks"""
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE user_id = ? AND LOWER(tag) = LOWER(?)
                   ORDER BY task_date ASC, task_time ASC""",
                (user_id, tag)
            ).fetchall()
            return [dict(r) for r in rows]

    def toggle_task(self, task_id: int, user_id: int) -> bool:
        with self.get_conn() as conn:
            conn.execute(
                """UPDATE tasks
                   SET completed = 1 - completed,
                       updated_at = datetime('now')
                   WHERE id = ? AND user_id = ?""",
                (task_id, user_id)
            )
            row = conn.execute(
                "SELECT completed FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return bool(row["completed"]) if row else False

    def delete_task(self, task_id: int, user_id: int):
        with self.get_conn() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id)
            )

    def clear_completed_tasks(self, user_id: int, task_date: str):
        with self.get_conn() as conn:
            conn.execute(
                "DELETE FROM tasks WHERE user_id = ? AND task_date = ? AND completed = 1",
                (user_id, task_date)
            )

    def get_upcoming_tasks_with_reminders(self, user_id: int) -> list[dict]:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM tasks
                   WHERE user_id = ? AND reminder_minutes IS NOT NULL
                   AND completed = 0 AND task_date >= ?
                   ORDER BY task_date ASC, task_time ASC
                   LIMIT 20""",
                (user_id, today)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_tasks_due_for_reminder(self, minutes_ahead: int = 1) -> list[dict]:
        """Get tasks whose reminder time is within the next minute"""
        now = datetime.now()
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT t.*, u.user_id FROM tasks t
                   JOIN users u ON t.user_id = u.user_id
                   WHERE t.completed = 0
                   AND t.reminder_minutes IS NOT NULL
                   AND datetime(t.task_date || ' ' || t.task_time, '-' || t.reminder_minutes || ' minutes')
                       BETWEEN datetime('now', 'localtime', '-1 minute')
                       AND datetime('now', 'localtime', '+1 minute')
                   AND t.id NOT IN (
                       SELECT task_id FROM reminder_log WHERE status = 'sent'
                   )"""
            ).fetchall()
            return [dict(r) for r in rows]

    def log_reminder_sent(self, task_id: int):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO reminder_log(task_id) VALUES (?)",
                (task_id,)
            )

    # ─── STATS & META ────────────────────────────────────────

    def get_stats(self, user_id: int) -> dict:
        with self.get_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND completed = 1", (user_id,)
            ).fetchone()[0]
            with_reminders = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND reminder_minutes IS NOT NULL", (user_id,)
            ).fetchone()[0]
            tags = conn.execute(
                """SELECT tag, COUNT(*) as cnt FROM tasks
                   WHERE user_id = ? AND tag IS NOT NULL
                   GROUP BY tag ORDER BY cnt DESC""",
                (user_id,)
            ).fetchall()
            return {
                "total": total,
                "completed": completed,
                "pending": total - completed,
                "with_reminders": with_reminders,
                "by_tag": {r["tag"]: r["cnt"] for r in tags},
            }

    def get_user_tags(self, user_id: int) -> list[str]:
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT DISTINCT tag FROM tasks
                   WHERE user_id = ? AND tag IS NOT NULL
                   ORDER BY tag""",
                (user_id,)
            ).fetchall()
            return [r["tag"] for r in rows]

    def count_tag(self, user_id: int, tag: str) -> int:
        with self.get_conn() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND LOWER(tag) = LOWER(?)",
                (user_id, tag)
            ).fetchone()[0]

    def get_task_by_id(self, task_id: int, user_id: int) -> Optional[dict]:
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ? AND user_id = ?",
                (task_id, user_id)
            ).fetchone()
            return dict(row) if row else None
