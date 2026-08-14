# MAGI / BioAudit Roadmap — evidence first

## Current state

- multi-provider orchestrator works;
- BioAudit prototype works;
- objective v3 mechanics, locking, permutation and logging work;
- reliability reporting and selective recovery are available in v7.2;
- objective v3 must not proceed to locked test when the development gate shows ceiling or incomplete provider coverage.

## Gate 0 — technical integrity

Pass criteria:

- dataset and protocol lock valid;
- all automated tests pass;
- mock run produces complete artifacts;
- API failures are separated from reasoning errors;
- failed rows can be recovered without repeating successful calls.

## Gate 1 — complete development baselines

Every baseline must have 100% evaluable coverage. Incomplete providers are recovered before comparison.

Do not rank systems using end-to-end failure rows as if they were scientific answers.

## Gate 2 — discrimination check

Stop objective v3 when:

- a top baseline reaches 100%;
- fewer than 20% of jointly evaluable cases create meaningful outcome disagreement;
- the test set uses the same easy textbook template.

The correct action is a new protocol, not opening the locked test to search for favorable separation.

## Gate 3 — objective v4 design

Before new API calls:

1. freeze defect taxonomy;
2. freeze structured output schemas;
3. create clean/defective twins;
4. implement defect-level and evidence-level scoring;
5. add executable numeric/code checks;
6. independently audit answer keys;
7. lock development/test datasets and scorer together.

See `benchmark/OBJECTIVE_V4_BLUEPRINT.md`.

## Gate 4 — development architecture comparison

Compare complete baselines with:

- fast proposer + targeted verifier;
- heterogeneous MAGI;
- MAGI with adversarial auditor;
- same-model triad ablation.

Selection priority:

1. critical-defect recall;
2. defect-level F1;
3. clean-case false-positive rate;
4. cost;
5. latency.

## Gate 5 — locked test

Only the prespecified reference and one finalist run on the locked test. A second permutation is robustness analysis, never a replacement for the primary run.

## Gate 6 — investment decision

Continue only if at least one operational value is demonstrated:

- fewer critical misses than the reference;
- comparable quality using fewer premium calls;
- better defect recall without excessive false positives;
- evidence-linked repairs that save reviewer time;
- reproducible benefit attributable to verifier, auditor or model diversity.

## Gate 7 — productization

After positive evidence:

- upload `.txt`, `.md`, `.py`, `.ipynb`;
- evidence-linked issue cards;
- report export and audit history;
- privacy/redaction controls;
- Raspberry Pi touchscreen as a console, not as the core value proposition.
