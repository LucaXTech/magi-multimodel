from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .analyze_results import analyze_directory
from .run_experiment import load_cases
from .scoring import score_response


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ricalcola le rubriche senza nuove chiamate API")
    parser.add_argument("directory", type=Path, help="Cartella benchmark che contiene results.jsonl")
    parser.add_argument("--output-name", default="rescored_v2")
    args = parser.parse_args()

    source = args.directory
    source_results = source / "results.jsonl"
    if not source_results.exists():
        raise SystemExit(f"File non trovato: {source_results}")

    cases = {case["id"]: case for case in load_cases()}
    rows = load_rows(source_results)
    output = source / args.output_name
    if output.exists():
        output = source / f"{args.output_name}_{datetime.now().strftime('%H%M%S')}"
    output.mkdir(parents=True)

    audit_rows = []
    with (output / "results.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            case = cases.get(row["case_id"])
            if case is None:
                raise SystemExit(f"Caso non trovato nella rubrica corrente: {row['case_id']}")
            previous = {
                "score": row.get("score"),
                "correct": row.get("correct"),
                "critical_error": row.get("critical_error"),
                "concept_details": row.get("concept_details"),
                "critical_error_details": row.get("critical_error_details"),
            }
            new_rubric = score_response(row.get("response", ""), case)
            updated = dict(row)
            updated["previous_rubric"] = previous
            updated.update(new_rubric)
            handle.write(json.dumps(updated, ensure_ascii=False) + "\n")
            audit_rows.append({
                "case_id": row["case_id"],
                "system": row["system"],
                "old_score": previous["score"],
                "new_score": new_rubric["score"],
                "old_critical": previous["critical_error"],
                "new_critical": new_rubric["critical_error"],
                "new_matched_concepts": new_rubric["matched_concepts"],
                "new_total_concepts": new_rubric["total_concepts"],
                "critical_evidence": json.dumps(new_rubric["critical_error_details"], ensure_ascii=False),
            })

    with (output / "score_audit.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]) if audit_rows else ["case_id"])
        writer.writeheader()
        writer.writerows(audit_rows)

    summaries, _ = analyze_directory(output)
    print(f"Ricalcolo completato senza chiamate API: {output}")
    for item in summaries:
        print(
            f"{item['system']}: rubric_score={item['mean_score']:.2f}, "
            f"auto_pass={100*item['correct_rate']:.1f}%, "
            f"critical_flags={100*item['critical_error_rate']:.1f}%"
        )
    print("Controlla score_audit.csv. Le critical flag automatiche restano un proxy ad alta precisione, non una ground truth.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
