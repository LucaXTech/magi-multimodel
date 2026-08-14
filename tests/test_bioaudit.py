from pathlib import Path

from bioaudit.orchestrator import BioAuditOrchestrator, parse_report
from magi.config import Settings
from magi.providers import build_providers


def test_parse_report() -> None:
    payload, error = parse_report('{"verdict":"PASS","summary":"ok","critical_issues":[],"moderate_issues":[],"strengths":[],"missing_information":[],"disagreements_resolved":[],"next_actions":[],"internal_confidence":80}')
    assert error is None
    assert payload is not None
    assert payload["verdict"] == "PASS"


def test_mock_bioaudit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RUNS_DIR", str(tmp_path / "runs"))
    settings = Settings.from_env()
    providers = build_providers(settings, mock=True)
    result, directory = BioAuditOrchestrator(settings, providers).run(
        "Standardizziamo tutto il dataset e poi dividiamo casualmente finestre sovrapposte tra train e test.",
        profile="eeg_ml",
        output_root=tmp_path / "bioaudit",
    )
    assert result["report"]["verdict"] == "REVISE"
    assert (directory / "report.md").exists()
