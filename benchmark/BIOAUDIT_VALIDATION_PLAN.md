# BioAudit validation plan

BioAudit is evaluated separately from the objective reasoning benchmark.

## Unit of evaluation

A synthetic or de-identified protocol containing a predefined set of defects and clean controls.

## Defect taxonomy

- subject/session/site leakage;
- preprocessing or feature-selection leakage;
- test-set tuning;
- wrong unit of analysis;
- confounding and batch effects;
- missing-data bias;
- multiple-comparison errors;
- non-causal real-time signal processing;
- unsupported clinical or causal claims.

## Objective metrics

- defect-level sensitivity/recall;
- false-positive rate on clean controls;
- severity classification accuracy;
- evidence-location accuracy;
- proportion of recommended fixes that are executable;
- time and cost per audited protocol.

## Dataset structure

Use paired variants: one clean protocol and one minimally modified defective twin. This supports direct measurement of whether BioAudit reacts to the planted defect rather than to style or topic.

Long free-form human scoring is not mandatory. Human review is reserved for a small sample of ambiguous evidence links and recommended fixes.
