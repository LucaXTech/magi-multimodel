from __future__ import annotations

import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


MIN_COMPLETE_COVERAGE = 1.0


def load_rows(directory: Path) -> list[dict[str, Any]]:
    path = directory / "results.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_manifest(directory: Path) -> dict[str, Any]:
    path = directory / "manifest.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def bootstrap_delta(
    a: list[float],
    b: list[float],
    seed: int = 20260806,
    draws: int = 5000,
) -> tuple[float, float, float]:
    if len(a) != len(b) or not a:
        return math.nan, math.nan, math.nan
    deltas = [x - y for x, y in zip(a, b, strict=True)]
    rng = random.Random(seed)
    sims = [mean(rng.choice(deltas) for _ in deltas) for _ in range(draws)]
    sims.sort()
    lo = sims[int(0.025 * (len(sims) - 1))]
    hi = sims[int(0.975 * (len(sims) - 1))]
    return mean(deltas), lo, hi


def exact_mcnemar_p(b: int, c: int) -> float:
    """Two-sided exact binomial McNemar p-value."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * tail)


def _safe_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _call_has_error(call: dict[str, Any]) -> bool:
    return bool(call.get("error")) or str(call.get("status", "")).lower() == "error"


def has_technical_failure(row: dict[str, Any]) -> bool:
    """Return True when transport/provider/component execution failed.

    Backwards-compatible with v3 rows, which did not carry an explicit
    ``technical_failure`` flag but did store ``errors`` and ``call_details``.
    """
    if row.get("technical_failure") is not None:
        return bool(row["technical_failure"])
    if int(row.get("errors", 0) or 0) > 0:
        return True
    return any(_call_has_error(call) for call in row.get("call_details", []))


def is_evaluable(row: dict[str, Any]) -> bool:
    """A reasoning score is evaluable only with a complete technical run and parsed output."""
    return not has_technical_failure(row) and bool(row.get("parse_success"))


def output_is_scorable(row: dict[str, Any]) -> bool:
    """Final output can be scored even if an upstream multi-agent component degraded."""
    return bool(row.get("parse_success"))


def _fmt_pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.2f}%"


def analyze(
    directory: Path,
    *,
    output_directory: Path | None = None,
    report_name: str = "report.md",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows(directory)
    manifest = load_manifest(directory)
    out = output_directory or directory
    out.mkdir(parents=True, exist_ok=True)

    by_system: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_system[row["system"]].append(row)

    summaries: list[dict[str, Any]] = []
    for system, items in sorted(by_system.items()):
        technical = [item for item in items if has_technical_failure(item)]
        nontechnical = [item for item in items if not has_technical_failure(item)]
        parse_failures = [item for item in nontechnical if not bool(item.get("parse_success"))]
        evaluable = [item for item in items if is_evaluable(item)]
        scorable_outputs = [item for item in items if output_is_scorable(item)]
        critical_evaluable = [item for item in evaluable if item.get("critical")]
        critical_technical = [item for item in technical if item.get("critical")]

        briers = [float(item["brier"]) for item in evaluable if item.get("brier") is not None]
        tokens = [int(item["total_tokens"]) for item in evaluable if item.get("total_tokens") is not None]
        costs = [float(item["estimated_cost_usd"]) for item in items if item.get("estimated_cost_usd") is not None]
        correct_evaluable = sum(bool(item.get("correct")) for item in evaluable)
        operational_correct = sum(bool(item.get("correct")) for item in items)
        coverage = len(evaluable) / len(items) if items else 0.0
        output_coverage = len(scorable_outputs) / len(items) if items else 0.0
        total_cost = sum(costs) if len(costs) == len(items) else None
        status = "COMPLETE" if coverage >= MIN_COMPLETE_COVERAGE else "INCOMPLETE"

        valid_accuracy = 100 * correct_evaluable / len(evaluable) if evaluable else None
        mean_score = _safe_mean([float(item["score"]) for item in evaluable])
        critical_error_rate = (
            100 * sum(not bool(item.get("correct")) for item in critical_evaluable) / len(critical_evaluable)
            if critical_evaluable
            else None
        )

        summary = {
            "system": system,
            "status": status,
            "planned_n": len(items),
            "evaluable_n": len(evaluable),
            "coverage": round(100 * coverage, 2),
            "output_coverage": round(100 * output_coverage, 2),
            "valid_accuracy": round(valid_accuracy, 2) if valid_accuracy is not None else None,
            "end_to_end_accuracy": round(100 * operational_correct / len(items), 2) if items else None,
            "mean_score": round(mean_score, 2) if mean_score is not None else None,
            "technical_failures": len(technical),
            "technical_failure_rate": round(100 * len(technical) / len(items), 2) if items else None,
            "parse_failures": len(parse_failures),
            "parse_failure_rate_nontechnical": (
                round(100 * len(parse_failures) / len(nontechnical), 2) if nontechnical else None
            ),
            "critical_evaluable_n": len(critical_evaluable),
            "critical_error_rate": round(critical_error_rate, 2) if critical_error_rate is not None else None,
            "critical_technical_failures": len(critical_technical),
            "mean_brier": round(mean(briers), 4) if briers else None,
            "mean_confidence": (
                round(mean(float(item["confidence"]) for item in evaluable if item.get("confidence") is not None), 2)
                if any(item.get("confidence") is not None for item in evaluable)
                else None
            ),
            "mean_time_seconds": round(mean(float(item["wall_time_seconds"]) for item in items), 3),
            "mean_evaluable_time_seconds": (
                round(mean(float(item["wall_time_seconds"]) for item in evaluable), 3) if evaluable else None
            ),
            "mean_tokens": round(mean(tokens), 1) if tokens else None,
            "total_cost_usd": round(total_cost, 6) if total_cost is not None else None,
            "cost_per_valid_correct_usd": (
                round(total_cost / correct_evaluable, 6)
                if total_cost is not None and correct_evaluable
                else None
            ),
            "errors": sum(int(item.get("errors", 0) or 0) for item in items),
            # Backwards-compatible aliases consumed by the CLI.
            "n": len(items),
            "accuracy": round(valid_accuracy, 2) if valid_accuracy is not None else None,
            "parse_success": round(100 * len(evaluable) / len(items), 2) if items else None,
            "cost_per_correct_usd": (
                round(total_cost / correct_evaluable, 6)
                if total_cost is not None and correct_evaluable
                else None
            ),
        }
        summaries.append(summary)

    # Descriptive breakdown: reasoning metrics are calculated only on evaluable rows.
    breakdown: list[dict[str, Any]] = []
    for system, items in sorted(by_system.items()):
        for dimension in ("category", "difficulty", "case_type"):
            groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for item in items:
                groups[str(item[dimension])].append(item)
            for value, group in sorted(groups.items()):
                evaluable = [item for item in group if is_evaluable(item)]
                breakdown.append({
                    "system": system,
                    "dimension": dimension,
                    "value": value,
                    "planned_n": len(group),
                    "evaluable_n": len(evaluable),
                    "coverage": round(100 * len(evaluable) / len(group), 2) if group else None,
                    "valid_accuracy": (
                        round(100 * mean(bool(item["correct"]) for item in evaluable), 2)
                        if evaluable
                        else None
                    ),
                    "mean_score": (
                        round(mean(float(item["score"]) for item in evaluable), 2)
                        if evaluable
                        else None
                    ),
                })

    reference = manifest.get("reference_system")
    comparisons: list[dict[str, Any]] = []
    if reference and reference in by_system:
        reference_map = {
            (row["case_id"], row["repeat"]): row
            for row in by_system[reference]
            if is_evaluable(row)
        }
        for system, items in sorted(by_system.items()):
            if system == reference:
                continue
            pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
            for row in items:
                if not is_evaluable(row):
                    continue
                key = (row["case_id"], row["repeat"])
                if key in reference_map:
                    pairs.append((row, reference_map[key]))
            if not pairs:
                continue
            system_correct = [1.0 if a["correct"] else 0.0 for a, _ in pairs]
            reference_correct = [1.0 if b["correct"] else 0.0 for _, b in pairs]
            acc_delta, acc_lo, acc_hi = bootstrap_delta(system_correct, reference_correct)
            score_delta, score_lo, score_hi = bootstrap_delta(
                [float(a["score"]) for a, _ in pairs],
                [float(b["score"]) for _, b in pairs],
            )
            b = sum(bool(a["correct"]) and not bool(r["correct"]) for a, r in pairs)
            c = sum(not bool(a["correct"]) and bool(r["correct"]) for a, r in pairs)
            comparisons.append({
                "system": system,
                "reference": reference,
                "paired_evaluable_n": len(pairs),
                "accuracy_delta_pp": round(100 * acc_delta, 2),
                "accuracy_ci95_low_pp": round(100 * acc_lo, 2),
                "accuracy_ci95_high_pp": round(100 * acc_hi, 2),
                "score_delta": round(score_delta, 2),
                "score_ci95_low": round(score_lo, 2),
                "score_ci95_high": round(score_hi, 2),
                "discordant_system_wins": b,
                "discordant_reference_wins": c,
                "mcnemar_exact_p": round(exact_mcnemar_p(b, c), 6),
            })

    # Consistency across repeated option permutations, only when every repeated row is evaluable.
    consistency: list[dict[str, Any]] = []
    for system, items in sorted(by_system.items()):
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            groups[item["case_id"]].append(item)
        eligible = [group for group in groups.values() if len(group) > 1 and all(is_evaluable(x) for x in group)]
        if eligible:
            stable = 0
            for group in eligible:
                answers = [json.dumps(item.get("canonical_predicted_answer"), sort_keys=True) for item in group]
                stable += len(set(answers)) == 1
            consistency.append({
                "system": system,
                "cases_with_complete_repeats": len(eligible),
                "canonical_answer_consistency": round(100 * stable / len(eligible), 2),
            })

    def write_csv(name: str, data: list[dict[str, Any]]) -> None:
        if not data:
            return
        with (out / name).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)

    write_csv("summary.csv", summaries)
    write_csv("breakdown.csv", breakdown)
    write_csv("paired_comparisons.csv", comparisons)
    write_csv("permutation_consistency.csv", consistency)

    lines = [
        "# MAGI Objective Benchmark — reliability-corrected report",
        "",
        f"- Source protocol: `{manifest.get('benchmark', manifest.get('protocol_version', 'unknown'))}`",
        f"- Split: `{manifest.get('split', 'unknown')}`",
        f"- Protocol hash: `{manifest.get('dataset_sha256', 'unknown')}`",
        f"- Selection: `{manifest.get('selection', 'unknown')}`",
        f"- Option order: `{manifest.get('option_order', 'unknown')}`",
        f"- System order: `{manifest.get('system_order', 'unknown')}`",
        f"- Reference system: `{reference or 'not specified'}`",
        "",
        "## Aggregate results",
        "",
        "| System | Status | Evaluable/planned | Coverage | Valid accuracy | End-to-end accuracy | Technical failures | Critical reasoning errors | Brier | Time (s) | Tokens |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in summaries:
        lines.append(
            f"| {item['system']} | {item['status']} | {item['evaluable_n']}/{item['planned_n']} | "
            f"{item['coverage']:.2f}% | {_fmt_pct(item['valid_accuracy'])} | "
            f"{_fmt_pct(item['end_to_end_accuracy'])} | {item['technical_failures']} | "
            f"{_fmt_pct(item['critical_error_rate'])} "
            f"(n={item['critical_evaluable_n']}) | "
            f"{item['mean_brier'] if item['mean_brier'] is not None else 'n/a'} | "
            f"{item['mean_time_seconds']:.3f} | "
            f"{item['mean_tokens'] if item['mean_tokens'] is not None else 'n/a'} |"
        )

    incomplete = [item for item in summaries if item["status"] != "COMPLETE"]
    lines += [
        "",
        "**Interpretation rule:** provider/API failures are availability failures, not wrong scientific answers. "
        "Valid accuracy, critical-error rate and Brier use only technically complete, parsed rows. "
        "End-to-end accuracy keeps missing outputs as failures and is reported separately.",
    ]
    if incomplete:
        names = ", ".join(item["system"] for item in incomplete)
        lines += [
            "",
            f"> **INCOMPLETE SYSTEMS: {names}.** They are not eligible for model ranking or baseline selection until failed rows are recovered.",
        ]

    if comparisons:
        lines += [
            "",
            f"## Paired comparisons against prespecified reference: {reference}",
            "",
            "Only case/repeat pairs evaluable for both systems are included.",
            "",
            "| System | Paired evaluable | Accuracy Δ pp [95% bootstrap CI] | Discordant wins/losses | Exact McNemar p |",
            "|---|---:|---:|---:|---:|",
        ]
        for item in comparisons:
            lines.append(
                f"| {item['system']} | {item['paired_evaluable_n']} | {item['accuracy_delta_pp']:.2f} "
                f"[{item['accuracy_ci95_low_pp']:.2f}, {item['accuracy_ci95_high_pp']:.2f}] | "
                f"{item['discordant_system_wins']}/{item['discordant_reference_wins']} | {item['mcnemar_exact_p']} |"
            )
    if consistency:
        lines += [
            "",
            "## Option-permutation consistency",
            "",
            "| System | Cases with complete repeats | Canonical answer consistency |",
            "|---|---:|---:|",
        ]
        for item in consistency:
            lines.append(
                f"| {item['system']} | {item['cases_with_complete_repeats']} | "
                f"{item['canonical_answer_consistency']:.2f}% |"
            )
    if manifest.get("mock"):
        lines += ["", "> MOCK/SMOKE TEST: performance numbers are not interpretable and must not be used as model results."]

    (out / report_name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summaries, comparisons
