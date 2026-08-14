from __future__ import annotations

from typing import Any


DEMO_CASES = {
    "eeg_subject_leakage": {
        "title": "EEG subject leakage",
        "profile": "eeg_ml",
        "text": (
            "EEG data were collected from 18 participants. Continuous recordings "
            "were segmented into 2-second windows. All windows were pooled and "
            "randomly split 80/20 into training and test sets. Standardization was "
            "computed on the full dataset before splitting. A classifier achieved "
            "94% test accuracy."
        ),
    },
    "imbalanced_classifier": {
        "title": "Imbalanced biomedical classifier",
        "profile": "general_ml",
        "text": (
            "The dataset contains 950 negative and 50 positive samples. "
            "The classifier predicts every sample as negative and achieves "
            "95% accuracy. Accuracy is reported as the primary performance metric."
        ),
    },
}


def list_demo_cases() -> list[dict[str, str]]:
    return [
        {
            "id": case_id,
            "title": case["title"],
            "profile": case["profile"],
            "text": case["text"],
        }
        for case_id, case in DEMO_CASES.items()
    ]


def build_demo_report(case_id: str) -> dict[str, Any]:
    if case_id == "eeg_subject_leakage":
        return {
            "verdict": "BLOCK",
            "summary": (
                "The reported performance is not a valid estimate of "
                "generalization to unseen participants."
            ),
            "internal_confidence": 98,
            "critical_issues": [
                {
                    "title": "Participant leakage across train and test sets",
                    "evidence_from_input": (
                        "All windows were pooled and randomly split 80/20 "
                        "into training and test sets."
                    ),
                    "why_it_matters": (
                        "Windows from the same participant are correlated. "
                        "The classifier can exploit subject-specific structure "
                        "instead of learning a participant-independent signal."
                    ),
                    "recommended_fix": (
                        "Split data by participant using GroupKFold, LOSO, "
                        "or another participant-independent validation protocol."
                    ),
                    "verification": (
                        "Confirm that no participant identifier occurs in more "
                        "than one partition and recompute performance."
                    ),
                },
                {
                    "title": "Preprocessing fitted on held-out data",
                    "evidence_from_input": (
                        "Standardization was computed on the full dataset before splitting."
                    ),
                    "why_it_matters": (
                        "Statistics from the test set leak into the training pipeline "
                        "and bias the evaluation."
                    ),
                    "recommended_fix": (
                        "Fit standardization only on each training fold and apply "
                        "the learned parameters to its validation/test fold."
                    ),
                    "verification": (
                        "Inspect the pipeline and confirm every data-dependent transform "
                        "is fitted inside the training partition."
                    ),
                },
            ],
            "moderate_issues": [
                {
                    "title": "Single accuracy value is insufficient",
                    "evidence_from_input": "A classifier achieved 94% test accuracy.",
                    "why_it_matters": (
                        "A single aggregate metric does not describe variability "
                        "across held-out participants."
                    ),
                    "recommended_fix": (
                        "Report participant-level performance and uncertainty, "
                        "plus task-appropriate complementary metrics."
                    ),
                    "verification": (
                        "Check that the corrected evaluation reports dispersion "
                        "across independent held-out subjects."
                    ),
                }
            ],
            "strengths": [
                "The dataset contains multiple independent participants.",
                "The study reports an explicit held-out performance value.",
            ],
            "missing_information": [
                "Class balance and target definition.",
                "Feature extraction and model-selection procedure.",
                "Whether artifact rejection thresholds were fitted globally.",
            ],
            "next_actions": [
                "Replace random window splitting with participant-grouped validation.",
                "Move standardization inside each training fold.",
                "Rerun the experiment and quantify the performance change.",
            ],
        }

    if case_id == "imbalanced_classifier":
        return {
            "verdict": "BLOCK",
            "summary": (
                "The reported 95% accuracy is identical to the trivial "
                "majority-class baseline."
            ),
            "internal_confidence": 99,
            "critical_issues": [
                {
                    "title": "Accuracy hides complete positive-class failure",
                    "evidence_from_input": (
                        "The classifier predicts every sample as negative "
                        "and achieves 95% accuracy."
                    ),
                    "why_it_matters": (
                        "The classifier has 0% sensitivity for the positive class "
                        "despite apparently high overall accuracy."
                    ),
                    "recommended_fix": (
                        "Report the confusion matrix and class-sensitive metrics "
                        "such as recall, precision, specificity, balanced accuracy, "
                        "and PR-AUC where appropriate."
                    ),
                    "verification": (
                        "Verify that the selected primary metric distinguishes "
                        "the trained model from the majority-class baseline."
                    ),
                }
            ],
            "moderate_issues": [],
            "strengths": [
                "The class prevalence is explicitly reported.",
            ],
            "missing_information": [
                "Application-specific costs of false negatives and false positives.",
                "Decision threshold and calibration strategy.",
            ],
            "next_actions": [
                "Compute the confusion matrix.",
                "Choose a metric aligned with the biomedical objective.",
                "Compare against an explicit majority-class baseline.",
            ],
        }

    raise ValueError(f"Unknown demo case: {case_id}")