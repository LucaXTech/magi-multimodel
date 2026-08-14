from __future__ import annotations

import concurrent.futures
import json
import random
import statistics
import time
from dataclasses import dataclass
from typing import Any

from magi.config import Settings
from magi.providers import Provider
from magi.types import LLMResult

from .objective_scoring import format_case, parse_answer, response_schema

PERSONA_SYSTEMS = {
    "MELCHIOR": (
        "Sei MELCHIOR, analista tecnico. Risolvi il caso con rigore, controlla formule, "
        "unità, leakage e validità logica. Non seguire il consenso se è sbagliato."
    ),
    "BALTHASAR": (
        "Sei BALTHASAR, revisore scientifico e red team. Cerca assunzioni nascoste, "
        "confondenti, leakage e conclusioni non supportate. Poi scegli la risposta corretta."
    ),
    "CASPER": (
        "Sei CASPER, valutatore pragmatico. Scegli la soluzione operativa corretta e più "
        "semplice, senza sacrificare validità metodologica."
    ),
}

OBJECTIVE_SYSTEM = (
    "Sei un valutatore tecnico. Risolvi il caso in modo indipendente. Restituisci SOLO "
    "JSON valido nello schema richiesto. Non usare markdown e non aggiungere testo esterno."
)

JUDGE_SYSTEM = (
    "Sei un giudice cieco. I candidati sono anonimi e possono essere tutti sbagliati. "
    "Non votare per maggioranza, lunghezza o stile: risolvi il caso e usa i candidati solo "
    "come argomenti da verificare. Restituisci SOLO JSON valido nello schema richiesto."
)

AUDITOR_SYSTEM = (
    "Sei un auditor avversariale. Cerca un errore condiviso, un calcolo sbagliato o una "
    "assunzione non supportata nelle risposte anonime. Restituisci SOLO JSON valido."
)


@dataclass
class ObjectiveRun:
    text: str
    calls: list[LLMResult]
    wall_time_seconds: float
    metadata: dict[str, Any]


def _parallel(jobs: dict[str, tuple[Provider, str, str]]) -> dict[str, LLMResult]:
    results: dict[str, LLMResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(jobs))) as executor:
        futures = {
            executor.submit(provider.generate, system, prompt): name
            for name, (provider, system, prompt) in jobs.items()
        }
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                provider = jobs[name][0]
                results[name] = LLMResult(
                    provider=provider.name,
                    model=provider.model,
                    text="",
                    latency_seconds=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                    status="error",
                )
    return results


def case_prompt(case: dict[str, Any]) -> str:
    return (
        "BENCHMARK_OBJECTIVE_JSON_V1\n\n"
        + format_case(case)
        + "\n\nSCHEMA OBBLIGATORIO:\n"
        + response_schema(case)
        + "\nLa confidence esprime la probabilità che la tua risposta sia corretta, da 0 a 100."
    )


def run_baseline(provider: Provider, case: dict[str, Any]) -> ObjectiveRun:
    start = time.perf_counter()
    result = provider.generate(OBJECTIVE_SYSTEM, case_prompt(case))
    return ObjectiveRun(
        text=result.text,
        calls=[result],
        wall_time_seconds=round(time.perf_counter() - start, 3),
        metadata={},
    )


def _agent_jobs(
    providers: dict[str, Provider],
    case: dict[str, Any],
    same_provider: str | None = None,
) -> dict[str, tuple[Provider, str, str]]:
    mapping = {
        "MELCHIOR": same_provider or "openai",
        "BALTHASAR": same_provider or "anthropic",
        "CASPER": same_provider or "gemini",
    }
    prompt = case_prompt(case)
    return {
        name: (providers[provider_name], PERSONA_SYSTEMS[name] + " " + OBJECTIVE_SYSTEM, prompt)
        for name, provider_name in mapping.items()
    }


def _anonymous_candidates(
    results: dict[str, LLMResult], seed: int
) -> tuple[dict[str, str], dict[str, str]]:
    names = list(results)
    random.Random(seed).shuffle(names)
    labels = [f"CANDIDATE_{chr(65 + i)}" for i in range(len(names))]
    mapping = dict(zip(labels, names, strict=True))
    texts = {
        label: results[name].text if not results[name].error else f"ERRORE: {results[name].error}"
        for label, name in mapping.items()
    }
    return texts, mapping


def _judge_prompt(
    case: dict[str, Any], candidates: dict[str, str], audit: str | None = None
) -> str:
    rendered = "\n\n".join(f"### {label}\n{text}" for label, text in candidates.items())
    audit_text = f"\n\n### AUDIT AVVERSARIALE\n{audit}" if audit else ""
    return (
        "BENCHMARK_OBJECTIVE_JUDGE_JSON_V1\n\n"
        + format_case(case)
        + "\n\nRISPOSTE ANONIME:\n"
        + rendered
        + audit_text
        + "\n\nRisolvi indipendentemente il caso. SCHEMA OBBLIGATORIO:\n"
        + response_schema(case)
    )


def _audit_prompt(case: dict[str, Any], candidates: dict[str, str]) -> str:
    rendered = "\n\n".join(f"### {label}\n{text}" for label, text in candidates.items())
    return (
        "BENCHMARK_OBJECTIVE_AUDIT_JSON_V1\n\n"
        + format_case(case)
        + "\n\nRISPOSTE ANONIME:\n"
        + rendered
        + "\n\nRestituisci questo schema: "
        '{"shared_risk":"massimo 50 parole","recommended_answer":"A",'
        '"confidence":0,"reason":"massimo 60 parole"}'
    )


def run_magi(
    settings: Settings,
    providers: dict[str, Provider],
    case: dict[str, Any],
    seed: int,
    auditor: bool = False,
    same_provider: str | None = None,
) -> ObjectiveRun:
    start = time.perf_counter()
    agent_results = _parallel(_agent_jobs(providers, case, same_provider=same_provider))
    candidates, candidate_map = _anonymous_candidates(agent_results, seed)
    calls = list(agent_results.values())
    audit_text: str | None = None
    if auditor:
        audit_provider = providers[settings.auditor_provider]
        audit_result = audit_provider.generate(AUDITOR_SYSTEM, _audit_prompt(case, candidates))
        calls.append(audit_result)
        audit_text = audit_result.text if not audit_result.error else f"ERRORE: {audit_result.error}"
    judge = providers[settings.judge_provider]
    verdict = judge.generate(JUDGE_SYSTEM, _judge_prompt(case, candidates, audit_text))
    calls.append(verdict)
    return ObjectiveRun(
        text=verdict.text,
        calls=calls,
        wall_time_seconds=round(time.perf_counter() - start, 3),
        metadata={"candidate_map": candidate_map, "auditor": auditor, "same_provider": same_provider},
    )


def _answer_key(payload: dict[str, Any] | None, case: dict[str, Any]) -> str | float | tuple[str, ...] | None:
    if payload is None:
        return None
    answer = payload.get("answer")
    if case["type"] == "numeric":
        try:
            return float(answer)
        except (TypeError, ValueError):
            return None
    if case["type"] == "multi_select":
        if not isinstance(answer, list):
            return None
        return tuple(sorted(str(item).strip().upper() for item in answer))
    return str(answer).strip().upper()


def run_majority(providers: dict[str, Provider], case: dict[str, Any]) -> ObjectiveRun:
    start = time.perf_counter()
    results = _parallel(_agent_jobs(providers, case))
    calls = list(results.values())
    parsed = []
    for result in results.values():
        payload, _ = parse_answer(result.text)
        if payload is not None:
            parsed.append(payload)

    answer: Any = "NO_MAJORITY"
    confidence = 0
    rationale = "Nessuna maggioranza valida."
    if parsed:
        keys = [_answer_key(payload, case) for payload in parsed]
        valid_keys = [key for key in keys if key is not None]
        if case["type"] == "numeric" and valid_keys:
            answer = statistics.median(float(key) for key in valid_keys)
            confidence = int(round(sum(int(p.get("confidence", 50)) for p in parsed) / len(parsed)))
            rationale = "Mediana delle risposte numeriche dei tre agenti."
        elif valid_keys:
            counts: dict[Any, int] = {}
            for key in valid_keys:
                counts[key] = counts.get(key, 0) + 1
            best_key, best_count = max(counts.items(), key=lambda item: item[1])
            if best_count >= 2:
                answer = list(best_key) if isinstance(best_key, tuple) else best_key
                supporters = [p for p in parsed if _answer_key(p, case) == best_key]
                confidence = int(round(sum(int(p.get("confidence", 50)) for p in supporters) / len(supporters)))
                rationale = f"Maggioranza di {best_count} agenti su {len(parsed)}."
    text = json.dumps(
        {"answer": answer, "confidence": confidence, "rationale": rationale},
        ensure_ascii=False,
    )
    return ObjectiveRun(
        text=text,
        calls=calls,
        wall_time_seconds=round(time.perf_counter() - start, 3),
        metadata={"aggregation": "majority"},
    )
