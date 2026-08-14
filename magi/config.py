from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None
    anthropic_api_key: str | None
    gemini_api_key: str | None
    groq_api_key: str | None
    openai_model: str
    anthropic_model: str
    gemini_model: str
    groq_model: str
    auditor_provider: str
    anthropic_thinking: str
    judge_provider: str
    max_output_tokens: int
    agent_word_limit: int
    judge_word_limit: int
    openai_reasoning_effort: str
    openai_verbosity: str
    runs_dir: Path

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()

        def clean(name: str) -> str | None:
            value = os.getenv(name, "").strip()
            return value or None

        def read_int(name: str, default: int, minimum: int) -> int:
            try:
                value = int(os.getenv(name, str(default)))
            except ValueError as exc:
                raise ValueError(f"{name} deve essere un intero.") from exc
            if value < minimum:
                raise ValueError(f"{name} deve essere almeno {minimum}.")
            return value

        judge = os.getenv("JUDGE_PROVIDER", "openai").strip().lower()
        valid_providers = {"openai", "anthropic", "gemini", "groq"}
        if judge not in valid_providers:
            raise ValueError("JUDGE_PROVIDER deve essere openai, anthropic, gemini o groq.")

        auditor_provider = os.getenv("AUDITOR_PROVIDER", "groq").strip().lower()
        if auditor_provider not in valid_providers:
            raise ValueError("AUDITOR_PROVIDER deve essere openai, anthropic, gemini o groq.")

        anthropic_thinking = os.getenv("ANTHROPIC_THINKING", "disabled").strip().lower()
        if anthropic_thinking not in {"disabled", "adaptive"}:
            raise ValueError("ANTHROPIC_THINKING deve essere disabled o adaptive.")

        reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT", "low").strip().lower()
        if reasoning_effort not in {"none", "minimal", "low", "medium", "high", "xhigh"}:
            raise ValueError(
                "OPENAI_REASONING_EFFORT deve essere none, minimal, low, medium, high o xhigh."
            )

        verbosity = os.getenv("OPENAI_VERBOSITY", "low").strip().lower()
        if verbosity not in {"low", "medium", "high"}:
            raise ValueError("OPENAI_VERBOSITY deve essere low, medium o high.")

        return cls(
            openai_api_key=clean("OPENAI_API_KEY"),
            anthropic_api_key=clean("ANTHROPIC_API_KEY"),
            gemini_api_key=clean("GEMINI_API_KEY"),
            groq_api_key=clean("GROQ_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5-mini").strip(),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip(),
            groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip(),
            judge_provider=judge,
            auditor_provider=auditor_provider,
            anthropic_thinking=anthropic_thinking,
            max_output_tokens=read_int("MAX_OUTPUT_TOKENS", 2500, 256),
            agent_word_limit=read_int("AGENT_WORD_LIMIT", 320, 80),
            judge_word_limit=read_int("JUDGE_WORD_LIMIT", 450, 120),
            openai_reasoning_effort=reasoning_effort,
            openai_verbosity=verbosity,
            runs_dir=Path(os.getenv("RUNS_DIR", "runs")),
        )
