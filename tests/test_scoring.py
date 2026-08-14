from benchmark.run_benchmark import score_text


def test_all_groups_match() -> None:
    result = score_text(
        "C'è subject leakage. Usa LOSO e fai fit solo sul training fold.",
        [["subject leakage"], ["loso"], ["training fold"]],
        ["random split va bene"],
    )
    assert result["score"] == 1.0


def test_red_flag_penalty() -> None:
    result = score_text(
        "Lo split casuale va bene.",
        [["subject leakage"]],
        ["lo split casuale va bene"],
    )
    assert result["score"] == 0.0
