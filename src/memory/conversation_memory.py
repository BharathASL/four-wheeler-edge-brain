"""SQLite-backed conversation memory for per-user chat continuity."""

from __future__ import annotations

import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from src.memory.memory_slots import MemorySlot, extract_slots_from_input
from src.memory.semantic_memory import SemanticMemoryIndex


def _query_tokens(query: str) -> List[str]:
    cleaned = []
    for ch in (query or "").lower():
        cleaned.append(ch if ch.isalnum() or ch.isspace() else " ")

    words = [w for w in "".join(cleaned).split() if len(w) >= 3]
    stop = {
        "what",
        "when",
        "where",
        "which",
        "this",
        "that",
        "have",
        "with",
        "from",
        "your",
        "about",
        "remember",
        "remeber",
        "know",
        "please",
        "could",
        "would",
        "should",
        "there",
        "their",
        "them",
        "they",
        "were",
        "been",
        "being",
        "into",
        "just",
    }
    prioritized = [w for w in words if w not in stop]
    if prioritized:
        return prioritized
    return words


@dataclass
class RetrievalMetrics:
    query: str
    latency_ms: float
    returned_count: int
    used_fts: bool


class RetrievalBenchmarkRecorder:
    """In-memory metrics sink used to benchmark retrieval quality and latency."""

    def __init__(self):
        self._records: List[RetrievalMetrics] = []

    def record(self, metrics: RetrievalMetrics) -> None:
        self._records.append(metrics)

    def summary(self) -> Dict[str, float]:
        if not self._records:
            return {
                "queries": 0,
                "avg_latency_ms": 0.0,
                "max_latency_ms": 0.0,
                "avg_returned_count": 0.0,
                "fts_usage_ratio": 0.0,
            }

        count = len(self._records)
        total_latency = sum(r.latency_ms for r in self._records)
        total_returned = sum(r.returned_count for r in self._records)
        fts_used = sum(1 for r in self._records if r.used_fts)
        return {
            "queries": float(count),
            "avg_latency_ms": total_latency / count,
            "max_latency_ms": max(r.latency_ms for r in self._records),
            "avg_returned_count": total_returned / count,
            "fts_usage_ratio": fts_used / count,
        }


class ConversationMemoryStore:
    """Persist users and chat turns so context can survive process restarts."""

    def __init__(
        self,
        db_path: str = "data/conversations.sqlite",
        semantic_index: Optional[SemanticMemoryIndex] = None,
        default_retrieval_mode: str = "fts",
    ):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._semantic_lock = threading.Lock()
        self._fts_enabled = False
        self._semantic_index = semantic_index
        self._default_retrieval_mode = self._normalize_retrieval_mode(default_retrieval_mode)
        self._initialize()
        self._backfill_semantic_index()

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
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS slots (
                        user_id INTEGER NOT NULL,
                        slot_name TEXT NOT NULL,
                        value TEXT NOT NULL,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY(user_id, slot_name),
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_slots_user_id_updated_at
                    ON slots(user_id, updated_at DESC)
                    """
                )

                # Use FTS5 when available for scalable long-history recall.
                try:
                    conn.execute(
                        """
                        CREATE VIRTUAL TABLE IF NOT EXISTS conversation_turns_fts
                        USING fts5(
                            user_id UNINDEXED,
                            turn_id UNINDEXED,
                            user_text,
                            assistant_text
                        )
                        """
                    )
                    self._fts_enabled = True

                    # Backfill FTS table from existing rows if needed.
                    existing = conn.execute("SELECT COUNT(*) FROM conversation_turns_fts").fetchone()
                    existing_count = int(existing[0]) if existing else 0
                    if existing_count == 0:
                        conn.execute(
                            """
                            INSERT INTO conversation_turns_fts(user_id, turn_id, user_text, assistant_text)
                            SELECT user_id, id, user_text, assistant_text
                            FROM conversation_turns
                            """
                        )
                except sqlite3.OperationalError:
                    # Some SQLite builds may not include FTS5.
                    self._fts_enabled = False

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
        turn_id = -1
        with self._lock:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO conversation_turns(user_id, user_text, assistant_text, created_at)
                    VALUES(?, ?, ?, ?)
                    """,
                    (user_id, user_text, assistant_text, time.time()),
                )
                turn_id = int(cursor.lastrowid)
                if self._fts_enabled:
                    conn.execute(
                        """
                        INSERT INTO conversation_turns_fts(user_id, turn_id, user_text, assistant_text)
                        VALUES(?, ?, ?, ?)
                        """,
                        (user_id, turn_id, user_text, assistant_text),
                    )
                conn.commit()

        existing_slots = self._get_slot_records(user_id)
        extracted_slots = extract_slots_from_input(user_text, existing_slots=existing_slots)
        if extracted_slots:
            self.store_slots(user_id, extracted_slots)

        if self._semantic_index is not None:
            with self._semantic_lock:
                self._semantic_index.add_turn(
                    turn_id=turn_id,
                    user_id=user_id,
                    user_text=user_text,
                    assistant_text=assistant_text,
                )

    def store_slots(self, user_id: int, slots: List[MemorySlot]) -> None:
        if not slots:
            return

        with self._lock:
            with self._connect() as conn:
                for slot in slots:
                    conn.execute(
                        """
                        INSERT INTO slots(user_id, slot_name, value, updated_at)
                        VALUES(?, ?, ?, ?)
                        ON CONFLICT(user_id, slot_name) DO UPDATE SET
                            value = excluded.value,
                            updated_at = excluded.updated_at
                        """,
                        (user_id, slot.name, slot.value, float(slot.updated_at or time.time())),
                    )
                conn.commit()

    def get_slot(self, user_id: int, slot_name: str) -> Optional[str]:
        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT value
                    FROM slots
                    WHERE user_id = ? AND slot_name = ?
                    """,
                    (user_id, slot_name),
                ).fetchone()
        if row is None:
            return None
        return str(row[0])

    def get_all_slots(self, user_id: int) -> Dict[str, str]:
        records = self._get_slot_records(user_id)
        return {slot_name: slot.value for slot_name, slot in records.items()}

    def _get_slot_records(self, user_id: int) -> Dict[str, MemorySlot]:
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT slot_name, value, updated_at
                    FROM slots
                    WHERE user_id = ?
                    ORDER BY updated_at DESC, slot_name ASC
                    """,
                    (user_id,),
                ).fetchall()
        return {
            str(row[0]): MemorySlot(name=str(row[0]), value=str(row[1]), updated_at=float(row[2]))
            for row in rows
        }

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

    def search_relevant_turns(
        self,
        user_id: int,
        query: str,
        limit: int = 4,
        metrics_hook: Optional[Callable[[RetrievalMetrics], None]] = None,
        retrieval_mode: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        if limit <= 0:
            return []

        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        start = time.perf_counter()
        mode = self._normalize_retrieval_mode(retrieval_mode or self._default_retrieval_mode)
        if mode == "semantic":
            rows = self._search_relevant_turns_semantic(user_id=user_id, query=normalized_query, limit=limit)
            used_fts = False
        elif mode == "hybrid":
            rows, used_fts = self._search_relevant_turns_hybrid(
                user_id=user_id,
                query=normalized_query,
                limit=limit,
            )
        elif self._fts_enabled:
            rows = self._search_relevant_turns_fts(user_id=user_id, query=normalized_query, limit=limit)
            used_fts = True
        else:
            rows = self._search_relevant_turns_like(user_id=user_id, query=normalized_query, limit=limit)
            used_fts = False

        latency_ms = (time.perf_counter() - start) * 1000.0
        if metrics_hook is not None:
            metrics_hook(
                RetrievalMetrics(
                    query=normalized_query,
                    latency_ms=latency_ms,
                    returned_count=len(rows),
                    used_fts=used_fts,
                )
            )

        return rows

    def _normalize_retrieval_mode(self, retrieval_mode: Optional[str]) -> str:
        mode = (retrieval_mode or "fts").strip().lower()
        if mode in {"fts", "semantic", "hybrid"}:
            return mode
        return "fts"

    def _backfill_semantic_index(self) -> None:
        if self._semantic_index is None:
            return

        with self._semantic_lock:
            min_id = self._semantic_index.max_indexed_turn_id + 1

        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, user_id, user_text, assistant_text
                    FROM conversation_turns
                    WHERE id >= ?
                    ORDER BY id ASC
                    """,
                    (min_id,),
                ).fetchall()

        if not rows:
            return

        turns = [
            (int(row[0]), int(row[1]), str(row[2]), str(row[3]))
            for row in rows
        ]
        with self._semantic_lock:
            self._semantic_index.add_turns_batch(turns)

    def _search_relevant_turns_semantic(self, user_id: int, query: str, limit: int) -> List[Dict[str, str]]:
        if self._semantic_index is None:
            return []

        with self._semantic_lock:
            matches = self._semantic_index.search(query=query, user_id=user_id, limit=limit)
        return [
            {"user": match.user_text, "assistant": match.assistant_text}
            for match in matches
        ]

    def _search_relevant_turns_hybrid(self, user_id: int, query: str, limit: int) -> Tuple[List[Dict[str, str]], bool]:
        """Hybrid retrieval: use semantic search as the primary signal, and backfill with
        FTS/LIKE results to reach `limit` rows when semantic returns a partial set.
        The returned boolean indicates whether an FTS/LIKE lookup was used.
        """
        # First, run semantic search.
        semantic_rows = self._search_relevant_turns_semantic(
            user_id=user_id,
            query=query,
            limit=limit,
        )

        # Build a deduplicated semantic-first result set.
        seen: set[Tuple[Optional[str], Optional[str]]] = set()
        merged: List[Dict[str, str]] = []

        for row in semantic_rows:
            key = (row.get("user"), row.get("assistant"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)

        # If semantic rows already satisfy the limit after dedupe, stop here.
        if len(merged) >= limit:
            return merged[:limit], False

        # Backfill using FTS or LIKE. We overfetch up to `limit` because fallback
        # rows may overlap semantic rows and be removed by dedupe.
        if self._fts_enabled:
            fallback_rows = self._search_relevant_turns_fts(
                user_id=user_id,
                query=query,
                limit=limit,
            )
        else:
            fallback_rows = self._search_relevant_turns_like(
                user_id=user_id,
                query=query,
                limit=limit,
            )

        for row in fallback_rows:
            key = (row.get("user"), row.get("assistant"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
            if len(merged) >= limit:
                break

        used_fts = True
        return merged, used_fts

    def _search_relevant_turns_fts(self, user_id: int, query: str, limit: int) -> List[Dict[str, str]]:
        tokens = _query_tokens(query)
        if not tokens:
            return []

        # Quote terms for stable matching and avoid overly broad stop-word matches.
        fts_query = " OR ".join(f'"{tok}"' for tok in tokens)
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT user_text, assistant_text
                    FROM conversation_turns_fts
                    WHERE user_id = ?
                      AND conversation_turns_fts MATCH ?
                    ORDER BY bm25(conversation_turns_fts), turn_id DESC
                    LIMIT ?
                    """,
                    (user_id, fts_query, limit),
                ).fetchall()

        return [{"user": str(row[0]), "assistant": str(row[1])} for row in rows]

    def _search_relevant_turns_like(self, user_id: int, query: str, limit: int) -> List[Dict[str, str]]:
        pattern = f"%{query}%"
        with self._lock:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT user_text, assistant_text
                    FROM conversation_turns
                    WHERE user_id = ?
                      AND (user_text LIKE ? OR assistant_text LIKE ?)
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (user_id, pattern, pattern, limit),
                ).fetchall()

        return [{"user": str(row[0]), "assistant": str(row[1])} for row in rows]


__all__ = ["ConversationMemoryStore", "RetrievalBenchmarkRecorder", "RetrievalMetrics"]
