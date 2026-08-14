from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class LLMResult:
    provider: str
    model: str
    text: str
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    error: str | None = None
    status: str | None = None
    incomplete_reason: str | None = None

    @property
    def is_incomplete(self) -> bool:
        return self.status == "incomplete" or self.incomplete_reason is not None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AgentResult:
    agent: str
    role: str
    initial: LLMResult
    critique: LLMResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "role": self.role,
            "initial": self.initial.to_dict(),
            "critique": self.critique.to_dict() if self.critique else None,
        }


@dataclass
class AgentScore:
    agent: str
    technical_rigor: int
    relevance: int
    uncertainty_handling: int
    practical_value: int
    decision_weight: int
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Scorecard:
    evaluator: LLMResult
    parsed: bool
    global_confidence: int | None = None
    consensus_level: int | None = None
    agents: list[AgentScore] = field(default_factory=list)
    strongest_contribution: str = ""
    main_correction: str = ""
    residual_uncertainty: str = ""
    parse_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evaluator": self.evaluator.to_dict(),
            "parsed": self.parsed,
            "global_confidence": self.global_confidence,
            "consensus_level": self.consensus_level,
            "agents": [agent.to_dict() for agent in self.agents],
            "strongest_contribution": self.strongest_contribution,
            "main_correction": self.main_correction,
            "residual_uncertainty": self.residual_uncertainty,
            "parse_error": self.parse_error,
        }


@dataclass
class MagiRun:
    run_id: str
    question: str
    critique_enabled: bool
    scoring_enabled: bool = False
    auditor_enabled: bool = False
    blind_judge_enabled: bool = False
    candidate_map: dict[str, str] = field(default_factory=dict)
    random_seed: int | None = None
    agents: list[AgentResult] = field(default_factory=list)
    auditor: LLMResult | None = None
    verdict: LLMResult | None = None
    scorecard: Scorecard | None = None
    created_at: str = ""
    wall_time_seconds: float | None = None

    def all_calls(self) -> list[LLMResult]:
        calls: list[LLMResult] = []
        for agent in self.agents:
            calls.append(agent.initial)
            if agent.critique is not None:
                calls.append(agent.critique)
        if self.auditor is not None:
            calls.append(self.auditor)
        if self.verdict is not None:
            calls.append(self.verdict)
        if self.scorecard is not None:
            calls.append(self.scorecard.evaluator)
        return calls

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "question": self.question,
            "critique_enabled": self.critique_enabled,
            "scoring_enabled": self.scoring_enabled,
            "auditor_enabled": self.auditor_enabled,
            "blind_judge_enabled": self.blind_judge_enabled,
            "candidate_map": self.candidate_map,
            "random_seed": self.random_seed,
            "agents": [agent.to_dict() for agent in self.agents],
            "auditor": self.auditor.to_dict() if self.auditor else None,
            "verdict": self.verdict.to_dict() if self.verdict else None,
            "scorecard": self.scorecard.to_dict() if self.scorecard else None,
            "wall_time_seconds": self.wall_time_seconds,
        }
