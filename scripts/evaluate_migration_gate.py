#!/usr/bin/env python3
"""Evaluate memory retrieval quality/latency for FAISS migration decisions.

This script seeds a fixed query set into SQLite conversation memory, runs
retrieval at k, and prints recall@k + latency percentiles with pass/fail
thresholds for objective migration gating.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.conversation_memory import ConversationMemoryStore, RetrievalMetrics


def _percentile(values: List[float], percentile: float) -> float:
    if not values:
        return 0.0
    if percentile <= 0:
        return min(values)
    if percentile >= 100:
        return max(values)

    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * (percentile / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = rank - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _load_query_set(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    turns = payload.get("turns") or []
    queries = payload.get("queries") or []
    if not turns or not queries:
        raise ValueError("query set must include non-empty 'turns' and 'queries'")
    return payload


def _contains_any_expected(rows: List[Dict[str, str]], expected_tokens: List[str]) -> bool:
    blob = "\n".join(f"{row['user']}\n{row['assistant']}" for row in rows).lower()
    for token in expected_tokens:
        if token.lower() in blob:
            return True
    return False


def run_evaluation(args: argparse.Namespace) -> Dict[str, Any]:
    query_set = _load_query_set(args.query_set)
    db_path = Path(args.db_path)
    if db_path.exists():
        db_path.unlink()
    store = ConversationMemoryStore(db_path=args.db_path)

    speaker_name = query_set.get("speaker_name", "migration-gate-eval-user")
    user_id, _ = store.get_or_create_user(speaker_name)

    for turn in query_set["turns"]:
        store.append_turn(user_id, str(turn["user"]), str(turn["assistant"]))

    metrics: List[RetrievalMetrics] = []
    hits = 0
    results = []

    for q in query_set["queries"]:
        query = str(q["query"])
        expected_tokens = [str(t) for t in q.get("expect_any", [])]
        rows = store.search_relevant_turns(
            user_id=user_id,
            query=query,
            limit=args.k,
            metrics_hook=metrics.append,
        )
        matched = _contains_any_expected(rows, expected_tokens)
        hits += 1 if matched else 0
        results.append(
            {
                "query": query,
                "expected": expected_tokens,
                "matched": matched,
                "returned_count": len(rows),
            }
        )

    total = len(query_set["queries"])
    recall_at_k = (hits / total) if total else 0.0
    latencies = [m.latency_ms for m in metrics]
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    fts_ratio = (sum(1 for m in metrics if m.used_fts) / len(metrics)) if metrics else 0.0

    threshold_pass = (
        recall_at_k >= args.min_recall_at_k
        and p95 <= args.max_p95_ms
        and p99 <= args.max_p99_ms
    )

    report = {
        "dataset": args.query_set,
        "db_path": args.db_path,
        "k": args.k,
        "thresholds": {
            "min_recall_at_k": args.min_recall_at_k,
            "max_p95_ms": args.max_p95_ms,
            "max_p99_ms": args.max_p99_ms,
        },
        "metrics": {
            "query_count": total,
            "recall_at_k": recall_at_k,
            "latency_ms_p50": p50,
            "latency_ms_p95": p95,
            "latency_ms_p99": p99,
            "fts_usage_ratio": fts_ratio,
        },
        "decision": {
            "pass": threshold_pass,
            "recommendation": (
                "Keep SQLite retrieval for now"
                if threshold_pass
                else "Investigate FAISS/hybrid migration"
            ),
        },
        "per_query": results,
    }
    return report


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate retrieval migration gate metrics")
    parser.add_argument(
        "--query-set",
        default=str(REPO_ROOT / "scripts" / "migration_gate_query_set.json"),
        help="Path to fixed query set JSON",
    )
    parser.add_argument(
        "--db-path",
        default=str(REPO_ROOT / "data" / "migration_gate_eval.sqlite"),
        help="SQLite database path for evaluation",
    )
    parser.add_argument("-k", type=int, default=4, help="Top-k retrieved turns per query")
    parser.add_argument("--min-recall-at-k", type=float, default=0.80)
    parser.add_argument("--max-p95-ms", type=float, default=20.0)
    parser.add_argument("--max-p99-ms", type=float, default=30.0)
    parser.add_argument("--output-json", default="", help="Optional path to write JSON report")
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    report = run_evaluation(args)

    print("Migration Gate Evaluation")
    print(f"- recall@{report['k']}: {report['metrics']['recall_at_k']:.3f}")
    print(f"- latency p50 (ms): {report['metrics']['latency_ms_p50']:.2f}")
    print(f"- latency p95 (ms): {report['metrics']['latency_ms_p95']:.2f}")
    print(f"- latency p99 (ms): {report['metrics']['latency_ms_p99']:.2f}")
    print(f"- fts usage ratio: {report['metrics']['fts_usage_ratio']:.2f}")
    print(f"- decision: {report['decision']['recommendation']}")

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"- report written: {out_path}")

    return 0 if report["decision"]["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
