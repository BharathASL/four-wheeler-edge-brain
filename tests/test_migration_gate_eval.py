import argparse
import json

from scripts.evaluate_migration_gate import run_evaluation


def test_run_evaluation_reports_category_recall(tmp_path):
    query_set = {
        "speaker_name": "eval-user",
        "turns": [
            {
                "user": "My favorite drink is masala chai.",
                "assistant": "Got it, your favorite drink is masala chai.",
            },
            {
                "user": "I usually work from home on Fridays.",
                "assistant": "Understood, Fridays are your work-from-home days.",
            },
        ],
        "queries": [
            {
                "category": "direct",
                "query": "What drink do I like?",
                "expect_any": ["masala chai"],
            },
            {
                "category": "paraphrase",
                "query": "Which day is my work-from-home day?",
                "expect_any": ["fridays"],
            },
        ],
    }
    query_set_path = tmp_path / "query_set.json"
    query_set_path.write_text(json.dumps(query_set), encoding="utf-8")
    db_path = tmp_path / "eval.sqlite"

    args = argparse.Namespace(
        query_set=str(query_set_path),
        db_path=str(db_path),
        k=4,
        retrieval_mode="fts",
        semantic_backend="auto",
        min_recall_at_k=0.80,
        max_p95_ms=20.0,
        max_p99_ms=30.0,
        output_json="",
    )

    report = run_evaluation(args)

    assert report["metrics"]["recall_at_k"] == 1.0
    assert report["retrieval_mode"] == "fts"
    assert report["metrics"]["recall_by_category"] == {
        "direct": 1.0,
        "paraphrase": 1.0,
    }
    assert report["per_query"][0]["category"] == "direct"
    assert report["per_query"][1]["category"] == "paraphrase"