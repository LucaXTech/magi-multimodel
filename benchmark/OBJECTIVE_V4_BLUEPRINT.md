# Objective Benchmark v4 — blueprint before dataset construction

## Why v4 is needed

Objective v3 verifies mechanics and basic methodology knowledge, but a top single model can reach ceiling. A benchmark with easy textbook MCQ cannot establish value for a multi-model architecture.

The v4 benchmark must be aligned with the intended BioAudit product: detecting multiple interacting defects, avoiding false alarms on clean protocols, checking calculations and proposing verifiable repairs.

No test case will be sent to a real model before the dataset, taxonomy, metrics and lock are finalized.

## Research questions

### RQ1 — verifier architecture

Can a fast/cheap proposer plus a targeted verifier correct substantive errors while using fewer premium-model calls than full MAGI?

### RQ2 — heterogeneous deliberation

Does heterogeneous MAGI improve recall of critical defects on multi-defect methodology audits without an unacceptable increase in false positives, cost or latency?

### RQ3 — product usefulness

Can BioAudit distinguish clean from defective protocols and return the correct evidence-linked repair actions?

## Case families

### 1. Defect-set audits — primary family

Input: a compact methodology, pipeline or code/protocol fragment containing zero to five prespecified defects.

Output schema:

```json
{
  "defects": ["LEAKAGE_GLOBAL_SCALER", "TEST_SET_TUNING"],
  "critical_defects": ["TEST_SET_TUNING"],
  "evidence_spans": {"TEST_SET_TUNING": "..."},
  "confidence": 0
}
```

Scoring:

- critical-defect recall — primary endpoint;
- defect-level precision, recall and F1;
- false-positive rate on clean twin cases;
- exact set match;
- evidence-location accuracy.

### 2. Clean/defective twins

Each defective protocol has a minimally changed clean twin. This prevents a system from succeeding by flagging every pipeline.

Metrics:

- paired sensitivity to the inserted defect;
- specificity on the clean twin;
- consistency of unchanged findings.

### 3. Claim-validity cases

Output one of:

- `SUPPORTED`;
- `UNSUPPORTED`;
- `INSUFFICIENT_INFORMATION`.

Also return a finite reason code such as `CAUSALITY_NOT_IDENTIFIED`, `EXTERNAL_VALIDATION_MISSING` or `CI_INCLUDES_NULL`.

### 4. Numeric consistency cases

Require both final answer and intermediate quantities. The scorer checks internal arithmetic consistency, not just the final number.

Example fields:

```json
{
  "design_effect": 1.9,
  "effective_n": 63.1579,
  "confidence": 0
}
```

### 5. Executable code cases

Models identify a faulty line or produce a constrained patch. Unit tests determine correctness. Cases cover leakage, grouping, temporal order, metric implementation and signal-processing causality.

## Defect taxonomy

The taxonomy must be finite and versioned before case writing. Initial families:

- data leakage;
- test-set reuse;
- grouping/subject contamination;
- temporal leakage;
- feature-selection scope;
- resampling/preprocessing scope;
- confounding and non-identifiability;
- repeated-measures dependence;
- multiple testing;
- calibration/coverage reporting;
- causal/clinical overclaim;
- non-causal online signal processing;
- event/timestamp misalignment;
- arithmetic/internal inconsistency.

Each defect receives:

- unique code;
- severity rule;
- minimal evidence requirement;
- accepted repair actions;
- confusable non-defects.

## Dataset structure

Engineering pilot target:

- 36 development cases;
- 60 locked test cases;
- at least 20 clean/defective twin pairs;
- balanced defect prevalence and severity;
- no case ID, ordering or wording cue exposed to models;
- algorithmically generated numerical parameters where possible;
- independent answer-key check before lock.

Publication extension:

- at least 100 locked test cases;
- two independent expert reviewers;
- adjudication log;
- preregistration.

## Systems to compare

Single-model baselines:

- OpenAI;
- Anthropic;
- Gemini;
- Groq.

Architectures:

- `fast_then_verify`: fast proposer, premium verifier;
- `majority_hetero`;
- `magi_hetero`;
- `magi_audit`;
- same-model triad as diversity ablation.

Only one finalist reaches the locked test.

## Prespecified selection rule

1. complete technical coverage;
2. lowest critical-defect miss rate;
3. highest defect-level F1;
4. lowest false-positive rate on clean twins;
5. lower cost;
6. lower latency.

Exact case match is secondary because a useful audit may identify most defects without matching the full set perfectly.

## Reliability requirements

- 100% evaluable paired coverage before ranking;
- failed API rows recovered with identical seeds and prompts;
- component failures reported separately;
- no Brier score for missing output;
- no test execution after a ceiling/floor or answer-key defect is discovered;
- test dataset and scoring code locked together by hash.

## Gates

### Gate A — taxonomy and schema

Freeze defect codes, severity rules and JSON schemas.

### Gate B — generator and scorer

Create cases and unit tests without calling real models.

### Gate C — independent answer-key audit

Review every test answer before lock.

### Gate D — development baselines

Run complete baseline coverage; inspect disagreement and failure modes.

### Gate E — architecture tuning

Tune verifier/MAGI only on development.

### Gate F — locked test

Run reference and one finalist once, then robustness permutation.

## Stop rules

Stop or redesign before test when:

- a top baseline is at ceiling;
- clean-case false positives are excessive;
- architecture gains come only from more calls on simple cases;
- provider coverage is incomplete;
- answer keys require post hoc reinterpretation;
- no credible cost/accuracy trade-off exists.
