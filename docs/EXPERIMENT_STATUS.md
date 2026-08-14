# Experiment status

## Objective benchmark v3

Objective v3 was designed as a protocol-driven engineering benchmark with:

- 24 development and 24 locked-test cases;
- balanced domains and MCQ answer positions;
- MCQ, multi-select, and numeric formats;
- stratified case selection;
- deterministic answer-option permutation;
- rotated provider execution order;
- a protocol SHA256 lock;
- objective scoring and paired analysis;
- selective recovery of failed provider calls.

## Development run

The full development baseline run requested 24 cases for each of four providers.

Observed evaluable performance:

| System | Evaluable | Valid accuracy | Technical status |
|---|---:|---:|---|
| OpenAI baseline | 24/24 | 100% | complete |
| Anthropic baseline | 24/24 | 100% | complete |
| Groq baseline | 24/24 | 83.3% | complete |
| Gemini baseline | 10/24 | 100% | incomplete due to quota/rate limiting |

Gemini's initial apparent low accuracy was an instrumentation artifact: failed API calls had been counted as scientific errors. v7.2 corrected the reporting model and added selective recovery. Six additional Gemini rows were successfully recovered before a new rate limit stopped the recovery, leaving 10 evaluable rows in total.

## Decision

Objective v3 is **not** used to claim superiority of any MAGI architecture.

Reasons:

1. two complete premium baselines reached 100% on development;
2. the dataset therefore has insufficient headroom to demonstrate improvement;
3. incomplete Gemini coverage prevents a fair four-provider ranking;
4. opening the locked test after observing a development ceiling would encourage benchmark fishing rather than solve the design problem.

The v3 locked test remains unopened for model comparison. The protocol is retained as an engineering validation artifact.

## Next experiment: Objective v4

The next generation shifts from textbook question answering to methodology auditing. Planned design principles include:

- a frozen defect taxonomy;
- clean/defective paired cases;
- multiple interacting defects;
- defect-level precision/recall/F1;
- critical-defect recall as a primary safety-oriented metric;
- evidence-span scoring;
- repair-quality checks;
- executable numeric/code cases where possible;
- explicit false-positive measurement on clean cases;
- independent audit of answer keys before the locked test;
- cost and latency measured alongside quality.

MAGI architecture comparisons will resume only after the development set demonstrates adequate discrimination among single-model baselines.
