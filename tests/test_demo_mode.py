from pathlib import Path

import bioaudit.web as bioaudit_web
import magi.web as magi_web

from bioaudit.demo import (
    build_demo_report as build_bioaudit_demo_report,
    list_demo_cases as list_bioaudit_demo_cases,
)
from magi.demo import (
    build_demo_run,
    list_demo_cases as list_magi_demo_cases,
)


def test_magi_demo_cases_exist():
    ids = {case["id"] for case in list_magi_demo_cases()}

    assert ids == {
        "eeg_subject_leakage",
        "imbalanced_accuracy",
    }


def test_magi_demo_run_is_structured_and_recorded():
    run = build_demo_run(
        "eeg_subject_leakage",
        critique=True,
        score=True,
        auditor=True,
    )

    assert run["demo_mode"] is True
    assert run["demo_case"] == "eeg_subject_leakage"
    assert run["verdict"]["error"] is None
    assert len(run["agents"]) == 3
    assert run["auditor"] is not None
    assert run["scorecard"]["parsed"] is True

    calls = [agent["initial"] for agent in run["agents"]]

    assert all(call["demo_recording"] is True for call in calls)
    assert all(call["model"] == "recorded-demo" for call in calls)


def test_magi_demo_worker_never_builds_real_providers(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real provider path was touched in demo mode")

    monkeypatch.setattr(magi_web, "build_providers", forbidden)

    request = magi_web.RunRequest(
        question="demo",
        critique=True,
        score=True,
        auditor=True,
        demo_case="eeg_subject_leakage",
    )

    job_id = magi_web.jobs.create(request)
    magi_web._demo_worker(job_id, request)

    job = magi_web.jobs.get(job_id)

    assert job["status"] == "completed"
    assert job["result"]["demo_mode"] is True


def test_magi_demo_config_requires_no_api_keys():
    original = magi_web.DEMO_MODE

    try:
        magi_web.DEMO_MODE = True
        config = magi_web.config()

        assert config["demo_mode"] is True
        assert config["demo_cases"]
        assert all(config["available"].values())
        assert all(
            model == "recorded-demo"
            for model in config["models"].values()
        )
    finally:
        magi_web.DEMO_MODE = original


def test_magi_demo_ui_discloses_recorded_mode():
    html = Path("magi/static/index.html").read_text(encoding="utf-8")

    assert "PRERECORDED DEMO" in html
    assert "No API calls" in html
    assert "demoCaseSelect" in html


def test_bioaudit_demo_cases_exist():
    ids = {case["id"] for case in list_bioaudit_demo_cases()}

    assert ids == {
        "eeg_subject_leakage",
        "imbalanced_classifier",
    }


def test_bioaudit_demo_report_is_structured():
    report = build_bioaudit_demo_report("eeg_subject_leakage")

    assert report["verdict"] == "BLOCK"
    assert len(report["critical_issues"]) == 2

    for issue in report["critical_issues"]:
        assert issue["title"]
        assert issue["evidence_from_input"]
        assert issue["why_it_matters"]
        assert issue["recommended_fix"]
        assert issue["verification"]


def test_bioaudit_demo_worker_never_touches_real_provider_path(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real provider path was touched in demo mode")

    original = bioaudit_web.DEMO_MODE

    monkeypatch.setattr(bioaudit_web.Settings, "from_env", forbidden)
    monkeypatch.setattr(bioaudit_web, "build_providers", forbidden)

    try:
        bioaudit_web.DEMO_MODE = True

        request = bioaudit_web.AuditRequest(
            text="This is a sufficiently long prerecorded demo input.",
            demo_case="eeg_subject_leakage",
        )

        job_id = bioaudit_web.jobs.create()
        bioaudit_web.worker(job_id, request)

        job = bioaudit_web.jobs.get(job_id)

        assert job["status"] == "completed"
        assert job["result"]["demo_mode"] is True
        assert job["result"]["report"]["verdict"] == "BLOCK"
    finally:
        bioaudit_web.DEMO_MODE = original


def test_bioaudit_demo_config_requires_no_api_keys(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Settings should not be loaded in demo mode")

    original = bioaudit_web.DEMO_MODE
    monkeypatch.setattr(bioaudit_web.Settings, "from_env", forbidden)

    try:
        bioaudit_web.DEMO_MODE = True
        config = bioaudit_web.config()

        assert config["demo_mode"] is True
        assert config["demo_cases"]
        assert all(config["available"].values())
    finally:
        bioaudit_web.DEMO_MODE = original


def test_bioaudit_demo_ui_discloses_recorded_mode():
    assert "PRERECORDED DEMO" in bioaudit_web.HTML
    assert "No model API calls are made" in bioaudit_web.HTML
    assert 'id="demoCase"' in bioaudit_web.HTML