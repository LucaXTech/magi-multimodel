from __future__ import annotations

import concurrent.futures
import json
import re
import time
import random
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .config import Settings
from .prompts import (
    AUDITOR_SYSTEM,
    JUDGE_SYSTEM,
    PERSONAS,
    build_auditor_prompt,
    build_critique_prompt,
    build_initial_prompt,
    build_judge_prompt,
    build_score_prompt,
)
from .providers import Provider
from .storage import save_run
from .types import AgentResult, AgentScore, LLMResult, MagiRun, Scorecard


AGENT_PROVIDER = {
    "MELCHIOR": "openai",
    "BALTHASAR": "anthropic",
    "CASPER": "gemini",
}

EventCallback = Callable[[str, dict[str, Any]], None]


#       /\_/\
#      ( o.o )  Listen to every answer; trust only the evidence.
#       > ^ <
class MagiOrchestrator:
    def __init__(self, settings: Settings, providers: dict[str, Provider]) -> None:
        self.settings = settings
        self.providers = providers

    @staticmethod
    def _emit(callback: EventCallback | None, event: str, **payload: Any) -> None:
        if callback is None:
            return
        try:
            callback(event, payload)
        except Exception:
            # La telemetria dell'interfaccia non deve interrompere il run.
            pass

    @staticmethod
    def _parallel_call(
        jobs: dict[str, tuple[Provider, str, str]]
    ) -> dict[str, LLMResult]:
        results: dict[str, LLMResult] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as executor:
            future_to_name = {
                executor.submit(provider.generate, system, prompt): name
                for name, (provider, system, prompt) in jobs.items()
            }
            for future in concurrent.futures.as_completed(future_to_name):
                name = future_to_name[future]
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

    @staticmethod
    def _clean_json_text(text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return cleaned[start : end + 1]
        return cleaned

    @classmethod
    def _parse_scorecard(cls, evaluator: LLMResult) -> Scorecard:
        if evaluator.error:
            return Scorecard(
                evaluator=evaluator,
                parsed=False,
                parse_error=evaluator.error,
            )
        try:
            payload = json.loads(cls._clean_json_text(evaluator.text))
            agents: list[AgentScore] = []
            expected = {"MELCHIOR", "BALTHASAR", "CASPER"}
            seen: set[str] = set()
            for item in payload.get("agents", []):
                name = str(item.get("agent", "")).upper()
                if name not in expected or name in seen:
                    continue
                seen.add(name)

                def score(field: str) -> int:
                    value = int(round(float(item.get(field, 0))))
                    return max(0, min(100, value))

                agents.append(
                    AgentScore(
                        agent=name,
                        technical_rigor=score("technical_rigor"),
                        relevance=score("relevance"),
                        uncertainty_handling=score("uncertainty_handling"),
                        practical_value=score("practical_value"),
                        decision_weight=score("decision_weight"),
                        rationale=str(item.get("rationale", "")).strip(),
                    )
                )
            if seen != expected:
                raise ValueError("La scorecard non contiene tutti e tre gli agenti.")

            def top_score(field: str) -> int:
                value = int(round(float(payload.get(field, 0))))
                return max(0, min(100, value))

            return Scorecard(
                evaluator=evaluator,
                parsed=True,
                global_confidence=top_score("global_confidence"),
                consensus_level=top_score("consensus_level"),
                agents=sorted(
                    agents,
                    key=lambda agent: ("MELCHIOR", "BALTHASAR", "CASPER").index(
                        agent.agent
                    ),
                ),
                strongest_contribution=str(
                    payload.get("strongest_contribution", "")
                ).strip(),
                main_correction=str(payload.get("main_correction", "")).strip(),
                residual_uncertainty=str(
                    payload.get("residual_uncertainty", "")
                ).strip(),
            )
        except Exception as exc:
            return Scorecard(
                evaluator=evaluator,
                parsed=False,
                parse_error=f"{type(exc).__name__}: {exc}",
            )

    def run(
        self,
        question: str,
        critique: bool = False,
        score: bool = False,
        auditor: bool = False,
        blind_judge: bool = False,
        random_seed: int | None = None,
        on_event: EventCallback | None = None,
    ) -> tuple[MagiRun, str]:
        question = question.strip()
        if not question:
            raise ValueError("La domanda non può essere vuota.")

        started = time.perf_counter()
        run = MagiRun(
            run_id=datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8],
            created_at=datetime.now(timezone.utc).isoformat(),
            question=question,
            critique_enabled=critique,
            scoring_enabled=score,
            auditor_enabled=auditor,
            blind_judge_enabled=blind_judge,
            random_seed=random_seed,
        )

        self._emit(on_event, "initial_started", agents=list(AGENT_PROVIDER))
        initial_jobs = {
            agent: (
                self.providers[provider_name],
                PERSONAS[agent]["system"],
                build_initial_prompt(question, agent, self.settings.agent_word_limit),
            )
            for agent, provider_name in AGENT_PROVIDER.items()
        }
        initial_results = self._parallel_call(initial_jobs)
        initial_texts = {
            agent: result.text if not result.error else f"ERRORE: {result.error}"
            for agent, result in initial_results.items()
        }
        self._emit(
            on_event,
            "initial_completed",
            agents={
                name: {
                    "provider": result.provider,
                    "model": result.model,
                    "error": result.error,
                }
                for name, result in initial_results.items()
            },
        )

        critique_results: dict[str, LLMResult] = {}
        if critique:
            self._emit(on_event, "critique_started", agents=list(AGENT_PROVIDER))
            critique_jobs = {
                agent: (
                    self.providers[provider_name],
                    PERSONAS[agent]["system"],
                    build_critique_prompt(
                        question,
                        agent,
                        initial_texts,
                        self.settings.agent_word_limit,
                    ),
                )
                for agent, provider_name in AGENT_PROVIDER.items()
            }
            critique_results = self._parallel_call(critique_jobs)
            self._emit(on_event, "critique_completed", agents=list(AGENT_PROVIDER))

        for agent in PERSONAS:
            run.agents.append(
                AgentResult(
                    agent=agent,
                    role=PERSONAS[agent]["role"],
                    initial=initial_results[agent],
                    critique=critique_results.get(agent),
                )
            )

        critique_texts = None
        if critique:
            critique_texts = {
                agent: result.text if not result.error else f"ERRORE: {result.error}"
                for agent, result in critique_results.items()
            }

        judge_initial_texts = initial_texts
        judge_critique_texts = critique_texts
        if blind_judge:
            names = list(initial_texts)
            rng = random.Random(random_seed)
            rng.shuffle(names)
            labels = [f"CANDIDATE_{chr(65 + i)}" for i in range(len(names))]
            run.candidate_map = dict(zip(labels, names, strict=True))
            judge_initial_texts = {
                label: initial_texts[agent]
                for label, agent in run.candidate_map.items()
            }
            if critique_texts:
                judge_critique_texts = {
                    label: critique_texts[agent]
                    for label, agent in run.candidate_map.items()
                }

        if auditor:
            audit_provider = self.providers[self.settings.auditor_provider]
            audit_prompt = build_auditor_prompt(
                question,
                judge_initial_texts,
                judge_critique_texts,
                self.settings.agent_word_limit,
            )
            self._emit(
                on_event,
                "auditor_started",
                provider=audit_provider.name,
                model=audit_provider.model,
            )
            run.auditor = audit_provider.generate(AUDITOR_SYSTEM, audit_prompt)
            self._emit(
                on_event,
                "auditor_completed",
                error=run.auditor.error,
                incomplete=run.auditor.is_incomplete,
            )

        judge = self.providers[self.settings.judge_provider]
        judge_prompt = build_judge_prompt(
            question,
            judge_initial_texts,
            judge_critique_texts,
            self.settings.judge_word_limit,
            external_audit=(run.auditor.text if run.auditor and not run.auditor.error else None),
        )
        self._emit(
            on_event,
            "judge_started",
            provider=judge.name,
            model=judge.model,
        )
        run.verdict = judge.generate(JUDGE_SYSTEM, judge_prompt)
        self._emit(
            on_event,
            "judge_completed",
            error=run.verdict.error,
            incomplete=run.verdict.is_incomplete,
        )

        if score:
            score_prompt = build_score_prompt(
                question,
                initial_texts,
                critique_texts,
                run.verdict.text if not run.verdict.error else "",
            )
            self._emit(on_event, "score_started", provider=judge.name, model=judge.model)
            evaluator = judge.generate(
                "Sei un valutatore metodologico. Restituisci soltanto JSON valido.",
                score_prompt,
            )
            run.scorecard = self._parse_scorecard(evaluator)
            self._emit(
                on_event,
                "score_completed",
                parsed=run.scorecard.parsed,
                parse_error=run.scorecard.parse_error,
            )

        run.wall_time_seconds = round(time.perf_counter() - started, 3)
        path = save_run(run, self.settings.runs_dir)
        self._emit(on_event, "saved", run_id=run.run_id, path=str(path))
        return run, str(path)
