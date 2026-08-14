from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any

from .protocol import (
    OPTION_LABELS,
    VALID_DIFFICULTIES,
    VALID_SPLITS,
    VALID_TYPES,
    load_cases,
    normalized_question,
    verify_lock,
)


def validate() -> list[str]:
    errors: list[str] = []
    cases = load_cases()
    seen_ids: set[str] = set()
    seen_questions: dict[str, str] = {}

    for index, case in enumerate(cases, start=1):
        prefix = f"riga {index} ({case.get('id', '?')})"
        case_id = str(case.get("id", ""))
        if not case_id or case_id in seen_ids:
            errors.append(f"{prefix}: ID mancante o duplicato")
        seen_ids.add(case_id)

        question = str(case.get("question", "")).strip()
        fingerprint = normalized_question(question)
        if not question or fingerprint in seen_questions:
            other = seen_questions.get(fingerprint)
            errors.append(f"{prefix}: domanda mancante o duplicata di {other}")
        seen_questions[fingerprint] = case_id

        if case.get("split") not in VALID_SPLITS:
            errors.append(f"{prefix}: split non valido")
        if case.get("difficulty") not in VALID_DIFFICULTIES:
            errors.append(f"{prefix}: difficulty non valida")
        if case.get("type") not in VALID_TYPES:
            errors.append(f"{prefix}: type non valido")
        if not case.get("category") or not case.get("skill"):
            errors.append(f"{prefix}: category e skill sono obbligatori")
        if case.get("language") != "it" or not case.get("provenance") or not case.get("review_status"):
            errors.append(f"{prefix}: language, provenance e review_status sono obbligatori")
        if not isinstance(case.get("critical"), bool):
            errors.append(f"{prefix}: critical deve essere booleano")
        if not case.get("explanation") or "answer" not in case:
            errors.append(f"{prefix}: answer ed explanation sono obbligatori")

        kind = case.get("type")
        if kind in {"mcq", "multi_select"}:
            options = case.get("options")
            if not isinstance(options, dict) or tuple(options) != OPTION_LABELS:
                errors.append(f"{prefix}: opzioni obbligatorie e ordinate A-D")
                continue
            answers = case["answer"] if kind == "multi_select" else [case["answer"]]
            if kind == "multi_select" and (not isinstance(answers, list) or len(answers) < 2):
                errors.append(f"{prefix}: multi_select deve avere almeno due risposte")
            for answer in answers:
                if str(answer) not in options:
                    errors.append(f"{prefix}: risposta {answer} non presente nelle opzioni")
        elif kind == "numeric":
            try:
                float(case["answer"])
            except (TypeError, ValueError):
                errors.append(f"{prefix}: risposta numerica non valida")
            if float(case.get("tolerance_abs", 0.0)) <= 0 and float(case.get("tolerance_rel", 0.0)) <= 0:
                errors.append(f"{prefix}: il caso numerico deve avere una tolleranza positiva")

    # Structural invariants: same blueprint in dev and test.
    for split in sorted(VALID_SPLITS):
        subset = [case for case in cases if case.get("split") == split]
        if len(subset) != 24:
            errors.append(f"split {split}: attesi 24 casi, trovati {len(subset)}")
        category_counts = Counter(case.get("category") for case in subset)
        if set(category_counts.values()) != {4} or len(category_counts) != 6:
            errors.append(f"split {split}: attesi 6 domini × 4 casi, trovati {dict(category_counts)}")
        type_counts = Counter(case.get("type") for case in subset)
        expected_types = {"mcq": 12, "multi_select": 6, "numeric": 6}
        if dict(type_counts) != expected_types:
            errors.append(f"split {split}: mix di formati errato {dict(type_counts)}")
        labels = Counter(case["answer"] for case in subset if case.get("type") == "mcq")
        if labels != Counter({"A": 3, "B": 3, "C": 3, "D": 3}):
            errors.append(f"split {split}: answer-position non bilanciata {dict(labels)}")

        multi_counts = Counter(len(case["answer"]) for case in subset if case.get("type") == "multi_select")
        if multi_counts != Counter({2: 3, 3: 3}):
            errors.append(f"split {split}: numero di opzioni corrette multi-select sbilanciato {dict(multi_counts)}")

        length_diffs: list[float] = []
        correct_is_longest = 0
        mcq_items = [case for case in subset if case.get("type") == "mcq"]
        for case in mcq_items:
            lengths = {key: len(value) for key, value in case["options"].items()}
            correct_len = lengths[case["answer"]]
            length_diffs.append(correct_len - mean(value for key, value in lengths.items() if key != case["answer"]))
            correct_is_longest += correct_len == max(lengths.values())
        if abs(mean(length_diffs)) > 10 or correct_is_longest > len(mcq_items) / 2:
            errors.append(
                f"split {split}: possibile length cue (mean diff={mean(length_diffs):.1f}, "
                f"correct-longest={correct_is_longest}/{len(mcq_items)})"
            )

    return errors


def describe() -> dict[str, Any]:
    cases = load_cases()
    return {
        split: {
            "n": len(subset := [case for case in cases if case["split"] == split]),
            "categories": dict(Counter(case["category"] for case in subset)),
            "types": dict(Counter(case["type"] for case in subset)),
            "difficulties": dict(Counter(case["difficulty"] for case in subset)),
            "critical": sum(bool(case["critical"]) for case in subset),
            "mcq_answers": dict(Counter(case["answer"] for case in subset if case["type"] == "mcq")),
        }
        for split in sorted(VALID_SPLITS)
    }


def main() -> int:
    errors = validate()
    if errors:
        print("Errori:")
        for error in errors:
            print("-", error)
        return 1
    cases = load_cases()
    print(f"Validi: {len(cases)} casi oggettivi v3")
    for split, info in describe().items():
        print(
            f"- {split}: n={info['n']}, categorie={info['categories']}, "
            f"tipi={info['types']}, difficoltà={info['difficulties']}, "
            f"critical={info['critical']}, MCQ={info['mcq_answers']}"
        )
    ok, message = verify_lock()
    print(f"- lock: {'OK' if ok else 'NON VALIDO'} — {message}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
