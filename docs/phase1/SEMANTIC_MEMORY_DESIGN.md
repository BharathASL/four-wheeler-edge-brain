# Semantic Memory Design

This document describes the first implementation slice for moving the chat-memory system toward a hybrid SQLite + FAISS design.

## Goals

- Keep SQLite as the source of truth for conversation storage.
- Add a semantic retrieval seam without breaking the current lexical runtime path.
- Make FAISS optional in the first slice so development and tests do not depend on new native vector packages.
- Gate any switch to hybrid or semantic-first runtime behavior on objective recall and latency measurements.

## First Slice

The first semantic-memory branch introduces three pieces:

1. A `SemanticMemoryIndex` abstraction in `src/semantic_memory.py`.
2. Optional semantic and hybrid retrieval modes in `ConversationMemoryStore`.
3. Migration-gate evaluator modes that can compare `fts`, `semantic`, and `hybrid` retrieval.

The branch does not change the default runtime retrieval path. Current chat behavior remains lexical unless a caller opts into semantic or hybrid retrieval explicitly.

## Architecture

### Source of truth

- SQLite stores all turns and metadata.
- FTS remains the lexical retrieval baseline and safe fallback.

### Semantic layer

- `SemanticMemoryIndex` owns vector indexing and semantic search.
- The first slice prefers a FAISS backend when available.
- If FAISS is unavailable, the code falls back to an in-memory vector backend so tests and development can continue.

### Encoder strategy

- The initial branch uses a deterministic hashing encoder as a lightweight scaffold.
- This encoder is not the intended final semantic model.
- A follow-on branch can replace the hashing encoder with a higher-quality embedding model while preserving the same retrieval abstraction.

## Retrieval Modes

- `fts`: current lexical retrieval only.
- `semantic`: semantic retrieval only when a semantic index is attached.
- `hybrid`: semantic results first, then lexical fallback rows are merged and deduplicated.

## Open Decisions

- Final embedding model selection for Pi-compatible development.
- Whether FAISS should maintain one shared index with user filtering or separate per-user indexes.
- Index persistence format and rebuild strategy for semantic indexes.
- When hybrid retrieval should become the default runtime behavior.

## Enablement Gate

Semantic retrieval should only become the default runtime path after the evaluator shows:

- recall at or above the existing migration threshold,
- acceptable p95 and p99 latency,
- no regression in direct queries,
- measurable gains on paraphrased queries.

Until then, the semantic path remains opt-in and SQLite/FTS remains the stable default.