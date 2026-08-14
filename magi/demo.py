from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


DEMO_CASES = {
    "eeg_subject_leakage": {
        "title": "EEG subject leakage",
        "question": (
            "We have EEG recordings from 18 participants. The continuous recordings "
            "are split into 2-second windows and the windows are randomly divided "
            "80/20 into training and test sets. A classifier reaches 94% accuracy. "
            "Evaluate the methodology."
        ),
    },
    "imbalanced_accuracy": {
        "title": "Imbalanced classification metric",
        "question": (
            "A binary biomedical classifier is evaluated on a dataset containing "
            "950 negative and 50 positive samples. It predicts every sample as "
            "negative and obtains 95% accuracy. Evaluate the reported performance."
        ),
    },
}


def list_demo_cases() -> list[dict[str, str]]:
    return [
        {
            "id": case_id,
            "title": case["title"],
            "question": case["question"],
        }
        for case_id, case in DEMO_CASES.items()
    ]


def _call(
    provider: str,
    model: str,
    text: str,
    latency: float,
    input_tokens: int,
    output_tokens: int,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "text": text,
        "latency_seconds": latency,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "error": None,
        "status": "completed",
        "demo_recording": True,
    }


def _eeg_leakage_run(
    critique: bool,
    score: bool,
    auditor: bool,
) -> dict[str, Any]:
    melchior = _call(
        "openai",
        "recorded-demo",
        """### Primary finding

The reported 94% accuracy is not a reliable estimate of subject-level generalization.

- Windows from the same participant can appear in both training and test sets.
- EEG windows from one participant are statistically dependent and share subject-specific structure.
- Random window-level splitting therefore permits **subject leakage**.

### Recommended correction

Split the dataset by participant before creating the final training and test partitions. For model selection, use grouped cross-validation such as leave-one-subject-out or GroupKFold.

The performance should then be recomputed on participants that were never observed during training.""",
        1.31,
        742,
        184,
    )

    balthasar = _call(
        "anthropic",
        "recorded-demo",
        """### Scientific review

The central methodological defect is a mismatch between the claimed target of generalization and the validation unit.

The experimental unit is the **participant**, not the individual 2-second segment. Randomly assigning correlated epochs to train and test sets violates the independence assumption underlying the reported held-out accuracy.

A valid evaluation should preserve participant independence and should report uncertainty across subjects, not only across windows.

Until subject-independent validation is performed, the 94% result should not be interpreted as evidence that the classifier generalizes to new participants.""",
        1.48,
        791,
        201,
    )

    casper = _call(
        "gemini",
        "recorded-demo",
        """### Practical assessment

The model may genuinely detect EEG structure, but the current experiment cannot tell whether it learned the target phenomenon or participant identity.

The immediate action is inexpensive:

1. assign each participant to only one split;
2. rerun preprocessing without fitting data-dependent transforms on held-out subjects;
3. evaluate balanced accuracy, ROC-AUC where appropriate, and subject-level variability;
4. compare the new result with the original 94%.

A large performance drop after grouped validation would be evidence that the original estimate was optimistic.""",
        1.12,
        701,
        176,
    )

    critique_text = """The other reviewers correctly identify subject leakage. I would additionally verify whether normalization, feature selection, artifact rejection thresholds, or hyperparameter tuning were computed using data from held-out participants."""

    agents = [
        {
            "agent": "MELCHIOR",
            "initial": melchior,
            "critique": _call(
                "openai",
                "recorded-demo",
                critique_text,
                0.61,
                318,
                71,
            ) if critique else None,
        },
        {
            "agent": "BALTHASAR",
            "initial": balthasar,
            "critique": _call(
                "anthropic",
                "recorded-demo",
                critique_text,
                0.66,
                329,
                73,
            ) if critique else None,
        },
        {
            "agent": "CASPER",
            "initial": casper,
            "critique": _call(
                "gemini",
                "recorded-demo",
                critique_text,
                0.54,
                301,
                69,
            ) if critique else None,
        },
    ]

    auditor_result = None
    if auditor:
        auditor_result = _call(
            "groq",
            "recorded-demo",
            """### Independent audit

Consensus on subject leakage is justified, but agreement alone is not proof.

I checked for alternative interpretations of the described split. The text explicitly states that **windows** are randomly divided 80/20 after segmentation, with no participant grouping. That is sufficient evidence for a high-risk validation defect.

Additional checks required:

- confirm preprocessing is fit within each training fold;
- report participant counts in every split;
- ensure repeated windows from one recording cannot cross partitions;
- distinguish window-level accuracy from subject-level generalization.""",
            0.83,
            522,
            132,
        )

    verdict = _call(
        "openai",
        "recorded-demo",
        """# MAGI verdict — REVISE

**Critical defect:** subject leakage in the validation design.

The current 94% accuracy does not establish generalization to unseen participants because correlated windows from the same individuals may occur in both training and test data.

## Required repair

Use participant-grouped splitting before model evaluation and keep every data-dependent preprocessing step inside the training partition.

## Verification

Repeat the experiment with LOSO or another participant-grouped protocol and report performance with uncertainty across held-out participants.

**Decision:** the scientific conclusion should be revised before the result is used as evidence of model generalization.""",
        0.94,
        611,
        145,
    )

    scorecard = None
    if score:
        scorecard = {
            "parsed": True,
            "global_confidence": 96,
            "consensus_level": 98,
            "agents": [
                {
                    "agent": "MELCHIOR",
                    "technical_rigor": 95,
                    "relevance": 96,
                    "uncertainty_handling": 91,
                    "practical_value": 93,
                    "decision_weight": 94,
                    "rationale": "Correctly identified the validation-unit mismatch and proposed grouped evaluation.",
                },
                {
                    "agent": "BALTHASAR",
                    "technical_rigor": 97,
                    "relevance": 96,
                    "uncertainty_handling": 95,
                    "practical_value": 88,
                    "decision_weight": 95,
                    "rationale": "Explicitly connected participant dependence to invalid generalization claims.",
                },
                {
                    "agent": "CASPER",
                    "technical_rigor": 91,
                    "relevance": 94,
                    "uncertainty_handling": 90,
                    "practical_value": 97,
                    "decision_weight": 91,
                    "rationale": "Translated the defect into concrete corrective experiments.",
                },
            ],
            "strongest_contribution": (
                "Identification of subject-level leakage caused by random window splitting."
            ),
            "main_correction": (
                "Evaluate with participant-grouped splits and fold-local preprocessing."
            ),
            "residual_uncertainty": (
                "The magnitude of performance inflation cannot be known until the corrected experiment is run."
            ),
            "evaluator": _call(
                "openai",
                "recorded-demo",
                "Recorded scorecard evaluation.",
                0.42,
                260,
                54,
            ),
        }

    return {
        "run_id": "demo-eeg-subject-leakage",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "question": DEMO_CASES["eeg_subject_leakage"]["question"],
        "critique_enabled": critique,
        "scoring_enabled": score,
        "auditor_enabled": auditor,
        "agents": agents,
        "auditor": auditor_result,
        "verdict": verdict,
        "scorecard": scorecard,
        "wall_time_seconds": 4.7 if critique else 3.4,
        "demo_mode": True,
        "demo_case": "eeg_subject_leakage",
        "demo_notice": "Prerecorded demonstration. No model API calls were made.",
    }


def _imbalanced_accuracy_run(
    critique: bool,
    score: bool,
    auditor: bool,
) -> dict[str, Any]:
    run = _eeg_leakage_run(
        critique=critique,
        score=score,
        auditor=auditor,
    )

    run["run_id"] = "demo-imbalanced-accuracy"
    run["question"] = DEMO_CASES["imbalanced_accuracy"]["question"]
    run["demo_case"] = "imbalanced_accuracy"

    run["agents"][0]["initial"]["text"] = """### Primary finding

Accuracy is misleading for this dataset.

A classifier that always predicts the majority class obtains 950 / 1000 = **95% accuracy while detecting zero positive cases**.

The reported metric therefore hides complete failure on the clinically rarer class.

Report the confusion matrix and class-sensitive metrics such as sensitivity/recall, specificity, precision, balanced accuracy, and PR-AUC when appropriate."""

    run["agents"][1]["initial"]["text"] = """### Scientific review

The result demonstrates the base-rate accuracy paradox.

Because prevalence is 95% negative, raw accuracy can be maximized without learning a useful decision boundary. The evaluation must explicitly quantify performance for the positive class.

For a biomedical application, the consequences of false negatives and false positives should determine which operating-point metrics are primary."""

    run["agents"][2]["initial"]["text"] = """### Practical assessment

The current classifier has no utility for identifying positive cases.

Immediate checks:

- confusion matrix;
- positive-class recall;
- precision;
- balanced accuracy;
- PR curve;
- comparison against the majority-class baseline.

Model selection should not use raw accuracy as the sole objective on this class distribution."""

    run["verdict"]["text"] = """# MAGI verdict — BLOCK

The 95% accuracy is a **majority-class baseline**, not evidence of useful classification.

The model predicts every positive sample incorrectly, so positive-class sensitivity is 0%.

## Required repair

Evaluate class-sensitive metrics and compare against explicit baselines. Select the primary metric according to the intended biomedical use and error costs.

**Decision:** the performance claim should not be accepted in its current form."""

    if run["auditor"]:
        run["auditor"]["text"] = """### Independent audit

The arithmetic confirms the defect: 950 negatives / 1000 total samples = 95%.

Therefore a constant-negative classifier exactly reproduces the reported accuracy while having zero sensitivity.

The performance claim is not informative unless minority-class behavior and a suitable baseline are reported."""

    if run["scorecard"]:
        run["scorecard"]["global_confidence"] = 99
        run["scorecard"]["consensus_level"] = 100

        run["scorecard"]["agents"] = [
            {
                "agent": "MELCHIOR",
                "technical_rigor": 98,
                "relevance": 99,
                "uncertainty_handling": 93,
                "practical_value": 94,
                "decision_weight": 97,
                "rationale": (
                    "Correctly showed that 95% accuracy is exactly reproduced "
                    "by the trivial majority-class classifier."
                ),
            },
            {
                "agent": "BALTHASAR",
                "technical_rigor": 97,
                "relevance": 98,
                "uncertainty_handling": 96,
                "practical_value": 91,
                "decision_weight": 96,
                "rationale": (
                    "Identified the base-rate accuracy paradox and connected "
                    "metric choice to biomedical error consequences."
                ),
            },
            {
                "agent": "CASPER",
                "technical_rigor": 93,
                "relevance": 97,
                "uncertainty_handling": 92,
                "practical_value": 99,
                "decision_weight": 94,
                "rationale": (
                    "Converted the metric failure into concrete checks including "
                    "recall, precision, balanced accuracy, PR analysis, and baselines."
                ),
            },
        ]

        run["scorecard"]["strongest_contribution"] = (
            "Recognition that 95% accuracy equals the trivial majority-class baseline."
        )
        run["scorecard"]["main_correction"] = (
            "Use class-sensitive metrics and explicit baseline comparison."
        )
        run["scorecard"]["residual_uncertainty"] = (
            "The appropriate operating point depends on the application-specific cost of errors."
        )

    return run


def build_demo_run(
    case_id: str,
    *,
    critique: bool,
    score: bool,
    auditor: bool,
) -> dict[str, Any]:
    if case_id == "eeg_subject_leakage":
        return _eeg_leakage_run(critique, score, auditor)

    if case_id == "imbalanced_accuracy":
        return _imbalanced_accuracy_run(critique, score, auditor)

    raise ValueError(f"Unknown demo case: {case_id}")