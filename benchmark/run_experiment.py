from __future__ import annotations

import argparse
import csv
import json
import random
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from magi.config import Settings
from magi.orchestrator import MagiOrchestrator
from magi.providers import PROVIDER_NAMES, Provider, build_providers
from magi.types import LLMResult

from .analyze_results import analyze_directory
from .scoring import score_response

CASES_PATH = Path(__file__).with_name("cases_v1.jsonl")
BASELINES = {"openai", "anthropic", "gemini", "groq"}
MAGI_SYSTEMS = {"magi_fast", "magi_audit", "magi_debate"}
ALL_SYSTEMS = tuple(sorted(BASELINES | MAGI_SYSTEMS))

BASELINE_SYSTEM = (
    "Sei un consulente tecnico indipendente. Rispondi correttamente e direttamente. "
    "Distingui fatti, assunzioni e ciò che non può essere concluso. Evita soglie o "
    "regole universali non supportate. Massimo 320 parole."
)


def load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def required_providers(system: str, settings: Settings) -> set[str]:
    if system in BASELINES:
        return {system}
    required = {"openai", "anthropic", "gemini", settings.judge_provider}
    if system in {"magi_audit", "magi_debate"}:
        required.add(settings.auditor_provider)
    return required


def calls_per_case(system: str) -> int:
    return {"openai":1,"anthropic":1,"gemini":1,"groq":1,"magi_fast":4,"magi_audit":5,"magi_debate":8}[system]


def call_metadata(calls: list[LLMResult]) -> dict[str, Any]:
    good = [c for c in calls if not c.error]
    input_tokens = sum(c.input_tokens or 0 for c in good)
    output_tokens = sum(c.output_tokens or 0 for c in good)
    token_complete = all(c.input_tokens is not None and c.output_tokens is not None for c in good)
    return {
        "calls": len(calls),
        "errors": sum(bool(c.error) for c in calls),
        "incomplete": sum(c.is_incomplete for c in good),
        "input_tokens": input_tokens if token_complete else None,
        "output_tokens": output_tokens if token_complete else None,
        "total_tokens": input_tokens + output_tokens if token_complete else None,
        "summed_call_latency_seconds": round(sum(c.latency_seconds for c in good), 3),
        "call_details": [c.to_dict() for c in calls],
    }


def load_pricing(path: Path | None) -> dict[str, dict[str, float]]:
    if path is None:
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): v for k, v in payload.items() if isinstance(v, dict)}


def estimate_cost(calls: list[LLMResult], pricing: dict[str, dict[str, float]]) -> float | None:
    total = 0.0
    for call in calls:
        rate = pricing.get(call.provider)
        if not rate or call.input_tokens is None or call.output_tokens is None:
            return None
        total += call.input_tokens / 1_000_000 * float(rate["input_per_million"])
        total += call.output_tokens / 1_000_000 * float(rate["output_per_million"])
    return round(total, 8)


def run_baseline(provider: Provider, question: str) -> tuple[str, list[LLMResult], float, str | None]:
    started = time.perf_counter()
    result = provider.generate(BASELINE_SYSTEM, question)
    return result.text, [result], round(time.perf_counter() - started, 3), result.error


def create_review_files(directory: Path, rows: list[dict[str, Any]], seed: int) -> None:
    rng = random.Random(seed)
    blinded = []
    key = []
    for row in rows:
        review_id = "R-" + uuid4().hex[:10]
        blinded.append({
            "review_id": review_id,
            "case_id": row["case_id"],
            "question": row["question"],
            "response": row["response"],
            "correctness_0_4": "",
            "critical_error_0_1": "",
            "completeness_0_3": "",
            "uncertainty_0_2": "",
            "reviewer_notes": "",
        })
        key.append({"review_id": review_id, "system": row["system"], "repeat": row["repeat"], "response_id": row["response_id"]})
    rng.shuffle(blinded)
    with (directory / "human_review_blinded.csv").open("w", encoding="utf-8", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=list(blinded[0]) if blinded else ["review_id"]); writer.writeheader(); writer.writerows(blinded)
    with (directory / "BLINDING_KEY_DO_NOT_OPEN.csv").open("w", encoding="utf-8", newline="") as f:
        writer=csv.DictWriter(f, fieldnames=list(key[0]) if key else ["review_id"]); writer.writeheader(); writer.writerows(key)


def main() -> int:
    parser = argparse.ArgumentParser(description="MAGI scientific benchmark v1")
    parser.add_argument("--systems", nargs="+", choices=ALL_SYSTEMS, default=["openai","anthropic","gemini","groq","magi_fast","magi_audit"])
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true")
    mode.add_argument("--real", action="append", choices=PROVIDER_NAMES, metavar="PROVIDER")
    parser.add_argument("--limit", type=int, default=3, help="Numero massimo di casi; default prudente: 3")
    parser.add_argument("--case", action="append", dest="case_ids", help="Seleziona uno o più case ID")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--judge-provider", choices=PROVIDER_NAMES, default=None)
    parser.add_argument("--pricing", type=Path, default=None, help="JSON locale con prezzi per milione di token")
    parser.add_argument("--output-root", type=Path, default=Path("benchmark_results"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-hybrid", action="store_true", help="Consente provider mock dentro sistemi MAGI; non usare per risultati scientifici")
    args=parser.parse_args()

    if args.limit < 1 or args.repeats < 1:
        raise SystemExit("--limit e --repeats devono essere >= 1")
    settings=Settings.from_env()
    if args.judge_provider:
        settings=replace(settings, judge_provider=args.judge_provider)
    cases=load_cases()
    if args.case_ids:
        wanted=set(args.case_ids); cases=[c for c in cases if c["id"] in wanted]
        missing=wanted-{c["id"] for c in cases}
        if missing: raise SystemExit("Case ID non trovati: "+", ".join(sorted(missing)))
    cases=cases[:args.limit]
    real=set(args.real or [])

    total_calls=sum(calls_per_case(s) for s in args.systems)*len(cases)*args.repeats
    print(f"Casi: {len(cases)} | Sistemi: {len(args.systems)} | Ripetizioni: {args.repeats}")
    print(f"Chiamate previste: {total_calls}")
    if args.dry_run:
        for s in args.systems: print(f"- {s}: {calls_per_case(s)} chiamate/caso; provider richiesti={sorted(required_providers(s, settings))}")
        return 0

    if not args.mock and not args.allow_hybrid:
        for system in args.systems:
            missing=required_providers(system, settings)-real
            if missing:
                raise SystemExit(f"{system} avrebbe provider mock: {sorted(missing)}. Aggiungi --real per ciascuno o usa --allow-hybrid solo per test tecnici.")

    providers=build_providers(settings, mock=args.mock, real_providers=None if (not args.mock and args.real is None) else args.real)
    pricing=load_pricing(args.pricing)
    timestamp=datetime.now().strftime("%Y%m%d-%H%M%S")
    directory=args.output_root/timestamp; directory.mkdir(parents=True,exist_ok=False)
    manifest={"created_at":timestamp,"systems":args.systems,"case_ids":[c["id"] for c in cases],"repeats":args.repeats,"seed":args.seed,"judge_provider":settings.judge_provider,"auditor_provider":settings.auditor_provider,"mock":args.mock,"real_providers":sorted(real),"planned_calls":total_calls}
    (directory/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")

    rows=[]
    for repeat in range(args.repeats):
        for case_index, case in enumerate(cases):
            for system_index, system in enumerate(args.systems):
                run_seed=args.seed + repeat*100000 + case_index*100 + system_index
                print(f"[{len(rows)+1}/{len(cases)*len(args.systems)*args.repeats}] {case['id']} :: {system}")
                if system in BASELINES:
                    text,calls,wall,error=run_baseline(providers[system],case["question"])
                    run_path=None
                else:
                    critique=system=="magi_debate"; auditor=system in {"magi_audit","magi_debate"}
                    run,run_path=MagiOrchestrator(settings,providers).run(case["question"],critique=critique,auditor=auditor,score=False,blind_judge=True,random_seed=run_seed)
                    text=run.verdict.text if run.verdict and not run.verdict.error else ""
                    calls=run.all_calls(); wall=run.wall_time_seconds or 0.0; error=run.verdict.error if run.verdict else "verdetto assente"
                rubric=score_response(text,case)
                meta=call_metadata(calls)
                row={
                    "response_id":uuid4().hex,
                    "case_id":case["id"],"category":case["category"],"difficulty":case["difficulty"],"question":case["question"],
                    "system":system,"repeat":repeat,"seed":run_seed,"response":text,"reference_answer":case["reference_answer"],
                    **rubric,**{k:v for k,v in meta.items() if k!="call_details"},
                    "estimated_cost_usd":estimate_cost(calls,pricing),"wall_time_seconds":wall,"error":error,"run_path":run_path,
                    "call_details":meta["call_details"],
                }
                rows.append(row)
                with (directory/"results.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(row,ensure_ascii=False)+"\n")

    create_review_files(directory,rows,args.seed)
    summaries,comparisons=analyze_directory(directory)
    print(f"\nRisultati: {directory}")
    for s in summaries: print(f"{s['system']}: score={s['mean_score']:.2f}, correct={100*s['correct_rate']:.1f}%, critical={100*s['critical_error_rate']:.1f}%")
    print("Apri report.md; per la revisione umana usa human_review_blinded.csv senza aprire la chiave.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
