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
