# MAGI Objective Benchmark v3 — Frozen protocol

## Research question

Does a prespecified heterogeneous MAGI configuration reduce errors on biomedical-methodology reasoning cases compared with a single-model reference, while keeping latency and cost acceptable?

## Primary endpoint

- **Exact case accuracy** on the locked test set.

## Secondary endpoints

- critical-error rate on cases marked `critical=true`;
- partial score for multi-select and numeric tolerance;
- verbalized-confidence Brier score (diagnostic only);
- parsing/API failures;
- latency, tokens and estimated cost per correct answer;
- consistency under a second option permutation.

## Dataset blueprint

- 48 cases total: 24 development + 24 locked test;
- 6 domains per split, 4 cases per domain;
- 12 MCQ, 6 multi-select and 6 numeric cases per split;
- MCQ keys balanced exactly across A/B/C/D;
- mostly intermediate/hard, with explicit critical-error tags;
- option order can be reproducibly permuted, identically for every system in the same case/repeat.

The test-set hash is stored in `protocol_lock_v3.json`. Any edit invalidates the lock and must create a new protocol version.

## Staged execution — no blind trial-and-error

### Phase 0 — Local preflight, zero API calls

```powershell
python -m benchmark.validate_objective
python -m benchmark.preflight --split dev --limit 12 --seed 20260806
python -m benchmark.run_objective --mock --split dev --limit 6
```

Pass only if the dataset lock, selection, parser, scorer and reports are valid.

### Phase 1 — Development baselines

Run all four single models on the complete development set, one fixed option permutation:

```powershell
python -m benchmark.run_objective `
  --real openai --real anthropic --real gemini --real groq `
  --systems openai anthropic gemini groq `
  --split dev --limit 24 --seed 20260806
```

Purpose:

1. detect ceiling/floor effects;
2. choose the **reference baseline** before touching the locked test;
3. identify parser/provider defects;
4. measure baseline disagreement.

Reference selection is lexicographic: lowest critical-error rate, then highest exact accuracy, then lower Brier, cost and latency. Ties must be documented rather than broken informally.

### Phase 2 — Development ablations

Use the 12 prespecified hard development cases selected stratifiably by the same seed. Compare the reference baseline with:

- `majority_hetero`;
- `magi_hetero`;
- `magi_audit`;
- `openai_triad`.

This phase chooses exactly one MAGI finalist. Prompts and system composition may be changed only here.

### Phase 3 — Freeze finalist

Before test execution, record in a run note:

- reference baseline;
- MAGI finalist;
- judge and auditor providers;
- seed and option-order policy;
- primary and secondary endpoints;
- unchanged dataset hash.

### Phase 4 — Locked test

Run only the prespecified reference and finalist on all 24 test cases. The CLI refuses test execution without `--reference-system` and a valid lock.

Example:

```powershell
python -m benchmark.run_objective `
  --real openai --real anthropic --real gemini --real groq `
  --systems openai magi_hetero `
  --reference-system openai `
  --split test --limit 24 --seed 20260806
```

The report uses paired bootstrap intervals and exact McNemar discordant-pair analysis. With 24 cases, interpret results as an engineering pilot, not definitive publication-grade evidence.

### Phase 5 — Robustness, only after primary analysis

Repeat the locked test with a second seed/option permutation. Report answer consistency and do not replace the primary result with the more favorable run.

## Stop rules

Do not proceed to the locked test when:

- the best development baseline is at or near ceiling and fewer than 20% of cases create meaningful disagreement;
- scoring or answer-key defects remain;
- a MAGI configuration does not show a credible mechanism of correction on development cases;
- cost or latency makes the intended use implausible.

Do not modify test questions, answers, prompts or selected systems after seeing test results. Any such change starts a new protocol version.

## Publication-grade extension

The 24-case test is an engineering gate. A serious paper should use a larger independently reviewed locked test set, ideally at least 100 cases, plus defect-level BioAudit validation and external review of answer keys.

## Reliability addendum — v7.2

Provider/API/component failures are not scientific reasoning errors.

For every system the report must include:

- planned rows;
- evaluable rows;
- coverage;
- valid accuracy on technically complete, parsed rows;
- end-to-end accuracy with missing outputs retained as operational failures;
- technical failure rate;
- parse failure rate conditional on technical success;
- critical reasoning error rate on evaluable critical rows only.

A system with coverage below 100% is marked `INCOMPLETE` and cannot be selected as the reference baseline until the failed rows are recovered. Paired comparisons use only the intersection of evaluable rows. Brier score is undefined for missing or malformed outputs and must not be imputed as 1.

The recovery procedure must preserve the original question, option permutation, case seed and judge seed, and must not repeat successful calls.
