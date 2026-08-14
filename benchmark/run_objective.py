from __future__ import annotations

import argparse
import json
import random
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from magi.config import Settings
from magi.providers import PROVIDER_NAMES, build_providers
from magi.types import LLMResult

from .analyze_objective import analyze
from .objective_engine import run_baseline, run_magi, run_majority
from .objective_scoring import parse_answer, score_payload
from .protocol import (
    PROTOCOL_VERSION,
    permute_case_options,
    select_cases,
    sha256_file,
    verify_lock,
)
from .validate_objective import validate

BASELINES = {"openai", "anthropic", "gemini", "groq"}
SYSTEMS = (
    "openai",
    "anthropic",
    "gemini",
    "groq",
    "majority_hetero",
    "magi_hetero",
    "magi_audit",
    "openai_triad",
)
DEFAULT_SYSTEMS = ["openai", "anthropic", "gemini", "groq"]


def calls_per_case(system: str) -> int:
    return {
        "openai": 1,
        "anthropic": 1,
        "gemini": 1,
        "groq": 1,
        "majority_hetero": 3,
        "magi_hetero": 4,
        "magi_audit": 5,
        "openai_triad": 4,
    }[system]


def required_providers(system: str, settings: Settings) -> set[str]:
    if system in BASELINES:
        return {system}
    if system == "majority_hetero":
        return {"openai", "anthropic", "gemini"}
    if system == "openai_triad":
        return {"openai", settings.judge_provider}
    required = {"openai", "anthropic", "gemini", settings.judge_provider}
    if system == "magi_audit":
        required.add(settings.auditor_provider)
    return required


def call_metadata(calls: list[LLMResult]) -> dict[str, Any]:
    good = [call for call in calls if not call.error]
    complete = bool(good) and all(
        call.input_tokens is not None and call.output_tokens is not None
        for call in good
    )
    input_tokens = sum(call.input_tokens or 0 for call in good)
    output_tokens = sum(call.output_tokens or 0 for call in good)
    return {
        "calls": len(calls),
        "errors": sum(bool(call.error) for call in calls),
        "incomplete": sum(call.is_incomplete for call in good),
        "input_tokens": input_tokens if complete else None,
        "output_tokens": output_tokens if complete else None,
        "total_tokens": input_tokens + output_tokens if complete else None,
        "summed_call_latency_seconds": round(sum(call.latency_seconds for call in good), 3),
        "call_details": [call.to_dict() for call in calls],
    }


def load_pricing(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): value for key, value in payload.items() if isinstance(value, dict)}


def estimate_cost(calls: list[LLMResult], pricing: dict[str, dict[str, float]]) -> float | None:
    total = 0.0
    for call in calls:
        rate = pricing.get(call.provider)
        if not rate or call.input_tokens is None or call.output_tokens is None:
            return None
        total += call.input_tokens / 1_000_000 * float(rate["input_per_million"])
        total += call.output_tokens / 1_000_000 * float(rate["output_per_million"])
    return round(total, 8)


def canonical_predicted_answer(
    predicted: Any,
    case_type: str,
    option_map: dict[str, str],
) -> Any:
    if case_type == "numeric" or not option_map:
        return predicted
    if case_type == "multi_select":
        if not isinstance(predicted, list):
            return predicted
        return sorted(option_map.get(str(item), str(item)) for item in predicted)
    return option_map.get(str(predicted), predicted)



def execute_system(
    system: str,
    settings: Settings,
    providers: dict[str, Any],
    presented_case: dict[str, Any],
    judge_seed: int,
):
    """Execute one prespecified benchmark system on one presented case."""
    if system in BASELINES:
        return run_baseline(providers[system], presented_case)
    if system == "majority_hetero":
        return run_majority(providers, presented_case)
    if system == "magi_hetero":
        return run_magi(settings, providers, presented_case, judge_seed, auditor=False)
    if system == "magi_audit":
        return run_magi(settings, providers, presented_case, judge_seed, auditor=True)
    if system == "openai_triad":
        return run_magi(
            settings,
            providers,
            presented_case,
            judge_seed,
            auditor=False,
            same_provider="openai",
        )
    raise RuntimeError(system)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MAGI Objective Benchmark v3")
    parser.add_argument("--systems", nargs="+", choices=SYSTEMS, default=DEFAULT_SYSTEMS)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true")
    mode.add_argument("--real", action="append", choices=PROVIDER_NAMES, metavar="PROVIDER")
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--case", action="append", dest="case_ids")
    parser.add_argument("--category", action="append")
    parser.add_argument("--difficulty", action="append", choices=("intermediate", "hard"))
    parser.add_argument("--selection", choices=("stratified", "ordered"), default="stratified")
    parser.add_argument("--option-order", choices=("permuted", "fixed"), default="permuted")
    parser.add_argument("--system-order", choices=("rotated", "fixed"), default="rotated")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--judge-provider", choices=PROVIDER_NAMES, default=None)
    parser.add_argument("--reference-system", choices=SYSTEMS, default=None)
    parser.add_argument("--pricing", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, default=Path("objective_results_v3"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-hybrid", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    errors = validate()
    if errors:
        raise SystemExit("Dataset oggettivo non valido:\n" + "\n".join(errors))
    if args.limit < 1 or args.repeats < 1:
        raise SystemExit("--limit e --repeats devono essere >= 1")

    lock_ok, lock_message = verify_lock()
    if args.split == "test" and not lock_ok:
        raise SystemExit("Test set bloccato: " + lock_message)
    if args.split == "test" and args.reference_system is None:
        raise SystemExit(
            "Sul test set devi prespecificare --reference-system usando la baseline scelta sul development set."
        )
    if args.reference_system and args.reference_system not in args.systems:
        raise SystemExit("--reference-system deve essere incluso in --systems")

    settings = Settings.from_env()
    if args.judge_provider:
        settings = replace(settings, judge_provider=args.judge_provider)

    try:
        cases = select_cases(
            split=args.split,
            limit=args.limit,
            seed=args.seed,
            categories=set(args.category or []),
            difficulties=set(args.difficulty or []),
            case_ids=set(args.case_ids or []),
            selection=args.selection,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if not cases:
        raise SystemExit("Nessun caso selezionato.")

    real = set(args.real or [])
    planned = sum(calls_per_case(system) for system in args.systems) * len(cases) * args.repeats
    print(f"Protocollo: {PROTOCOL_VERSION} | Split: {args.split} | Hash: {sha256_file()[:12]}")
    print(
        f"Casi: {len(cases)} | Sistemi: {len(args.systems)} | Ripetizioni/permutazioni: {args.repeats}"
    )
    print(
        f"Selezione: {args.selection} | Ordine opzioni: {args.option_order} | "
        f"Ordine sistemi: {args.system_order} | Seed: {args.seed}"
    )
    print(f"Chiamate previste: {planned}")
    for system in args.systems:
        print(f"- {system}: {calls_per_case(system)} chiamate/caso")
    print("Casi selezionati:", ", ".join(case["id"] for case in cases))
    if args.dry_run:
        return 0

    if not args.mock and not args.allow_hybrid:
        for system in args.systems:
            missing = required_providers(system, settings) - real
            if missing:
                raise SystemExit(
                    f"{system} avrebbe provider mock: {sorted(missing)}. "
                    "Aggiungi --real o usa --allow-hybrid soltanto per smoke test tecnici."
                )

    providers = build_providers(
        settings,
        mock=args.mock,
        real_providers=None if (not args.mock and args.real is None) else args.real,
    )
    pricing = load_pricing(args.pricing)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    directory = args.output_root / timestamp
    directory.mkdir(parents=True, exist_ok=False)

    manifest = {
        "benchmark": PROTOCOL_VERSION,
        "created_at": timestamp,
        "dataset_sha256": sha256_file(),
        "protocol_lock_valid": lock_ok,
        "protocol_lock_message": lock_message,
        "split": args.split,
        "selection": args.selection,
        "option_order": args.option_order,
        "system_order": args.system_order,
        "systems": args.systems,
        "reference_system": args.reference_system,
        "case_ids": [case["id"] for case in cases],
        "repeats": args.repeats,
        "seed": args.seed,
        "judge_provider": settings.judge_provider,
        "auditor_provider": settings.auditor_provider,
        "models": {
            "openai": settings.openai_model,
            "anthropic": settings.anthropic_model,
            "gemini": settings.gemini_model,
            "groq": settings.groq_model,
        },
        "generation_settings": {
            "max_output_tokens": settings.max_output_tokens,
            "openai_reasoning_effort": settings.openai_reasoning_effort,
            "openai_verbosity": settings.openai_verbosity,
            "anthropic_thinking": settings.anthropic_thinking,
            "temperature": "provider default; not explicitly set",
        },
        "mock": args.mock,
        "real_providers": sorted(real),
        "planned_calls": planned,
        "primary_endpoint": "exact_accuracy_on_evaluable_rows",
        "reporting_version": "reliability_v7.2",
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    total_runs = len(cases) * len(args.systems) * args.repeats
    counter = 0
    for repeat in range(args.repeats):
        for case_index, original_case in enumerate(cases):
            presentation_seed = args.seed + repeat * 100_000 + case_index * 1_000
            if args.option_order == "permuted":
                presented_case, option_map = permute_case_options(original_case, presentation_seed)
            else:
                presented_case, option_map = deepcopy(original_case), {
                    label: label for label in ("A", "B", "C", "D")
                } if original_case["type"] != "numeric" else {}

            case_systems = list(args.systems)
            if args.system_order == "rotated":
                random.Random(presentation_seed + 777).shuffle(case_systems)
            for system_index, system in enumerate(case_systems):
                counter += 1
                judge_seed = presentation_seed + system_index + 1
                print(f"[{counter}/{total_runs}] {original_case['id']} :: {system}")
                objective_run = execute_system(
                    system,
                    settings,
                    providers,
                    presented_case,
                    judge_seed,
                )

                payload, parse_error = parse_answer(objective_run.text)
                scored = score_payload(payload, presented_case)
                canonical_answer = canonical_predicted_answer(
                    scored.get("predicted_answer"),
                    original_case["type"],
                    option_map,
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
                row = {
                    "response_id": uuid4().hex,
                    "protocol_version": PROTOCOL_VERSION,
                    "dataset_sha256": manifest["dataset_sha256"],
                    "case_id": original_case["id"],
                    "split": original_case["split"],
                    "category": original_case["category"],
                    "skill": original_case["skill"],
                    "difficulty": original_case["difficulty"],
                    "critical": original_case["critical"],
                    "case_type": original_case["type"],
                    "question": presented_case["question"],
                    "presented_options": presented_case.get("options"),
                    "option_map_new_to_original": option_map,
                    "original_expected_answer": original_case["answer"],
                    "presented_expected_answer": presented_case["answer"],
                    "explanation": original_case["explanation"],
                    "system": system,
                    "repeat": repeat,
                    "presentation_seed": presentation_seed,
                    "judge_seed": judge_seed,
                    "raw_response": objective_run.text,
                    "parsed_response": payload,
                    "parse_error": parse_error,
                    "technical_failure": technical_failure,
                    "failure_type": failure_type,
                    "evaluable": (not technical_failure) and bool(scored["parse_success"]),
                    **scored,
                    "canonical_predicted_answer": canonical_answer,
                    **{key: value for key, value in meta.items() if key != "call_details"},
                    "estimated_cost_usd": estimate_cost(objective_run.calls, pricing),
                    "wall_time_seconds": objective_run.wall_time_seconds,
                    "run_metadata": objective_run.metadata,
                    "call_details": meta["call_details"],
                }
                with (directory / "results.jsonl").open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summaries, _ = analyze(directory)
    print(f"\nRisultati: {directory}")
    if args.mock:
        print("SMOKE TEST MOCK: usa soltanto parsing, logging e file generati; i punteggi non misurano i modelli.")
    else:
        for item in summaries:
            if item["status"] != "COMPLETE":
                print(
                    f"{item['system']}: INCOMPLETE — coverage={item['coverage']:.1f}% "
                    f"({item['evaluable_n']}/{item['planned_n']}), "
                    f"technical_failures={item['technical_failures']}, "
                    f"valid_accuracy={item['valid_accuracy']}%"
                )
            else:
                print(
                    f"{item['system']}: valid_accuracy={item['valid_accuracy']:.1f}%, "
                    f"score={item['mean_score']:.1f}, critical_error={item['critical_error_rate']}%, "
                    f"brier={item['mean_brier']}"
                )
    print("Apri report.md. Nessuna revisione manuale obbligatoria.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
