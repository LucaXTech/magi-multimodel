from benchmark.objective_scoring import parse_answer, score_payload


def test_mcq_exact() -> None:
    case = {"type": "mcq", "answer": "B"}
    payload, error = parse_answer('{"answer":"B","confidence":80,"rationale":"ok"}')
    assert error is None
    scored = score_payload(payload, case)
    assert scored["correct"] is True
    assert scored["score"] == 100.0
    assert scored["brier"] == 0.04


def test_multiselect_partial() -> None:
    case = {"type": "multi_select", "answer": ["A", "B", "D"]}
    payload, _ = parse_answer('{"answer":["A","D"],"confidence":60}')
    scored = score_payload(payload, case)
    assert scored["correct"] is False
    assert scored["score"] == 66.6667


def test_numeric_tolerance() -> None:
    case = {"type": "numeric", "answer": 0.8, "tolerance_abs": 0.01}
    payload, _ = parse_answer('{"answer":0.805,"confidence":90}')
    scored = score_payload(payload, case)
    assert scored["correct"] is True
