from __future__ import annotations

import argparse
import csv
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


def load_rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def exact_mcnemar_p(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2.0 * tail)


def bootstrap_diff(values: list[float], seed: int = 20260806, n_boot: int = 5000) -> tuple[float, float, float]:
    if not values:
        return 0.0, 0.0, 0.0
    rng = random.Random(seed)
    estimates = []
    for _ in range(n_boot):
        sample = [rng.choice(values) for _ in values]
        estimates.append(mean(sample))
    estimates.sort()
    lo = estimates[int(0.025 * (len(estimates) - 1))]
    hi = estimates[int(0.975 * (len(estimates) - 1))]
    return mean(values), lo, hi


def summarize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_system: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_system[row["system"]].append(row)
    out = []
    for system, items in sorted(by_system.items()):
        token_values = [r.get("total_tokens") for r in items if r.get("total_tokens") is not None]
        cost_values = [r.get("estimated_cost_usd") for r in items if r.get("estimated_cost_usd") is not None]
        out.append({
            "system": system,
            "n": len(items),
            "mean_score": round(mean(float(r["score"]) for r in items), 3),
            "correct_rate": round(mean(float(bool(r["correct"])) for r in items), 4),
            "critical_error_rate": round(mean(float(bool(r["critical_error"])) for r in items), 4),
            "mean_concept_recall": round(mean(float(r["concept_recall"]) for r in items), 4),
            "mean_wall_time_seconds": round(mean(float(r.get("wall_time_seconds") or 0) for r in items), 3),
            "mean_tokens": round(mean(token_values), 1) if token_values else None,
            "mean_estimated_cost_usd": round(mean(cost_values), 6) if cost_values else None,
        })
    return out


def paired_comparisons(rows: list[dict[str, Any]], summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baselines = [s for s in summaries if s["system"] in {"openai", "anthropic", "gemini", "groq"}]
    if not baselines:
        return []
    best = max(baselines, key=lambda s: s["mean_score"])["system"]
    index = {(r["case_id"], r["repeat"], r["system"]): r for r in rows}
    systems = sorted({r["system"] for r in rows if r["system"].startswith("magi_")})
    comparisons = []
    keys = sorted({(r["case_id"], r["repeat"]) for r in rows})
    for system in systems:
        pairs = []
        b = c = 0
        wins = losses = ties = 0
        for case_id, repeat in keys:
            base = index.get((case_id, repeat, best))
            magi = index.get((case_id, repeat, system))
            if not base or not magi:
                continue
            diff = float(magi["score"]) - float(base["score"])
            pairs.append(diff)
            if diff > 0: wins += 1
            elif diff < 0: losses += 1
            else: ties += 1
            base_ok = bool(base["correct"]); magi_ok = bool(magi["correct"])
            if base_ok and not magi_ok: b += 1
            elif magi_ok and not base_ok: c += 1
        avg, lo, hi = bootstrap_diff(pairs)
        comparisons.append({
            "magi_system": system,
            "reference_baseline": best,
            "n_pairs": len(pairs),
            "mean_score_difference": round(avg, 3),
            "bootstrap_95_ci_low": round(lo, 3),
            "bootstrap_95_ci_high": round(hi, 3),
            "wins": wins, "ties": ties, "losses": losses,
            "mcnemar_b_baseline_only_correct": b,
            "mcnemar_c_magi_only_correct": c,
            "mcnemar_exact_p": round(exact_mcnemar_p(b, c), 6),
        })
    return comparisons


def write_outputs(directory: Path, summaries: list[dict[str, Any]], comparisons: list[dict[str, Any]]) -> None:
    with (directory / "summary.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summaries[0]) if summaries else ["system"])
        writer.writeheader(); writer.writerows(summaries)
    if comparisons:
        with (directory / "paired_comparisons.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(comparisons[0])); writer.writeheader(); writer.writerows(comparisons)

    lines = ["# MAGI Benchmark Report", "", "## Aggregate results", "", "| System | N | Rubric score | Auto-pass | Critical flags | Mean time (s) | Mean tokens |", "|---|---:|---:|---:|---:|---:|---:|"]
    for s in summaries:
        lines.append(f"| {s['system']} | {s['n']} | {s['mean_score']:.2f} | {100*s['correct_rate']:.1f}% | {100*s['critical_error_rate']:.1f}% | {s['mean_wall_time_seconds']:.2f} | {s['mean_tokens'] if s['mean_tokens'] is not None else 'n/a'} |")
    lines += ["", "The deterministic score measures rubric coverage. Auto-pass and critical flags are automatic screening signals, not human-verified correctness.", ""]
    if comparisons:
        lines += ["## Paired comparisons", "", "| MAGI | Baseline | Pairs | Mean Δ score [95% bootstrap CI] | W/T/L | McNemar p |", "|---|---|---:|---:|---:|---:|"]
        for c in comparisons:
            lines.append(f"| {c['magi_system']} | {c['reference_baseline']} | {c['n_pairs']} | {c['mean_score_difference']:.2f} [{c['bootstrap_95_ci_low']:.2f}, {c['bootstrap_95_ci_high']:.2f}] | {c['wins']}/{c['ties']}/{c['losses']} | {c['mcnemar_exact_p']:.4f} |")
    (directory / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze_directory(directory: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows = load_rows(directory / "results.jsonl")
    summaries = summarize(rows)
    comparisons = paired_comparisons(rows, summaries)
    write_outputs(directory, summaries, comparisons)
    return summaries, comparisons


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    summaries, comparisons = analyze_directory(args.directory)
    print(json.dumps({"summaries": summaries, "comparisons": comparisons}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
