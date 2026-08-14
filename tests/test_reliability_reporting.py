from __future__ import annotations

import json
from pathlib import Path

from benchmark.analyze_objective import analyze, has_technical_failure
from benchmark.objective_scoring import score_payload


def _row(system: str, case_id: str, *, correct: bool, critical: bool = False) -> dict:
    return {
        "system": system,
        "case_id": case_id,
        "repeat": 0,
        "category": "metrics",
        "difficulty": "hard",
        "case_type": "mcq",
        "critical": critical,
        "parse_success": True,
        "correct": correct,
        "score": 100.0 if correct else 0.0,
        "brier": 0.01,
        "confidence": 90,
        "total_tokens": 100,
        "estimated_cost_usd": None,
        "wall_time_seconds": 1.0,
        "errors": 0,
        "call_details": [{"error": None, "status": "completed"}],
        "canonical_predicted_answer": "A",
    }


def test_missing_payload_has_no_brier() -> None:
    scored = score_payload(None, {"type": "mcq", "answer": "A"})
    assert scored["parse_success"] is False
    assert scored["brier"] is None


def test_technical_failure_not_counted_as_reasoning_error(tmp_path: Path) -> None:
    rows = [
        _row("complete", "c1", correct=True, critical=True),
        _row("complete", "c2", correct=False, critical=True),
        _row("partial", "c1", correct=True, critical=True),
        {
            **_row("partial", "c2", correct=False, critical=True),
            "parse_success": False,
            "brier": 1.0,  # legacy v7.1 row
            "errors": 1,
            "call_details": [{"error": "RateLimitError: 429 quota exceeded", "status": "error"}],
        },
    ]
    (tmp_path / "results.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps({"benchmark": "objective_v3", "split": "dev"}), encoding="utf-8"
    )

    summaries, _ = analyze(tmp_path)
    by_system = {row["system"]: row for row in summaries}

    assert by_system["complete"]["status"] == "COMPLETE"
    assert by_system["complete"]["valid_accuracy"] == 50.0
    assert by_system["complete"]["critical_error_rate"] == 50.0

    partial = by_system["partial"]
    assert partial["status"] == "INCOMPLETE"
    assert partial["coverage"] == 50.0
    assert partial["valid_accuracy"] == 100.0
    assert partial["end_to_end_accuracy"] == 50.0
    assert partial["technical_failures"] == 1
    assert partial["critical_error_rate"] == 0.0

    assert has_technical_failure(rows[-1]) is True
