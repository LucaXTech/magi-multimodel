from magi.i18n import (
    CATALOGS,
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    frontend_payload,
    normalize_language,
    translate,
    validate_catalogs,
)


def test_supported_languages_and_default():
    assert DEFAULT_LANGUAGE == "en"
    assert SUPPORTED_LANGUAGES == ("en", "it")


def test_catalog_keys_match_exactly():
    validate_catalogs()
    reference = set(CATALOGS[DEFAULT_LANGUAGE])
    assert reference
    assert set(CATALOGS["it"]) == reference


def test_unknown_language_falls_back_to_english():
    assert normalize_language(None) == "en"
    assert normalize_language("de") == "en"
    assert translate("magi.run.start", "de") == "START DELIBERATION"


def test_core_labels_are_translated():
    assert translate("magi.run.start", "en") == "START DELIBERATION"
    assert translate("magi.run.start", "it") == "AVVIA DELIBERAZIONE"
    assert translate("bioaudit.run.start", "en") == "START AUDIT"
    assert translate("bioaudit.run.start", "it") == "AVVIA AUDIT"


def test_format_values_are_interpolated():
    assert translate("magi.judge.live", "en", provider="OPENAI") == (
        "JUDGE: OPENAI | live only if selected"
    )
    assert translate("magi.judge.live", "it", provider="OPENAI") == (
        "JUDGE: OPENAI | reale solo se selezionato"
    )


def test_frontend_payload_is_complete():
    payload = frontend_payload()
    assert payload["default_language"] == "en"
    assert payload["supported_languages"] == ["en", "it"]
    assert payload["storage_key"] == "magi.ui.language"
    assert payload["catalogs"] == CATALOGS


def test_magi_web_exposes_frontend_i18n_payload():
    import magi.web as magi_web

    payload = magi_web.i18n_config()

    assert payload["default_language"] == "en"
    assert payload["supported_languages"] == ["en", "it"]
    assert payload["storage_key"] == "magi.ui.language"
    assert payload["catalogs"] == CATALOGS


def test_magi_html_is_english_first_with_language_switch():
    from pathlib import Path

    html = Path("magi/static/index.html").read_text(encoding="utf-8")

    assert '<html lang="en">' in html
    assert 'id="languageSelect"' in html
    assert 'data-i18n="magi.run.start"' in html
    assert "START DELIBERATION" in html


def test_magi_frontend_persists_and_applies_language():
    from pathlib import Path

    script = Path("magi/static/app.js").read_text(encoding="utf-8")

    assert "localStorage.setItem(i18n.storage_key, language)" in script
    assert "document.documentElement.lang = language" in script
    assert 'fetch("/api/i18n")' in script
    assert "renderRun(lastRenderedRun, false)" in script


def test_dynamic_magi_translation_keys_have_parity():
    keys = {
        "magi.system.standby",
        "magi.system.deliberating",
        "magi.system.complete",
        "magi.system.config_error",
        "magi.demo.static_fixture",
        "magi.demo.replaying",
        "magi.demo.completed",
    }

    for key in keys:
        assert key in CATALOGS["en"]
        assert key in CATALOGS["it"]


def test_bioaudit_web_exposes_frontend_i18n_payload():
    import bioaudit.web as bioaudit_web

    payload = bioaudit_web.i18n_config()

    assert payload["default_language"] == "en"
    assert payload["supported_languages"] == ["en", "it"]
    assert payload["storage_key"] == "magi.ui.language"
    assert payload["catalogs"] == CATALOGS


def test_bioaudit_html_is_english_first_with_language_switch():
    import bioaudit.web as bioaudit_web

    html = bioaudit_web.HTML

    assert '<html lang="en">' in html
    assert 'id="languageSelect"' in html
    assert 'data-i18n="bioaudit.run.start"' in html
    assert "START AUDIT" in html


def test_bioaudit_frontend_persists_language():
    import bioaudit.web as bioaudit_web

    html = bioaudit_web.HTML

    assert "localStorage.setItem(i18n.storage_key, language)" in html
    assert "document.documentElement.lang = language" in html
    assert 'api("/api/i18n")' in html


def test_bioaudit_job_not_found_is_localized():
    import pytest
    import bioaudit.web as bioaudit_web
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        bioaudit_web.get_job("definitely-missing", language="it")

    assert exc.value.status_code == 404
    assert exc.value.detail == "Job non trovato."


def test_demo_case_titles_are_localized():
    keys = {
        "demo.case.eeg_subject_leakage",
        "demo.case.imbalanced_accuracy",
        "demo.case.imbalanced_classifier",
    }

    for key in keys:
        assert key in CATALOGS["en"]
        assert key in CATALOGS["it"]
        assert CATALOGS["en"][key] != CATALOGS["it"][key]


def test_bioaudit_demo_polish():
    import bioaudit.web as bioaudit_web

    html = bioaudit_web.HTML

    assert "PROVIDER_LABELS" in html
    assert 't("bioaudit.demo.source")' in html
    assert "? ${esc(path)}" not in html


def test_magi_demo_case_titles_use_i18n():
    from pathlib import Path

    script = Path("magi/static/app.js").read_text(encoding="utf-8")

    assert 't(`demo.case.${item.id}`)' in script
    assert 't(`demo.case.${option.value}`)' in script
