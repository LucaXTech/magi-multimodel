from benchmark.scoring import score_response


def test_full_match_without_error():
    case={"must_include":[{"name":"a","patterns":["subject leakage"]},{"name":"b","patterns":["groupkfold"]}],"critical_errors":[]}
    result=score_response("Subject leakage: usare GroupKFold.",case)
    assert result["score"] == 100.0
    assert result["correct"] is True


def test_critical_error_penalty():
    case={"must_include":[{"name":"a","patterns":["groupkfold"]}],"critical_errors":[{"name":"bad","patterns":["split casuale va bene"]}]}
    result=score_response("GroupKFold, ma lo split casuale va bene.",case)
    assert result["critical_error"] is True
    assert result["score"] == 60.0
    assert result["correct"] is False
