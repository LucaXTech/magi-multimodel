from __future__ import annotations

import argparse
import json
import re
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from .config import Settings
from .demo import build_demo_run, list_demo_cases
from .orchestrator import MagiOrchestrator
from .providers import PROVIDER_NAMES, build_providers


STATIC_DIR = Path(__file__).with_name("static")
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
DEMO_MODE = False


class RunRequest(BaseModel):
    question: str = Field(min_length=3, max_length=12000)
    real_providers: list[str] = Field(default_factory=list)
    critique: bool = False
    score: bool = True
    auditor: bool = False
    blind_judge: bool = False
    random_seed: int | None = None
    demo_case: str | None = None


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(self, request: RunRequest) -> str:
        job_id = uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._jobs[job_id] = {
                "job_id": job_id,
                "status": "queued",
                "phase": "queued",
                "message": "Run in coda",
                "created_at": now,
                "updated_at": now,
                "request": request.model_dump(),
                "events": [],
                "result": None,
                "error": None,
            }
        return job_id

    def update(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.update(fields)
            job["updated_at"] = datetime.now(timezone.utc).isoformat()

    def event(self, job_id: str, event: str, payload: dict[str, Any]) -> None:
        phase_messages = {
            "initial_started": ("initial", "I tre agenti stanno analizzando"),
            "initial_completed": ("initial_done", "Analisi iniziali completate"),
            "critique_started": ("critique", "Critica incrociata in corso"),
            "critique_completed": ("critique_done", "Critiche completate"),
            "auditor_started": ("auditor", "Audit esterno indipendente"),
            "auditor_completed": ("auditor_done", "Audit esterno completato"),
            "judge_started": ("judge", "Il giudice sta deliberando"),
            "judge_completed": ("judge_done", "Verdetto completato"),
            "score_started": ("score", "Valutazione dei contributi"),
            "score_completed": ("score_done", "Scorecard completata"),
            "saved": ("saved", "Run salvato"),
        }
        phase, message = phase_messages.get(event, (event, event))
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job["status"] = "running"
            job["phase"] = phase
            job["message"] = message
            job["updated_at"] = datetime.now(timezone.utc).isoformat()
            job["events"].append(
                {
                    "event": event,
                    "payload": payload,
                    "at": job["updated_at"],
                }
            )
            job["events"] = job["events"][-20:]

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return json.loads(json.dumps(job)) if job is not None else None


jobs = JobStore()
app = FastAPI(title="MAGI Console", version="0.7.0")


def _run_worker(job_id: str, request: RunRequest) -> None:
    try:
        settings = Settings.from_env()
        unknown = set(request.real_providers).difference(PROVIDER_NAMES)
        if unknown:
            raise ValueError("Provider non validi: " + ", ".join(sorted(unknown)))
        providers = build_providers(
            settings,
            mock=False,
            real_providers=request.real_providers,
        )
        orchestrator = MagiOrchestrator(settings, providers)
        jobs.update(job_id, status="running", phase="starting", message="Avvio MAGI")
        run, path = orchestrator.run(
            request.question,
            critique=request.critique,
            score=request.score,
            auditor=request.auditor,
            blind_judge=request.blind_judge,
            random_seed=request.random_seed,
            on_event=lambda event, payload: jobs.event(job_id, event, payload),
        )
        jobs.update(
            job_id,
            status="completed",
            phase="completed",
            message="Deliberazione completata",
            result=run.to_dict(),
            output_path=path,
        )
    except Exception as exc:
        jobs.update(
            job_id,
            status="error",
            phase="error",
            message="Errore durante il run",
            error=f"{type(exc).__name__}: {exc}",
        )


def _demo_worker(job_id: str, request: RunRequest) -> None:
    try:
        case_id = request.demo_case or "eeg_subject_leakage"

        jobs.update(
            job_id,
            status="running",
            phase="starting",
            message="Starting prerecorded demo",
        )

        jobs.event(job_id, "initial_started", {"demo": True})
        time.sleep(0.25)
        jobs.event(job_id, "initial_completed", {"demo": True})

        if request.critique:
            time.sleep(0.20)
            jobs.event(job_id, "critique_started", {"demo": True})
            time.sleep(0.25)
            jobs.event(job_id, "critique_completed", {"demo": True})

        if request.auditor:
            time.sleep(0.20)
            jobs.event(job_id, "auditor_started", {"demo": True})
            time.sleep(0.25)
            jobs.event(job_id, "auditor_completed", {"demo": True})

        time.sleep(0.20)
        jobs.event(job_id, "judge_started", {"demo": True})
        time.sleep(0.25)
        jobs.event(job_id, "judge_completed", {"demo": True})

        if request.score:
            time.sleep(0.20)
            jobs.event(job_id, "score_started", {"demo": True})
            time.sleep(0.25)
            jobs.event(job_id, "score_completed", {"demo": True})

        run = build_demo_run(
            case_id,
            critique=request.critique,
            score=request.score,
            auditor=request.auditor,
        )

        jobs.update(
            job_id,
            status="completed",
            phase="completed",
            message="Prerecorded demo completed",
            result=run,
            output_path=None,
        )

    except Exception as exc:
        jobs.update(
            job_id,
            status="error",
            phase="error",
            message="Demo failed",
            error=f"{type(exc).__name__}: {exc}",
        )


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/style.css")
def style() -> FileResponse:
    return FileResponse(STATIC_DIR / "style.css", media_type="text/css")


@app.get("/app.js")
def javascript() -> FileResponse:
    return FileResponse(STATIC_DIR / "app.js", media_type="application/javascript")


@app.get("/api/config")
def config() -> dict[str, Any]:
    if DEMO_MODE:
        return {
            "available": {
                "openai": True,
                "anthropic": True,
                "gemini": True,
                "groq": True,
            },
            "models": {
                "openai": "recorded-demo",
                "anthropic": "recorded-demo",
                "gemini": "recorded-demo",
                "groq": "recorded-demo",
            },
            "judge_provider": "openai",
            "auditor_provider": "groq",
            "demo_mode": True,
            "demo_cases": list_demo_cases(),
        }

    settings = Settings.from_env()
    return {
        "available": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "gemini": bool(settings.gemini_api_key),
            "groq": bool(settings.groq_api_key),
        },
        "models": {
            "openai": settings.openai_model,
            "anthropic": settings.anthropic_model,
            "gemini": settings.gemini_model,
            "groq": settings.groq_model,
        },
        "judge_provider": settings.judge_provider,
        "auditor_provider": settings.auditor_provider,
        "demo_mode": DEMO_MODE,
        "demo_cases": list_demo_cases() if DEMO_MODE else [],
    }


@app.post("/api/jobs")
def create_job(request: RunRequest) -> dict[str, str]:
    request.real_providers = list(dict.fromkeys(p.lower() for p in request.real_providers))
    job_id = jobs.create(request)
    worker = _demo_worker if DEMO_MODE else _run_worker
    thread = threading.Thread(
        target=worker,
        args=(job_id, request),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job non trovato")
    return job


def _run_summary(payload: dict[str, Any]) -> dict[str, Any]:
    verdict = payload.get("verdict") or {}
    scorecard = payload.get("scorecard") or {}
    text = verdict.get("text") or ""
    return {
        "run_id": payload.get("run_id"),
        "created_at": payload.get("created_at"),
        "question": payload.get("question"),
        "critique_enabled": payload.get("critique_enabled", False),
        "scoring_enabled": payload.get("scoring_enabled", False),
        "wall_time_seconds": payload.get("wall_time_seconds"),
        "preview": text[:280],
        "global_confidence": scorecard.get("global_confidence"),
    }


@app.get("/api/runs")
def list_runs(limit: int = 12) -> list[dict[str, Any]]:
    if DEMO_MODE:
        return []
    settings = Settings.from_env()
    directory = settings.runs_dir
    if not directory.exists():
        return []
    summaries: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            summaries.append(_run_summary(payload))
        except (OSError, json.JSONDecodeError):
            continue
        if len(summaries) >= max(1, min(limit, 50)):
            break
    return summaries


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise HTTPException(status_code=400, detail="Run ID non valido")
    path = Settings.from_env().runs_dir / f"{run_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Run non trovato")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"Run illeggibile: {exc}") from exc


def main() -> None:
    global DEMO_MODE

    parser = argparse.ArgumentParser(description="MAGI touch-friendly web console")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--reload", action="store_true")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with prerecorded demonstrations and no external model API calls.",
    )
    args = parser.parse_args()

    DEMO_MODE = args.demo

    if DEMO_MODE:
        if args.reload:
            parser.error("--demo cannot be combined with --reload")
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
        )
    else:
        uvicorn.run(
            "magi.web:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
        )


if __name__ == "__main__":
    main()
