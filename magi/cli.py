from __future__ import annotations

import argparse
import sys

from .config import Settings
from .orchestrator import MagiOrchestrator
from .providers import PROVIDER_NAMES, build_providers
from .types import LLMResult, MagiRun


def _print_call_metadata(result: LLMResult) -> None:
    token_text = ""
    if result.input_tokens is not None or result.output_tokens is not None:
        token_text = (
            f", token in/out: {result.input_tokens or 0}/{result.output_tokens or 0}"
        )
    print(
        f"({result.provider}/{result.model}, {result.latency_seconds:.3f} s"
        f"{token_text})"
    )
    if result.is_incomplete:
        reason = result.incomplete_reason or "motivo non riportato"
        print(f"ATTENZIONE: risposta incompleta ({reason}).")


def _print_scorecard(run: MagiRun) -> None:
    if run.scorecard is None:
        return
    print("\n=== SCORECARD INTERNA ===")
    if not run.scorecard.parsed:
        print("Scorecard non interpretabile.")
        if run.scorecard.parse_error:
            print(f"Errore: {run.scorecard.parse_error}")
        if run.scorecard.evaluator.text:
            print(run.scorecard.evaluator.text)
        _print_call_metadata(run.scorecard.evaluator)
        return

    print(
        f"Confidenza globale: {run.scorecard.global_confidence}% | "
        f"Consenso: {run.scorecard.consensus_level}%"
    )
    print(
        "Nota: sono stime interne del giudice, non accuratezza misurata "
        "contro una ground truth."
    )
    for score in run.scorecard.agents:
        print(
            f"\n[{score.agent}] rigore={score.technical_rigor} | "
            f"rilevanza={score.relevance} | incertezza={score.uncertainty_handling} | "
            f"praticità={score.practical_value} | peso={score.decision_weight}"
        )
        print(score.rationale)
    print(f"\nContributo più forte: {run.scorecard.strongest_contribution}")
    print(f"Correzione principale: {run.scorecard.main_correction}")
    print(f"Incertezza residua: {run.scorecard.residual_uncertainty}")
    _print_call_metadata(run.scorecard.evaluator)


def _print_summary(run: MagiRun) -> None:
    calls = run.all_calls()
    successful = [call for call in calls if not call.error]
    input_tokens = sum(call.input_tokens or 0 for call in successful)
    output_tokens = sum(call.output_tokens or 0 for call in successful)
    summed_latency = sum(call.latency_seconds for call in successful)
    incomplete = sum(1 for call in successful if call.is_incomplete)
    errors = sum(1 for call in calls if call.error)

    print("\n=== RIEPILOGO RUN ===")
    print(f"Chiamate: {len(calls)} | Errori: {errors} | Incomplete: {incomplete}")
    print(f"Token riportati in/out: {input_tokens}/{output_tokens}")
    print(
        "Latenza cumulativa delle chiamate: "
        f"{summed_latency:.3f} s (le chiamate parallele si sovrappongono)"
    )
    if run.wall_time_seconds is not None:
        print(f"Tempo reale del run: {run.wall_time_seconds:.3f} s")


def main() -> int:
    parser = argparse.ArgumentParser(description="MAGI multi-model orchestrator")
    parser.add_argument("question", help="Domanda da analizzare")
    parser.add_argument(
        "--critique",
        action="store_true",
        help="Aggiunge la critica reciproca: 7 chiamate invece di 4.",
    )
    parser.add_argument(
        "--auditor",
        action="store_true",
        help="Aggiunge un audit esterno prima del giudizio (+1 chiamata).",
    )
    parser.add_argument(
        "--blind",
        action="store_true",
        help="Anonimizza e randomizza i candidati davanti ad auditor e giudice.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Seed riproducibile per l'ordine cieco dei candidati.",
    )
    parser.add_argument(
        "--score",
        action="store_true",
        help="Aggiunge una scorecard interna: una chiamata ulteriore al giudice.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--mock",
        action="store_true",
        help="Usa tutti i provider simulati, senza API e costi.",
    )
    mode.add_argument(
        "--real",
        action="append",
        choices=PROVIDER_NAMES,
        metavar="PROVIDER",
        help=(
            "Rende reale il provider indicato; ripeti l'opzione per più provider. "
            "Esempio: --real openai --real gemini"
        ),
    )
    args = parser.parse_args()

    try:
        settings = Settings.from_env()
        providers = build_providers(
            settings,
            mock=args.mock,
            real_providers=args.real,
        )
        run, output_path = MagiOrchestrator(settings, providers).run(
            args.question,
            critique=args.critique,
            score=args.score,
            auditor=args.auditor,
            blind_judge=args.blind,
            random_seed=args.seed,
        )
    except Exception as exc:
        print(f"ERRORE: {exc}", file=sys.stderr)
        return 1

    print("\n=== RISPOSTE INIZIALI ===")
    for agent in run.agents:
        print(f"\n[{agent.agent} — {agent.role}]")
        print(f"ERRORE: {agent.initial.error}" if agent.initial.error else agent.initial.text)
        _print_call_metadata(agent.initial)

    if args.critique:
        print("\n=== CRITICHE ===")
        for agent in run.agents:
            print(f"\n[{agent.agent}]")
            if agent.critique is None:
                print("Nessuna critica.")
            elif agent.critique.error:
                print(f"ERRORE: {agent.critique.error}")
                _print_call_metadata(agent.critique)
            else:
                print(agent.critique.text)
                _print_call_metadata(agent.critique)


    if run.auditor is not None:
        print("\n=== AUDIT ESTERNO ===")
        if run.auditor.error:
            print(f"ERRORE: {run.auditor.error}")
        else:
            print(run.auditor.text)
        _print_call_metadata(run.auditor)

    print("\n=== VERDETTO MAGI ===")
    if run.verdict is None:
        print("Verdetto assente.")
    elif run.verdict.error:
        print(f"ERRORE: {run.verdict.error}")
        _print_call_metadata(run.verdict)
    else:
        print(run.verdict.text)
        _print_call_metadata(run.verdict)

    _print_scorecard(run)
    _print_summary(run)
    print(f"\nRun salvato in: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
