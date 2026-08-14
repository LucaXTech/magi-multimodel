from __future__ import annotations

import json
import math
import re
from typing import Any


def clean_json_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        return cleaned[start : end + 1]
    return cleaned


def parse_answer(text: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(clean_json_text(text))
        if not isinstance(payload, dict):
            raise ValueError("L'output JSON non è un oggetto.")
        confidence = payload.get("confidence", 50)
        confidence = int(round(float(confidence)))
        payload["confidence"] = max(0, min(100, confidence))
        payload["rationale"] = str(payload.get("rationale", "")).strip()
        return payload, None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def normalize_choice(value: Any) -> str:
    return str(value).strip().upper()


def score_payload(payload: dict[str, Any] | None, case: dict[str, Any]) -> dict[str, Any]:
    if payload is None:
        return {
            "parse_success": False,
            "correct": False,
            "score": 0.0,
            # Missing or malformed output has no probabilistic forecast to score.
            # Availability is reported separately by the analyzer.
            "brier": None,
            "confidence": None,
            "predicted_answer": None,
        }

    kind = case["type"]
    predicted = payload.get("answer")
    correct = False
    partial = 0.0

    if kind in {"mcq", "true_false"}:
        expected = normalize_choice(case["answer"])
        actual = normalize_choice(predicted)
        correct = actual == expected
        partial = 1.0 if correct else 0.0
        predicted_normalized: Any = actual
    elif kind == "multi_select":
        if isinstance(predicted, str):
            predicted_values = [item for item in re.split(r"[,;\s]+", predicted) if item]
        elif isinstance(predicted, list):
            predicted_values = predicted
        else:
            predicted_values = []
        actual_set = {normalize_choice(item) for item in predicted_values}
        expected_set = {normalize_choice(item) for item in case["answer"]}
        union = actual_set | expected_set
        partial = len(actual_set & expected_set) / len(union) if union else 1.0
        correct = actual_set == expected_set
        predicted_normalized = sorted(actual_set)
    elif kind == "numeric":
        try:
            actual_number = float(predicted)
            expected_number = float(case["answer"])
            abs_tol = float(case.get("tolerance_abs", 0.0))
            rel_tol = float(case.get("tolerance_rel", 0.0))
            allowed = max(abs_tol, abs(expected_number) * rel_tol)
            error = abs(actual_number - expected_number)
            correct = error <= allowed + 1e-12
            if allowed > 0:
                partial = max(0.0, 1.0 - error / (allowed * 4.0))
            else:
                partial = 1.0 if correct else 0.0
            predicted_normalized = actual_number
        except (TypeError, ValueError):
            predicted_normalized = predicted
            partial = 0.0
            correct = False
    else:
        raise ValueError(f"Tipo di caso non supportato: {kind}")

    confidence = int(payload.get("confidence", 50))
    probability = confidence / 100.0
    outcome = 1.0 if correct else 0.0
    brier = (probability - outcome) ** 2

    return {
        "parse_success": True,
        "correct": correct,
        "score": round(partial * 100.0, 4),
        "brier": round(brier, 6),
        "confidence": confidence,
        "predicted_answer": predicted_normalized,
    }


def format_case(case: dict[str, Any]) -> str:
    # Case IDs are metadata only: exposing semantic IDs can leak the tested skill.
    lines = [f"DOMANDA: {case['question']}"]
    options = case.get("options") or {}
    if options:
        lines.append("OPZIONI:")
        for key, value in options.items():
            lines.append(f"{key}. {value}")
    if case["type"] == "multi_select":
        lines.append("Può essere corretta più di una opzione.")
    if case["type"] == "numeric":
        unit = case.get("unit", "")
        lines.append(f"Rispondi con un numero{f' in {unit}' if unit else ''}.")
    return "\n".join(lines)


def response_schema(case: dict[str, Any]) -> str:
    kind = case["type"]
    if kind == "multi_select":
        answer_example = '["A", "C"]'
    elif kind == "numeric":
        answer_example = "0.8"
    else:
        answer_example = '"B"'
    return (
        '{"answer": ' + answer_example + ', "confidence": 0, '
        '"rationale": "massimo 70 parole"}'
    )
