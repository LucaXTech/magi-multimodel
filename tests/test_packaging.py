from __future__ import annotations

import importlib.metadata
from pathlib import Path


EXPECTED_SCRIPTS = {
    "magi-web": "magi.web:main",
    "bioaudit-web": "bioaudit.web:main",
    "magi-benchmark-validate": "benchmark.validate_objective:main",
}


def test_installed_distribution_version_matches_version_file() -> None:
    installed = importlib.metadata.version("magi-multimodel")
    expected = Path("VERSION").read_text(encoding="utf-8").strip()

    assert installed == expected


def test_console_entry_points_are_registered() -> None:
    scripts = {
        entry.name: entry.value
        for entry in importlib.metadata.entry_points(group="console_scripts")
        if entry.name in EXPECTED_SCRIPTS
    }

    assert scripts == EXPECTED_SCRIPTS


def test_console_entry_points_are_loadable() -> None:
    entries = {
        entry.name: entry
        for entry in importlib.metadata.entry_points(group="console_scripts")
        if entry.name in EXPECTED_SCRIPTS
    }

    assert set(entries) == set(EXPECTED_SCRIPTS)

    for entry in entries.values():
        target = entry.load()
        assert callable(target)