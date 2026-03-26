import json

from scripts.evaluate_ai_harness import _update_history


def test_update_history_records_first_run(tmp_path):
    history_path = tmp_path / "history.json"
    report = {
        "prompt_set": {"name": "baseline"},
        "metrics": {
            "total_cases": 10,
            "correct_cases": 9,
            "accuracy": 0.9,
        },
    }

    trend = _update_history(str(history_path), report, min_accuracy=0.9)

    saved = json.loads(history_path.read_text(encoding="utf-8"))
    assert trend["run_count"] == 1
    assert trend["latest_accuracy"] == 0.9
    assert trend["previous_latest_accuracy"] is None
    assert trend["regressed_vs_latest"] is False
    assert len(saved["runs"]) == 1


def test_update_history_flags_regression_against_previous_run(tmp_path):
    history_path = tmp_path / "history.json"
    history_path.write_text(
        json.dumps(
            {
                "runs": [
                    {
                        "timestamp": "2026-03-26T00:00:00+00:00",
                        "accuracy": 1.0,
                        "total_cases": 10,
                        "correct_cases": 10,
                        "threshold": 0.9,
                        "prompt_set": {"name": "baseline"},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    report = {
        "prompt_set": {"name": "baseline"},
        "metrics": {
            "total_cases": 10,
            "correct_cases": 8,
            "accuracy": 0.8,
        },
    }

    trend = _update_history(str(history_path), report, min_accuracy=0.9)

    assert trend["run_count"] == 2
    assert trend["previous_latest_accuracy"] == 1.0
    assert trend["delta_vs_latest"] == -0.19999999999999996
    assert trend["regressed_vs_latest"] is True