from benchmark.scoring import score_response


def _case(critical_pattern: str) -> dict:
    return {
        "must_include": [{"name": "x", "patterns": ["leakage"]}],
        "critical_errors": [{"name": "bad", "patterns": [critical_pattern]}],
    }


def test_negated_sufficient_is_not_critical() -> None:
    result = score_response(
        "C'è leakage. Le etichette bilanciate non sono sufficienti.",
        _case(r"bilanciat.*sufficien"),
    )
    assert not result["critical_error"]


def test_positive_sufficient_is_critical() -> None:
    result = score_response(
        "C'è leakage, ma le etichette bilanciate sono sufficienti.",
        _case(r"bilanciat.*sufficien"),
    )
    assert result["critical_error"]


def test_not_correct_global_scaling_is_not_critical() -> None:
    result = score_response(
        "Non è corretto usare l'intero dataset: causa leakage.",
        _case(r"corretto.*intero dataset"),
    )
    assert not result["critical_error"]


def test_correct_global_scaling_is_critical() -> None:
    result = score_response(
        "È corretto usare l'intero dataset; non c'è leakage.",
        _case(r"corretto.*intero dataset"),
    )
    assert result["critical_error"]
