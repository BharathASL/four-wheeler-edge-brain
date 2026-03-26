"""Semantic memory scaffolding for hybrid SQLite + vector retrieval.

This module provides a low-risk semantic retrieval abstraction that can use a
FAISS backend when available and falls back to an in-memory vector index when
FAISS is unavailable. The first implementation slice keeps the current lexical
SQLite/FTS path intact and makes semantic retrieval opt-in.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Protocol, Sequence, Tuple


@dataclass(frozen=True)
class SemanticMatch:
    turn_id: int
    user_id: int
    score: float
    user_text: str
    assistant_text: str


class SemanticEncoder(Protocol):
    dimensions: int

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        ...


def _tokenize(text: str) -> List[str]:
    cleaned = []
    for ch in (text or "").lower():
        cleaned.append(ch if ch.isalnum() or ch.isspace() else " ")
    return [token for token in "".join(cleaned).split() if len(token) >= 2]


def _normalize_vector(vector: Sequence[float]) -> List[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return [0.0 for _ in vector]
    return [value / norm for value in vector]


class HashingSemanticEncoder:
    """Deterministic hashing encoder used as a lightweight semantic scaffold."""

    def __init__(self, dimensions: int = 128):
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    def encode(self, texts: Sequence[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in _tokenize(text):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                bucket = int.from_bytes(digest[:4], "big") % self.dimensions
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[bucket] += sign
            vectors.append(_normalize_vector(vector))
        return vectors


class InMemorySemanticBackend:
    name = "in-memory"

    def __init__(self, dimensions: int):
        self.dimensions = dimensions
        self._entries: List[Tuple[List[float], SemanticMatch]] = []

    def add(self, items: Iterable[Tuple[Sequence[float], SemanticMatch]]) -> None:
        for vector, metadata in items:
            self._entries.append((list(vector), metadata))

    def search(self, query_vector: Sequence[float], user_id: int, limit: int) -> List[SemanticMatch]:
        scored: List[SemanticMatch] = []
        query = list(query_vector)
        for vector, metadata in self._entries:
            if metadata.user_id != user_id:
                continue
            score = sum(left * right for left, right in zip(query, vector))
            scored.append(
                SemanticMatch(
                    turn_id=metadata.turn_id,
                    user_id=metadata.user_id,
                    score=score,
                    user_text=metadata.user_text,
                    assistant_text=metadata.assistant_text,
                )
            )
        scored.sort(key=lambda item: (item.score, item.turn_id), reverse=True)
        return scored[:limit]


class FaissSemanticBackend:
    name = "faiss"

    def __init__(self, dimensions: int):
        try:
            import faiss  # type: ignore
            import numpy as np  # type: ignore
        except Exception as exc:  # pragma: no cover - environment-dependent
            raise RuntimeError("faiss backend unavailable") from exc

        self.dimensions = dimensions
        self._faiss = faiss
        self._np = np
        self._index = faiss.IndexFlatIP(dimensions)
        self._metadata: List[SemanticMatch] = []

    def add(self, items: Iterable[Tuple[Sequence[float], SemanticMatch]]) -> None:
        vectors: List[List[float]] = []
        new_metadata: List[SemanticMatch] = []
        for vector, metadata in items:
            vectors.append(list(vector))
            new_metadata.append(metadata)
        if not vectors:
            return
        array = self._np.array(vectors, dtype="float32")
        self._index.add(array)
        self._metadata.extend(new_metadata)

    def search(self, query_vector: Sequence[float], user_id: int, limit: int) -> List[SemanticMatch]:
        if limit <= 0 or not self._metadata:
            return []
        overfetch = max(limit * 4, limit)
        query = self._np.array([list(query_vector)], dtype="float32")
        scores, indices = self._index.search(query, overfetch)
        matches: List[SemanticMatch] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._metadata):
                continue
            metadata = self._metadata[idx]
            if metadata.user_id != user_id:
                continue
            matches.append(
                SemanticMatch(
                    turn_id=metadata.turn_id,
                    user_id=metadata.user_id,
                    score=float(score),
                    user_text=metadata.user_text,
                    assistant_text=metadata.assistant_text,
                )
            )
            if len(matches) >= limit:
                break
        return matches


def create_semantic_backend(dimensions: int, prefer_faiss: bool = True):
    if prefer_faiss:
        try:
            return FaissSemanticBackend(dimensions)
        except RuntimeError:
            pass
    return InMemorySemanticBackend(dimensions)


class SemanticMemoryIndex:
    """Optional semantic index that can be attached to the conversation store."""

    def __init__(
        self,
        encoder: Optional[SemanticEncoder] = None,
        backend=None,
        prefer_faiss: bool = True,
    ):
        self.encoder = encoder or HashingSemanticEncoder()
        self.backend = backend or create_semantic_backend(self.encoder.dimensions, prefer_faiss=prefer_faiss)

    @property
    def backend_name(self) -> str:
        return str(getattr(self.backend, "name", "unknown"))

    def add_turn(self, turn_id: int, user_id: int, user_text: str, assistant_text: str) -> bool:
        payload = f"{user_text}\n{assistant_text}".strip()
        vector = self.encoder.encode([payload])[0]
        if not any(vector):
            return False
        self.backend.add(
            [
                (
                    vector,
                    SemanticMatch(
                        turn_id=turn_id,
                        user_id=user_id,
                        score=1.0,
                        user_text=user_text,
                        assistant_text=assistant_text,
                    ),
                )
            ]
        )
        return True

    def search(self, query: str, user_id: int, limit: int = 4) -> List[SemanticMatch]:
        normalized_query = (query or "").strip()
        if limit <= 0 or not normalized_query:
            return []
        query_vector = self.encoder.encode([normalized_query])[0]
        if not any(query_vector):
            return []
        return self.backend.search(query_vector, user_id=user_id, limit=limit)


__all__ = [
    "HashingSemanticEncoder",
    "InMemorySemanticBackend",
    "SemanticMatch",
    "SemanticMemoryIndex",
    "create_semantic_backend",
]