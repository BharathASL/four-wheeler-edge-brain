"""SQLite-backed conversation memory for per-user chat continuity."""

from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Tuple


class ConversationMemoryStore:
    """Persist users and chat turns so context can survive process restarts."""

    def __init__(self, db_path: str = "data/conversations.sqlite"):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self._db_path))

    def _initialize(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        created_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_turns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        user_text TEXT NOT NULL,
                        assistant_text TEXT NOT NULL,
                        created_at REAL NOT NULL,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_conversation_turns_user_id_id
                    ON conversation_turns(user_id, id)
                    """
                )
                conn.commit()

    def get_or_create_user(self, name: str) -> Tuple[int, bool]:
        normalized_name = (name or "").strip()
        if not normalized_name:
            raise ValueError("User name cannot be empty")

        with self._lock:
            with self._connect() as conn:
                row = conn.execute("SELECT id FROM users WHERE name = ?", (normalized_name,)).fetchone()
                if row:
                    return int(row[0]), False

                now = time.time()
                cursor = conn.execute(
                    "INSERT INTO users(name, created_at) VALUES(?, ?)",
                    (normalized_name, now),
                )
                conn.commit()
                return int(cursor.lastrowid), True

    def append_turn(self, user_id: int, user_text: str, assistant_text: str) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO conversation_turns(user_id, user_text, assistant_text, created_at)
                    VALUES(?, ?, ?, ?)
                    """,
                    (user_id, user_text, assistant_text, time.time()),
                )
                conn.commit()

    def get_recent_turns(self, user_id: int, limit: int = 6) -> List[Dict[str, str]]:
        if limit <= 0:
            return []

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT user_text, assistant_text
                    FROM conversation_turns
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, limit),
                ).fetchall()

        rows = list(reversed(rows))
        return [
            {
                "user": str(row[0]),
                "assistant": str(row[1]),
            }
            for row in rows
        ]


__all__ = ["ConversationMemoryStore"]
