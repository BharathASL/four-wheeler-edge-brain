#!/usr/bin/env python3
"""Evaluate DecisionEngine action quality against a fixed prompt set."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.core.decision_engine import DecisionEngine
from src.core.state_manager import StateManager


def _load_prompt_set(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    cases = payload.get("cases") or []
    if not cases:
        raise ValueError("Prompt set must include non-empty 'cases'")

    for idx, case in enumerate(cases, start=1):
        if "input" not in case or "expected_action" not in case:
            raise ValueError(f"Case {idx} must include 'input' and 'expected_action'")
    return payload


def evaluate(prompt_set_path: str, model_timeout: float = 5.0) -> Dict[str, Any]:
    payload = _load_prompt_set(prompt_set_path)
    state = StateManager()
    engine = DecisionEngine(model_timeout=model_timeout)

    per_case: List[Dict[str, Any]] = []
    correct = 0
    confusion: Dict[str, Dict[str, int]] = {}

    for case in payload["cases"]:
        user_input = str(case["input"])
        expected = str(case["expected_action"])

        output = engine.decide(user_input, state.snapshot())
        predicted = str(output.get("action", ""))
        matched = predicted == expected
        correct += 1 if matched else 0

        if expected not in confusion:
            confusion[expected] = {}
        confusion[expected][predicted] = confusion[expected].get(predicted, 0) + 1

        per_case.append(
            {
                "input": user_input,
                "expected_action": expected,
                "predicted_action": predicted,
                "matched": matched,
            }
        )

    total = len(payload["cases"])
    accuracy = (correct / total) if total else 0.0

    return {
        "prompt_set": payload.get("metadata", {}),
        "metrics": {
            "total_cases": total,
            "correct_cases": correct,
            "accuracy": accuracy,
        },
        "confusion": confusion,
        "per_case": per_case,
    }


def _load_history(path: str) -> Dict[str, Any]:
    history_path = Path(path)
    if not history_path.exists():
        return {"runs": []}
    return json.loads(history_path.read_text(encoding="utf-8"))


def _update_history(history_path: str, report: Dict[str, Any], min_accuracy: float) -> Dict[str, Any]:
    payload = _load_history(history_path)
    runs = list(payload.get("runs") or [])

    accuracy = float(report["metrics"]["accuracy"])
    previous_accuracies = [float(run.get("accuracy", 0.0)) for run in runs]
    previous_best = max(previous_accuracies) if previous_accuracies else None
    previous_latest = previous_accuracies[-1] if previous_accuracies else None

    regression_vs_latest = None if previous_latest is None else (accuracy - previous_latest)
    regression_vs_best = None if previous_best is None else (accuracy - previous_best)
    regressed = bool(previous_latest is not None and accuracy < previous_latest)

    run_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "accuracy": accuracy,
        "total_cases": int(report["metrics"]["total_cases"]),
        "correct_cases": int(report["metrics"]["correct_cases"]),
        "threshold": float(min_accuracy),
        "prompt_set": report.get("prompt_set", {}),
    }
    runs.append(run_entry)

    updated = {"runs": runs}
    history_file = Path(history_path)
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(json.dumps(updated, indent=2), encoding="utf-8")

    trend = {
        "history_path": history_path,
        "run_count": len(runs),
        "latest_accuracy": accuracy,
        "previous_latest_accuracy": previous_latest,
        "best_accuracy": max(previous_best, accuracy) if previous_best is not None else accuracy,
        "delta_vs_latest": regression_vs_latest,
        "delta_vs_best": regression_vs_best,
        "regressed_vs_latest": regressed,
    }
    return trend


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run AI action evaluation harness")
    parser.add_argument(
        "--prompt-set",
        default=str(REPO_ROOT / "scripts" / "ai_eval_prompt_set.json"),
        help="Path to evaluation prompt set JSON",
    )
    parser.add_argument(
        "--min-accuracy",
        type=float,
        default=0.90,
        help="Minimum passing accuracy threshold",
    )
    parser.add_argument("--model-timeout", type=float, default=5.0)
    parser.add_argument("--output-json", default="", help="Optional path to write report JSON")
    parser.add_argument(
        "--history-json",
        default=str(REPO_ROOT / "data" / "ai_eval_history.json"),
        help="Path to persistent history JSON for trend tracking",
    )
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    report = evaluate(prompt_set_path=args.prompt_set, model_timeout=args.model_timeout)
    trend = _update_history(args.history_json, report, args.min_accuracy)
    report["trend"] = trend

    accuracy = float(report["metrics"]["accuracy"])
    passed = accuracy >= args.min_accuracy

    print("AI Evaluation Harness")
    print(f"- total cases: {report['metrics']['total_cases']}")
    print(f"- correct cases: {report['metrics']['correct_cases']}")
    print(f"- accuracy: {accuracy:.3f}")
    print(f"- threshold: {args.min_accuracy:.3f}")
    print(f"- run count: {trend['run_count']}")
    if trend["delta_vs_latest"] is not None:
        print(f"- delta vs previous run: {trend['delta_vs_latest']:+.3f}")
    if trend["regressed_vs_latest"]:
        print("- regression alert: current accuracy is lower than previous run")
    print(f"- decision: {'PASS' if passed else 'FAIL'}")

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"- report written: {out_path}")

    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
