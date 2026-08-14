from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .analyze_objective import analyze, has_technical_failure, is_evaluable, load_manifest, load_rows


def classify_error(text: str) -> str:
    lower = text.lower()
    if "429" in lower or "rate limit" in lower or "quota exceeded" in lower or "too_many_requests" in lower:
        return "rate_limit_or_quota"
    if "401" in lower or "403" in lower or "authentication" in lower or "api key" in lower:
        return "authentication_or_permission"
    if "timeout" in lower or "timed out" in lower:
        return "timeout"
    if "connection" in lower or "network" in lower or "dns" in lower:
        return "network"
    return "provider_or_component_error"


def error_text(row: dict[str, Any]) -> str:
    errors = [str(call.get("error")) for call in row.get("call_details", []) if call.get("error")]
    return " | ".join(errors)


def build_audit(source: Path, output: Path) -> None:
    rows = load_rows(source)
    manifest = load_manifest(source)
    output.mkdir(parents=True, exist_ok=True)
    summaries, _ = analyze(source, output_directory=output, report_name="report_corrected.md")

    failures: list[dict[str, Any]] = []
    for row in rows:
        technical = has_technical_failure(row)
        parse_failure = (not technical) and not bool(row.get("parse_success"))
        if not technical and not parse_failure:
            continue
        text = error_text(row)
        failures.append({
            "system": row.get("system"),
            "case_id": row.get("case_id"),
            "repeat": row.get("repeat"),
            "critical": row.get("critical"),
            "failure_class": classify_error(text) if technical else "parse_error",
            "error": text or row.get("parse_error"),
        })

    if failures:
        with (output / "failure_details.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(failures[0]))
            writer.writeheader()
            writer.writerows(failures)

    # Extra diagnostic: disagreement and ceiling on complete/evaluable rows only.
    by_system: dict[str, dict[tuple[str, int], dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if is_evaluable(row):
            by_system[str(row["system"])][(str(row["case_id"]), int(row.get("repeat", 0)))] = row

    complete_systems = [s for s in summaries if s["status"] == "COMPLETE"]
    lines = [
        "# Objective-run audit",
        "",
        f"- Source: `{source}`",
        f"- Protocol: `{manifest.get('benchmark', 'unknown')}`",
        f"- Split: `{manifest.get('split', 'unknown')}`",
        f"- Dataset hash: `{manifest.get('dataset_sha256', 'unknown')}`",
        "",
        "## Reliability finding",
        "",
    ]
    if failures:
        classes = Counter(item["failure_class"] for item in failures)
        lines.append(
            f"Detected {len(failures)} non-evaluable rows: "
            + ", ".join(f"{name}={count}" for name, count in sorted(classes.items()))
            + "."
        )
        lines.append(
            "Provider/component failures are not scientific reasoning errors and must not be included in valid accuracy, critical-error rate or Brier score."
        )
    else:
        lines.append("No technical or parse failures were detected.")

    lines += ["", "## Complete-system disagreement", ""]
    if len(complete_systems) >= 2:
        names = [str(item["system"]) for item in complete_systems]
        all_keys = sorted(set.intersection(*(set(by_system[name]) for name in names)))
        disagreement = 0
        for key in all_keys:
            outcomes = {bool(by_system[name][key]["correct"]) for name in names}
            disagreement += len(outcomes) > 1
        rate = 100 * disagreement / len(all_keys) if all_keys else 0.0
        lines.append(
            f"Across {len(all_keys)} jointly evaluable case/repeat pairs for complete systems, correctness outcomes differed on {disagreement} ({rate:.2f}%)."
        )
    else:
        lines.append("Fewer than two complete systems; disagreement is not interpretable.")

    ceiling = [item for item in complete_systems if item.get("valid_accuracy") == 100.0]
    if ceiling:
        lines += [
            "",
            "## Ceiling warning",
            "",
            "Complete systems at 100% valid accuracy: " + ", ".join(str(item["system"]) for item in ceiling) + ".",
            "This development set cannot measure improvement over those systems; follow the protocol stop rule and do not open the locked test solely to search for separation.",
        ]

    (output / "audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Reanalyze an objective benchmark run without API calls.")
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    source = args.run_directory
    if not (source / "results.jsonl").exists():
        raise SystemExit(f"results.jsonl non trovato in {source}")
    output = args.output or (source / "reliability_audit_v7_2")
    build_audit(source, output)
    print(f"Audit completato senza chiamate API: {output}")
    print("Apri audit.md e report_corrected.md.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
