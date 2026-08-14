from __future__ import annotations

from collections import Counter

from benchmark.analyze_objective import exact_mcnemar_p
from benchmark.protocol import (
    load_cases,
    permute_case_options,
    select_cases,
    verify_lock,
)
from benchmark.run_objective import canonical_predicted_answer
from benchmark.validate_objective import validate


def test_v3_dataset_invariants() -> None:
    assert validate() == []
    cases = load_cases()
    assert len(cases) == 48
    for split in ("dev", "test"):
        subset = [case for case in cases if case["split"] == split]
        assert len(subset) == 24
        assert Counter(case["type"] for case in subset) == {
            "mcq": 12,
            "multi_select": 6,
            "numeric": 6,
        }
        assert Counter(case["answer"] for case in subset if case["type"] == "mcq") == {
            "A": 3,
            "B": 3,
            "C": 3,
            "D": 3,
        }


def test_protocol_lock_is_valid() -> None:
    ok, _ = verify_lock()
    assert ok is True


def test_stratified_limit_is_not_prefix() -> None:
    selected = select_cases(split="dev", limit=12, seed=7, selection="stratified")
    assert len(selected) == 12
    counts = Counter(case["category"] for case in selected)
    assert set(counts.values()) == {2}
    ordered = select_cases(split="dev", limit=12, seed=7, selection="ordered")
    assert [case["id"] for case in selected] != [case["id"] for case in ordered]


def test_option_permutation_preserves_semantics_mcq() -> None:
    case = next(case for case in load_cases() if case["type"] == "mcq")
    presented, mapping = permute_case_options(case, seed=123)
    assert mapping[presented["answer"]] == case["answer"]
    assert canonical_predicted_answer(presented["answer"], "mcq", mapping) == case["answer"]


def test_option_permutation_preserves_semantics_multiselect() -> None:
    case = next(case for case in load_cases() if case["type"] == "multi_select")
    presented, mapping = permute_case_options(case, seed=456)
    canonical = canonical_predicted_answer(presented["answer"], "multi_select", mapping)
    assert canonical == sorted(case["answer"])


def test_exact_mcnemar() -> None:
    assert exact_mcnemar_p(0, 0) == 1.0
    assert exact_mcnemar_p(9, 1) < 0.05
