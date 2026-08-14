from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path
from statistics import mean

from magi.config import Settings
from magi.orchestrator import MagiOrchestrator
from magi.providers import PROVIDER_NAMES, build_providers


CASES_PATH = Path(__file__).with_name("cases.jsonl")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def score_text(
    text: str,
    expected_groups: list[list[str]],
    red_flags: list[str],
) -> dict[str, float | int]:
    normalized = normalize(text)
    matched = sum(
        any(normalize(term) in normalized for term in alternatives)
        for alternatives in expected_groups
    )
    red_hits = sum(normalize(flag) in normalized for flag in red_flags)
    raw = matched / max(len(expected_groups), 1)
    score = max(0.0, raw - 0.25 * red_hits)
    return {
        "matched_groups": matched,
        "total_groups": len(expected_groups),
        "red_flag_hits": red_hits,
        "score": round(score, 3),
    }


def load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true")
    mode.add_argument(
        "--real", nargs="+", choices=PROVIDER_NAMES, metavar="PROVIDER"
    )
    parser.add_argument("--critique", action="store_true")
    parser.add_argument("--auditor", action="store_true")
    args = parser.parse_args()

    settings = Settings.from_env()
    providers = build_providers(
        settings, mock=args.mock, real_providers=args.real
    )
    orchestrator = MagiOrchestrator(settings, providers)

    rows = []
    for case in load_cases():
        run, path = orchestrator.run(
            case["question"], critique=args.critique, auditor=args.auditor
        )
        verdict = run.verdict.text if run.verdict and not run.verdict.error else ""
        row = {
            "id": case["id"],
            **score_text(verdict, case["expected_groups"], case["red_flags"]),
            "run_path": path,
        }
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))

    average = mean(float(row["score"]) for row in rows) if rows else 0.0
    print(f"\nPunteggio medio MAGI: {average:.3f}")
    print("Nota: smoke test lessicale, non valutazione scientifica definitiva.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
