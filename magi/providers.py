from __future__ import annotations

import time
import json
from abc import ABC, abstractmethod
from typing import Any, Iterable

from .config import Settings
from .types import LLMResult

PROVIDER_NAMES = ("openai", "anthropic", "gemini", "groq")


#       /\_/\
#      ( ^.^ )  Many engines, one careful boundary.
#       > ~ <
def _get_attr(obj: Any, name: str) -> Any:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _incomplete_reason(response: Any) -> str | None:
    details = _get_attr(response, "incomplete_details")
    return _get_attr(details, "reason") or _get_attr(details, "type")


class Provider(ABC):
    name: str
    model: str

    @abstractmethod
    def generate(self, system: str, prompt: str) -> LLMResult:
        raise NotImplementedError


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        max_output_tokens: int,
        reasoning_effort: str,
        verbosity: str,
    ) -> None:
        from openai import OpenAI

        self.model = model
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.verbosity = verbosity
        self.client = OpenAI(api_key=api_key)

    def generate(self, system: str, prompt: str) -> LLMResult:
        start = time.perf_counter()
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system,
                input=prompt,
                max_output_tokens=self.max_output_tokens,
                reasoning={"effort": self.reasoning_effort},
                text={"verbosity": self.verbosity},
                store=False,
            )
            usage = _get_attr(response, "usage")
            return LLMResult(
                provider=self.name,
                model=self.model,
                text=(response.output_text or "").strip(),
                latency_seconds=round(time.perf_counter() - start, 3),
                input_tokens=_get_attr(usage, "input_tokens"),
                output_tokens=_get_attr(usage, "output_tokens"),
                status=_get_attr(response, "status"),
                incomplete_reason=_incomplete_reason(response),
            )
        except Exception as exc:
            return LLMResult(
                provider=self.name,
                model=self.model,
                text="",
                latency_seconds=round(time.perf_counter() - start, 3),
                error=f"{type(exc).__name__}: {exc}",
                status="error",
            )


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, max_output_tokens: int, thinking_mode: str) -> None:
        from anthropic import Anthropic

        self.model = model
        self.max_output_tokens = max_output_tokens
        self.thinking_mode = thinking_mode
        self.client = Anthropic(api_key=api_key)

    def generate(self, system: str, prompt: str) -> LLMResult:
        start = time.perf_counter()
        try:
            request: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self.max_output_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            }
            if self.thinking_mode == "disabled":
                request["thinking"] = {"type": "disabled"}
            message = self.client.messages.create(**request)
            text = "\n".join(
                block.text
                for block in message.content
                if getattr(block, "type", None) == "text"
            ).strip()
            usage = getattr(message, "usage", None)
            stop_reason = getattr(message, "stop_reason", None)
            return LLMResult(
                provider=self.name,
                model=self.model,
                text=text,
                latency_seconds=round(time.perf_counter() - start, 3),
                input_tokens=_get_attr(usage, "input_tokens"),
                output_tokens=_get_attr(usage, "output_tokens"),
                status="incomplete" if stop_reason == "max_tokens" else "completed",
                incomplete_reason="max_tokens" if stop_reason == "max_tokens" else None,
            )
        except Exception as exc:
            return LLMResult(
                provider=self.name,
                model=self.model,
                text="",
                latency_seconds=round(time.perf_counter() - start, 3),
                error=f"{type(exc).__name__}: {exc}",
                status="error",
            )


class GeminiProvider(Provider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, max_output_tokens: int) -> None:
        from google import genai

        self.model = model
        self.max_output_tokens = max_output_tokens
        self.client = genai.Client(api_key=api_key)

    def generate(self, system: str, prompt: str) -> LLMResult:
        start = time.perf_counter()
        try:
            interaction = self.client.interactions.create(
                model=self.model,
                input=f"{system}\n\n{prompt}",
            )
            usage = (
                _get_attr(interaction, "usage")
                or _get_attr(interaction, "usage_metadata")
                or _get_attr(interaction, "usageMetadata")
            )

            def usage_value(*names: str) -> int | None:
                for name in names:
                    value = _get_attr(usage, name)
                    if value is not None:
                        try:
                            return int(value)
                        except (TypeError, ValueError):
                            continue
                return None

            return LLMResult(
                provider=self.name,
                model=self.model,
                text=(interaction.output_text or "").strip(),
                latency_seconds=round(time.perf_counter() - start, 3),
                input_tokens=usage_value(
                    "input_tokens",
                    "prompt_token_count",
                    "promptTokenCount",
                    "input_token_count",
                    "inputTokenCount",
                    "prompt_tokens",
                ),
                output_tokens=usage_value(
                    "output_tokens",
                    "candidates_token_count",
                    "candidatesTokenCount",
                    "output_token_count",
                    "outputTokenCount",
                    "completion_tokens",
                ),
                status=_get_attr(interaction, "status") or "completed",
            )
        except Exception as exc:
            return LLMResult(
                provider=self.name,
                model=self.model,
                text="",
                latency_seconds=round(time.perf_counter() - start, 3),
                error=f"{type(exc).__name__}: {exc}",
                status="error",
            )


class GroqProvider(Provider):
    name = "groq"

    def __init__(self, api_key: str, model: str, max_output_tokens: int) -> None:
        from groq import Groq

        self.model = model
        self.max_output_tokens = max_output_tokens
        self.client = Groq(api_key=api_key)

    def generate(self, system: str, prompt: str) -> LLMResult:
        start = time.perf_counter()
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_output_tokens,
            )
            choice = completion.choices[0]
            usage = getattr(completion, "usage", None)
            finish_reason = getattr(choice, "finish_reason", None)
            return LLMResult(
                provider=self.name,
                model=self.model,
                text=(choice.message.content or "").strip(),
                latency_seconds=round(time.perf_counter() - start, 3),
                input_tokens=_get_attr(usage, "prompt_tokens"),
                output_tokens=_get_attr(usage, "completion_tokens"),
                status="incomplete" if finish_reason == "length" else "completed",
                incomplete_reason="max_tokens" if finish_reason == "length" else None,
            )
        except Exception as exc:
            return LLMResult(
                provider=self.name,
                model=self.model,
                text="",
                latency_seconds=round(time.perf_counter() - start, 3),
                error=f"{type(exc).__name__}: {exc}",
                status="error",
            )


class MockProvider(Provider):
    def __init__(self, name: str, model: str = "mock-v2") -> None:
        self.name = name
        self.model = model

    def generate(self, system: str, prompt: str) -> LLMResult:
        start = time.perf_counter()
        lower = prompt.lower()
        if "bioaudit_report_json_v1" in lower:
            report_json = (
                '{"verdict":"REVISE","summary":"La pipeline richiede correzioni metodologiche prima di sostenere claim di generalizzazione.",'
                '"critical_issues":[{"title":"Split non indipendente","evidence_from_input":"split casuale delle finestre",'
                '"why_it_matters":"Finestre correlate possono contaminare train e test.",'
                '"recommended_fix":"Separare i dati secondo l unità di generalizzazione.",'
                '"verification":"Auditare ID, sessioni e intervalli temporali tra split."}],'
                '"moderate_issues":[],"strengths":["Obiettivo applicativo dichiarato"],'
                '"missing_information":["Dettagli completi del protocollo"],'
                '"disagreements_resolved":[],"next_actions":["Ricostruire gli split","Rieseguire la validazione"],'
                '"internal_confidence":84}'
            )
            return LLMResult(
                provider=self.name, model=self.model, text=report_json,
                latency_seconds=round(time.perf_counter() - start, 3),
                input_tokens=240, output_tokens=260, status="completed",
            )
        if "benchmark_objective" in lower:
            answer = "A"
            if "72" in lower and "18" in lower:
                answer = 0.8
            elif "81" in lower and "9" in lower:
                answer = 0.9
            elif "250 hz" in lower and "nyquist" in lower:
                answer = 125
            elif "nperseg=500" in lower:
                answer = 0.5
            objective_json = json.dumps(
                {"answer": answer, "confidence": 70, "rationale": "Risposta mock per test tecnico."},
                ensure_ascii=False,
            )
            return LLMResult(
                provider=self.name, model=self.model, text=objective_json,
                latency_seconds=round(time.perf_counter() - start, 3),
                input_tokens=120, output_tokens=45, status="completed",
            )
        if "magi_scorecard_json_v1" in lower:
            score_json = (
                '{"global_confidence":82,"consensus_level":68,"agents":['
                '{"agent":"MELCHIOR","technical_rigor":88,"relevance":90,'
                '"uncertainty_handling":84,"practical_value":80,'
                '"decision_weight":42,"rationale":"Analisi tecnica completa e verificabile."},'
                '{"agent":"BALTHASAR","technical_rigor":82,"relevance":78,'
                '"uncertainty_handling":91,"practical_value":68,'
                '"decision_weight":28,"rationale":"Buon controllo dei rischi e delle assunzioni."},'
                '{"agent":"CASPER","technical_rigor":74,"relevance":82,'
                '"uncertainty_handling":70,"practical_value":92,'
                '"decision_weight":30,"rationale":"Contributo pragmatico utile per l MVP."}'
                '],"strongest_contribution":"Separazione netta tra dati di training e test.",'
                '"main_correction":"Evitare conclusioni categoriche non supportate.",'
                '"residual_uncertainty":"Servono dati reali e una ground truth esterna."}'
            )
            return LLMResult(
                provider=self.name,
                model=self.model,
                text=score_json,
                latency_seconds=round(time.perf_counter() - start, 3),
                input_tokens=180,
                output_tokens=220,
                status="completed",
            )
        if "finestre" in lower and "soggett" in lower:
            core = (
                "Lo split casuale a livello di finestra può creare subject leakage. "
                "Usare GroupKFold, split per soggetto o LOSO e fare fit del "
                "preprocessing soltanto sul training fold."
            )
        elif "standardizz" in lower and "dataset" in lower:
            core = (
                "Standardizzare prima della cross-validation crea data leakage. "
                "Inserire lo scaler in una pipeline, fare fit sul training fold e "
                "applicare la trasformazione a validation e test."
            )
        elif "tp=72" in lower:
            core = (
                "La sensibilità è TP/(TP+FN) = 72/(72+18) = 0.8, cioè 80%. "
                "È la quota di positivi reali identificati correttamente."
            )
        else:
            core = (
                "Occorre esplicitare obiettivo, vincoli, dati disponibili, criterio "
                "di successo e assunzioni prima di scegliere la soluzione."
            )
        emphasis = {
            "openai": "1. PROPOSTA\nPropongo una pipeline operativa e verificabile.",
            "anthropic": "1. ERRORE O RISCHIO PRINCIPALE\nSegnalo bias e rischi di validità.",
            "gemini": "1. SOLUZIONE PRATICA\nPartirei da un MVP economico.",
            "groq": "1. AUDIT INDIPENDENTE\nCerco errori condivisi e conclusioni non supportate.",
        }.get(self.name, "Sintesi.")
        return LLMResult(
            provider=self.name,
            model=self.model,
            text=f"{emphasis}\n{core}",
            latency_seconds=round(time.perf_counter() - start, 3),
            input_tokens=100,
            output_tokens=60,
            status="completed",
        )


def _real_provider(name: str, settings: Settings) -> Provider:
    if name == "openai":
        if not settings.openai_api_key:
            raise RuntimeError("Manca OPENAI_API_KEY nel file .env.")
        return OpenAIProvider(
            settings.openai_api_key,
            settings.openai_model,
            settings.max_output_tokens,
            settings.openai_reasoning_effort,
            settings.openai_verbosity,
        )
    if name == "anthropic":
        if not settings.anthropic_api_key:
            raise RuntimeError("Manca ANTHROPIC_API_KEY nel file .env.")
        return AnthropicProvider(
            settings.anthropic_api_key,
            settings.anthropic_model,
            settings.max_output_tokens,
            settings.anthropic_thinking,
        )
    if name == "groq":
        if not settings.groq_api_key:
            raise RuntimeError("Manca GROQ_API_KEY nel file .env.")
        return GroqProvider(
            settings.groq_api_key,
            settings.groq_model,
            settings.max_output_tokens,
        )
    if name == "gemini":
        if not settings.gemini_api_key:
            raise RuntimeError("Manca GEMINI_API_KEY nel file .env.")
        return GeminiProvider(
            settings.gemini_api_key,
            settings.gemini_model,
            settings.max_output_tokens,
        )
    raise ValueError(f"Provider sconosciuto: {name}")


def build_providers(
    settings: Settings,
    mock: bool = False,
    real_providers: Iterable[str] | None = None,
) -> dict[str, Provider]:
    """Crea provider mock, ibridi o tutti reali."""
    if mock and real_providers:
        raise ValueError("Non usare --mock e --real insieme.")

    if mock:
        selected: set[str] = set()
    elif real_providers is None:
        selected = set(PROVIDER_NAMES)
    else:
        selected = {name.lower() for name in real_providers}
        unknown = selected.difference(PROVIDER_NAMES)
        if unknown:
            raise ValueError("Provider non validi: " + ", ".join(sorted(unknown)))

    return {
        name: _real_provider(name, settings) if name in selected else MockProvider(name)
        for name in PROVIDER_NAMES
    }
