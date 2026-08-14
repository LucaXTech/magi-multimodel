# MAGI

[![Tests](https://github.com/LucaXTech/magi-multimodel/actions/workflows/tests.yml/badge.svg)](https://github.com/LucaXTech/magi-multimodel/actions/workflows/tests.yml)

**Multi-model deliberation and biomedical methodology auditing.**

MAGI is an experimental Python framework that orchestrates heterogeneous LLM providers as specialized agents, compares their reasoning, and produces a final synthesis. The repository also includes **BioAudit**, a vertical prototype for auditing biomedical/ML methodology, and an evidence-first benchmark framework for evaluating whether multi-model deliberation actually adds value.

> Status: research prototype. MAGI/BioAudit is not a medical device and does not replace clinical, statistical, regulatory, or scientific review.

## Why this project exists

Calling several models is easy. Demonstrating that the extra calls improve reliability is not.

MAGI is built around that distinction. The project separates:

- **orchestration** — multiple providers and specialized roles;
- **verification** — adversarial review and structured synthesis;
- **measurement** — locked benchmark protocols, objective scoring, coverage, cost, and latency;
- **product exploration** — BioAudit as a practical methodology-auditing use case.

## Architecture

- **MELCHIOR / OpenAI** — technical analysis
- **BALTHASAR / Anthropic** — scientific review / red-team
- **CASPER / Gemini** — pragmatic evaluation
- **AUDITOR / Groq-Llama** — independent challenge of consensus
- **JUDGE** — final structured synthesis

Providers and model IDs are configurable in `.env`; they are not hard-coded assumptions of the experimental protocol.

## Current evidence

Objective benchmark v3 successfully validated the engineering pipeline: deterministic case locking, stratified selection, answer-option permutation, provider rotation, objective scoring, and selective recovery of failed API calls.

The development run also exposed an important limitation: the dataset showed a **ceiling effect** for the strongest baselines. The locked test was therefore *not* opened. Gemini experienced quota/rate-limit failures; v7.2+ explicitly separates technical availability from reasoning accuracy.

This is intentional evidence-first behavior: an insufficiently discriminative benchmark is retired rather than mined for a favorable result.

See [`docs/EXPERIMENT_STATUS.md`](docs/EXPERIMENT_STATUS.md) and [`benchmark/OBJECTIVE_V4_BLUEPRINT.md`](benchmark/OBJECTIVE_V4_BLUEPRINT.md).

## Quick start

### 1. Environment

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add only the providers you want to use.

### 2. MAGI console

```powershell
python -m magi.web
```

Open `http://127.0.0.1:8080`.

### 3. BioAudit

```powershell
python -m bioaudit.web
```

Open `http://127.0.0.1:8081`.

Free mock smoke test:

```powershell
python -m bioaudit.cli --file bioaudit\examples\eeg_pipeline.txt --mock
```

### 4. Benchmark integrity checks

These commands do not call external APIs:

```powershell
python -m benchmark.validate_objective
python -m benchmark.preflight --split dev --limit 12 --seed 20260806
python -m benchmark.run_objective --mock --split dev --limit 6
python -m pytest -q
```

## Reliable benchmark reporting

MAGI distinguishes:

- **valid accuracy** — accuracy only on technically valid, parsed responses;
- **coverage** — fraction of requested evaluations that are actually evaluable;
- **end-to-end accuracy** — operational success including provider availability;
- **technical failures** — API/rate-limit/provider failures;
- **critical reasoning errors** — substantive errors only on evaluable responses.

Incomplete systems are not eligible for scientific ranking.

### Audit an existing run without API calls

```powershell
python -m benchmark.audit_objective_run objective_results_v3\<timestamp>
```

### Recover only failed rows

```powershell
python -m benchmark.recover_objective objective_results_v3\<timestamp> `
  --systems gemini --real gemini --dry-run
```

Remove `--dry-run` only when you deliberately want to spend API quota.

## BioAudit direction

BioAudit is being developed as the first concrete use case for MAGI. Its target output is not a generic chatbot response but an evidence-linked review containing:

- critical and moderate methodological defects;
- evidence from the submitted method/pipeline;
- recommended repair;
- verification step;
- missing information;
- prioritized next actions.

The next benchmark generation focuses on **defect-level detection and repair**, clean/defective twins, executable checks, and false-positive control rather than textbook multiple-choice questions.

## Repository safety

- Never commit `.env` or API keys.
- Generated runs and benchmark outputs are ignored by Git.
- Do not submit identifiable patient data or confidential material to external APIs without appropriate authorization and controls.
- Check provider terms, data handling, and retention requirements before using sensitive material.

See [`SECURITY.md`](SECURITY.md).

## Roadmap

The project follows explicit gates rather than adding agents indefinitely:

1. technical integrity;
2. complete development baselines;
3. benchmark discrimination check;
4. objective v4 design;
5. architecture ablations;
6. locked test;
7. investment decision;
8. productization.

See [`ROADMAP.md`](ROADMAP.md).

## License

No open-source license has been selected yet. Until a license is added, standard copyright rules apply.
