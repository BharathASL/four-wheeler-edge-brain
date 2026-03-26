#!/usr/bin/env python3
"""Evaluate DecisionEngine action quality against a fixed prompt set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.decision_engine import DecisionEngine
from src.state_manager import StateManager


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
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    report = evaluate(prompt_set_path=args.prompt_set, model_timeout=args.model_timeout)

    accuracy = float(report["metrics"]["accuracy"])
    passed = accuracy >= args.min_accuracy

    print("AI Evaluation Harness")
    print(f"- total cases: {report['metrics']['total_cases']}")
    print(f"- correct cases: {report['metrics']['correct_cases']}")
    print(f"- accuracy: {accuracy:.3f}")
    print(f"- threshold: {args.min_accuracy:.3f}")
    print(f"- decision: {'PASS' if passed else 'FAIL'}")

    if args.output_json:
        out_path = Path(args.output_json)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"- report written: {out_path}")

    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
