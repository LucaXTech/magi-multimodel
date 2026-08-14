from __future__ import annotations

import argparse
import json
import time
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from dataclasses import replace

from magi.config import Settings
from magi.providers import PROVIDER_NAMES, build_providers

from .analyze_objective import analyze, has_technical_failure, load_manifest, load_rows
from .objective_scoring import parse_answer, score_payload
from .protocol import load_cases, permute_case_options, sha256_file
from .run_objective import (
    SYSTEMS,
    call_metadata,
    calls_per_case,
    canonical_predicted_answer,
    estimate_cost,
    execute_system,
    load_pricing,
    required_providers,
)


def needs_recovery(row: dict[str, Any]) -> bool:
    return has_technical_failure(row) or not bool(row.get("parse_success"))


def is_rate_limit_error(calls: list[dict[str, Any]]) -> bool:
    text = " ".join(str(call.get("error") or "") for call in calls).lower()
    return any(token in text for token in ("429", "rate limit", "quota exceeded", "too_many_requests"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recover only failed objective-benchmark rows without rerunning successful calls."
    )
    parser.add_argument("run_directory", type=Path)
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true")
    mode.add_argument("--real", action="append", choices=PROVIDER_NAMES, metavar="PROVIDER")
    parser.add_argument("--judge-provider", choices=PROVIDER_NAMES, default=None)
    parser.add_argument("--pricing", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("objective_results_v3"))
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--continue-on-rate-limit", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-hybrid", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    source = args.run_directory
    if not (source / "results.jsonl").exists():
        raise SystemExit(f"results.jsonl non trovato in {source}")
    if args.delay_seconds < 0:
        raise SystemExit("--delay-seconds deve essere >= 0")

    rows = load_rows(source)
    source_manifest = load_manifest(source)
    source_hash = str(source_manifest.get("dataset_sha256", ""))
    current_hash = sha256_file()
    if source_hash and source_hash != current_hash:
        raise SystemExit(
            "Il dataset locale non corrisponde all'hash del run sorgente. "
            "Usa la stessa versione del progetto che ha generato il run."
        )

    failed_systems = sorted({str(row["system"]) for row in rows if needs_recovery(row)})
    selected_systems = set(args.systems or failed_systems)
    targets = [row for row in rows if row["system"] in selected_systems and needs_recovery(row)]
    if not targets:
        raise SystemExit("Nessuna riga fallita da recuperare per i sistemi selezionati.")

    planned_calls = sum(calls_per_case(str(row["system"])) for row in targets)
    print(f"Run sorgente: {source}")
    print(f"Righe fallite selezionate: {len(targets)}")
    print(f"Chiamate previste per il recupero: {planned_calls}")
    by_system: dict[str, int] = {}
    for row in targets:
        by_system[str(row["system"])] = by_system.get(str(row["system"]), 0) + 1
    for system, count in sorted(by_system.items()):
        print(f"- {system}: {count} righe, {count * calls_per_case(system)} chiamate")
    if args.dry_run:
        return 0

    settings = Settings.from_env()
    if args.judge_provider:
        settings = replace(settings, judge_provider=args.judge_provider)
    real = set(args.real or [])
    if not args.mock and not args.allow_hybrid:
        for system in selected_systems:
            missing = required_providers(system, settings) - real
            if missing:
                raise SystemExit(
                    f"{system} avrebbe provider mock: {sorted(missing)}. "
                    "Aggiungi --real o usa --allow-hybrid soltanto per smoke test."
                )

    providers = build_providers(
        settings,
        mock=args.mock,
        real_providers=None if args.mock else args.real,
    )
    pricing = load_pricing(args.pricing)
    cases_by_id = {str(case["id"]): case for case in load_cases()}

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = args.output_root / f"{timestamp}-recovered"
    directory.mkdir(parents=True, exist_ok=False)

    manifest = dict(source_manifest)
    manifest.update({
        "created_at": timestamp,
        "recovered_from": str(source),
        "recovery_version": "v7.2",
        "recovery_systems": sorted(selected_systems),
        "recovery_rows_planned": len(targets),
        "recovery_calls_planned": planned_calls,
        "recovery_delay_seconds": args.delay_seconds,
        "real_providers": sorted(real),
        "mock_recovery": args.mock,
    })
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    target_keys = {(row["response_id"], row["system"]) for row in targets}
    recovered = 0
    blocked_by_rate_limit = False

    with (directory / "results.jsonl").open("w", encoding="utf-8") as handle:
        for index, original_row in enumerate(rows, start=1):
            key = (original_row.get("response_id"), original_row.get("system"))
            if key not in target_keys or blocked_by_rate_limit:
                handle.write(json.dumps(original_row, ensure_ascii=False) + "\n")
                continue

            case_id = str(original_row["case_id"])
            if case_id not in cases_by_id:
                raise SystemExit(f"Case ID non trovato nel dataset locale: {case_id}")
            original_case = cases_by_id[case_id]
            presentation_seed = int(original_row["presentation_seed"])
            if source_manifest.get("option_order") == "permuted":
                presented_case, option_map = permute_case_options(original_case, presentation_seed)
            else:
                presented_case = deepcopy(original_case)
                option_map = original_row.get("option_map_new_to_original", {})

            # Guard against silently reconstructing a different prompt.
            if presented_case["question"] != original_row.get("question"):
                raise SystemExit(f"Prompt mismatch per {case_id}: domanda diversa dal run sorgente.")
            if presented_case.get("options") != original_row.get("presented_options"):
                raise SystemExit(f"Prompt mismatch per {case_id}: opzioni diverse dal run sorgente.")

            system = str(original_row["system"])
            judge_seed = int(original_row["judge_seed"])
            print(f"[{recovered + 1}/{len(targets)}] recupero {case_id} :: {system}")
            objective_run = execute_system(system, settings, providers, presented_case, judge_seed)
            payload, parse_error = parse_answer(objective_run.text)
            scored = score_payload(payload, presented_case)
            canonical_answer = canonical_predicted_answer(
                scored.get("predicted_answer"), original_case["type"], option_map
            )
            meta = call_metadata(objective_run.calls)
            technical_failure = bool(meta["errors"] or meta["incomplete"])
            if meta["errors"]:
                failure_type = "provider_or_component_error"
            elif meta["incomplete"]:
                failure_type = "incomplete_generation"
            elif not scored["parse_success"]:
                failure_type = "parse_error"
            else:
                failure_type = None

            row = dict(original_row)
            row.update({
                "response_id": uuid4().hex,
                "raw_response": objective_run.text,
                "parsed_response": payload,
                "parse_error": parse_error,
                "technical_failure": technical_failure,
                "failure_type": failure_type,
                "evaluable": (not technical_failure) and bool(scored["parse_success"]),
                **scored,
                "canonical_predicted_answer": canonical_answer,
                **{k: v for k, v in meta.items() if k != "call_details"},
                "estimated_cost_usd": estimate_cost(objective_run.calls, pricing),
                "wall_time_seconds": objective_run.wall_time_seconds,
                "run_metadata": objective_run.metadata,
                "call_details": meta["call_details"],
                "recovered_from_response_id": original_row.get("response_id"),
                "recovery_timestamp": timestamp,
            })
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            recovered += 1

            if technical_failure and is_rate_limit_error(meta["call_details"]):
                print("Rate limit/quota ancora attivo: interrompo il recupero per non sprecare altre chiamate.")
                if not args.continue_on_rate_limit:
                    blocked_by_rate_limit = True
            if args.delay_seconds > 0 and not blocked_by_rate_limit:
                time.sleep(args.delay_seconds)

    summaries, _ = analyze(directory)
    manifest["recovery_rows_attempted"] = recovered
    manifest["recovery_stopped_by_rate_limit"] = blocked_by_rate_limit
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"\nRecupero salvato in: {directory}")
    for item in summaries:
        print(
            f"{item['system']}: status={item['status']}, coverage={item['coverage']:.1f}%, "
            f"valid_accuracy={item['valid_accuracy']}%, technical_failures={item['technical_failures']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
