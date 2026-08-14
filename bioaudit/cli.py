from __future__ import annotations

import argparse
from pathlib import Path

from magi.config import Settings
from magi.providers import PROVIDER_NAMES, build_providers

from .orchestrator import BioAuditOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description="BioAudit: audit multi-modello di metodi biomedicali e ML")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--file", type=Path)
    source.add_argument("--text")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--mock", action="store_true")
    mode.add_argument("--real", action="append", choices=PROVIDER_NAMES)
    parser.add_argument("--profile", choices=["eeg_ml", "biomedical", "general_ml"], default="eeg_ml")
    parser.add_argument("--auditor", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--blind", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--output-root", type=Path, default=Path("bioaudit_results"))
    parser.add_argument("--allow-hybrid", action="store_true")
    args = parser.parse_args()

    if args.file:
        text = args.file.read_text(encoding="utf-8")
        source_name = args.file.name
    else:
        text = args.text
        source_name = "direct_text"

    settings = Settings.from_env()
    real = set(args.real or [])
    required = {"openai", "anthropic", "gemini", settings.judge_provider}
    if args.auditor:
        required.add(settings.auditor_provider)
    if not args.mock and not args.allow_hybrid:
        missing = required - real
        if missing:
            raise SystemExit(f"Provider mancanti per un audit reale: {sorted(missing)}")
    providers = build_providers(
        settings,
        mock=args.mock,
        real_providers=None if (not args.mock and args.real is None) else args.real,
    )
    result, directory = BioAuditOrchestrator(settings, providers).run(
        text=text,
        profile=args.profile,
        auditor=args.auditor,
        blind=args.blind,
        seed=args.seed,
        output_root=args.output_root,
        source_name=source_name,
    )
    report = result["report"]
    print(f"\nBIOAUDIT: {report['verdict']} | confidenza interna {report['internal_confidence']}%")
    print(report["summary"])
    print(f"Problemi critici: {len(report['critical_issues'])} | moderati: {len(report['moderate_issues'])}")
    print(f"Report: {directory / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
