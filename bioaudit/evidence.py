from __future__ import annotations

import hashlib
from copy import deepcopy
from typing import Any


REPORT_SCHEMA_VERSION = "bioaudit.report.v2"
EVIDENCE_PROTOCOL_VERSION = "bioaudit.evidence.v1"

_MISSING_SENTINELS = {
    "",
    "not specified",
    "not provided",
    "none",
    "n/a",
    "unknown",
}


def source_metadata(text: str, source_name: str) -> dict[str, Any]:
    return {
        "name": source_name,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "length_chars": len(text),
        "line_count": text.count("\n") + 1,
    }


def _utf16_length(text: str) -> int:
    """Return the number of UTF-16 code units used by browser text controls."""
    return len(text.encode("utf-16-le")) // 2


def _stable_finding_id(
    severity: str,
    title: str,
    evidence_candidate: str | None,
) -> str:
    material = "\0".join(
        (
            severity.strip().lower(),
            title.strip(),
            (evidence_candidate or "").strip(),
        )
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:10].upper()
    prefix = "C" if severity == "critical" else "M"
    return f"BA-{prefix}-{digest}"


def locate_evidence(
    source_text: str,
    evidence_candidate: Any,
) -> dict[str, Any]:
    """
    Link a model-provided evidence quote to the submitted source.

    Only an exact contiguous substring is accepted as linked evidence.
    Paraphrases and invented quotations are explicitly marked missing.
    """
    candidate = (
        evidence_candidate.strip()
        if isinstance(evidence_candidate, str)
        else ""
    )

    if candidate.lower() in _MISSING_SENTINELS:
        return {
            "status": "evidence_missing",
            "reason": "not_provided",
            "quote": None,
            "candidate_text": candidate or None,
            "start_char": None,
            "end_char": None,
            "start_utf16": None,
            "end_utf16": None,
            "line_start": None,
            "line_end": None,
            "match_count": 0,
        }

    start = source_text.find(candidate)

    if start < 0:
        return {
            "status": "evidence_missing",
            "reason": "not_exact_match",
            "quote": None,
            "candidate_text": candidate,
            "start_char": None,
            "end_char": None,
            "start_utf16": None,
            "end_utf16": None,
            "line_start": None,
            "line_end": None,
            "match_count": 0,
        }

    end = start + len(candidate)

    return {
        "status": "linked",
        "reason": None,
        "quote": candidate,
        "candidate_text": None,
        "start_char": start,
        "end_char": end,
        "start_utf16": _utf16_length(source_text[:start]),
        "end_utf16": _utf16_length(source_text[:end]),
        "line_start": source_text.count("\n", 0, start) + 1,
        "line_end": source_text.count("\n", 0, end) + 1,
        "match_count": source_text.count(candidate),
    }


def link_report_evidence(
    report: dict[str, Any],
    source_text: str,
) -> dict[str, Any]:
    """
    Add stable finding IDs and deterministic evidence links.

    A finding can never silently claim a source citation that cannot be
    reproduced from the submitted input.
    """
    linked_report = deepcopy(report)

    linked_count = 0
    missing_count = 0
    used_ids: dict[str, int] = {}

    for severity, key in (
        ("critical", "critical_issues"),
        ("moderate", "moderate_issues"),
    ):
        normalized: list[dict[str, Any]] = []

        for raw_item in linked_report.get(key, []):
            if isinstance(raw_item, dict):
                item = dict(raw_item)
            else:
                item = {
                    "title": str(raw_item),
                    "evidence_from_input": None,
                    "why_it_matters": "",
                    "recommended_fix": "",
                    "verification": "",
                }

            title = str(item.get("title") or "Untitled finding")
            candidate = item.get("evidence_from_input")
            evidence = locate_evidence(source_text, candidate)

            finding_id = _stable_finding_id(
                severity,
                title,
                candidate if isinstance(candidate, str) else None,
            )

            duplicate_number = used_ids.get(finding_id, 0) + 1
            used_ids[finding_id] = duplicate_number

            if duplicate_number > 1:
                finding_id = f"{finding_id}-{duplicate_number}"

            item["finding_id"] = finding_id
            item["severity"] = severity
            item["evidence"] = evidence

            if evidence["status"] == "linked":
                item["evidence_from_input"] = evidence["quote"]
                item.pop("evidence_candidate", None)
                linked_count += 1
            else:
                # Never preserve an unverified string as if it were a citation.
                item["evidence_from_input"] = None
                if evidence.get("candidate_text"):
                    item["evidence_candidate"] = evidence["candidate_text"]
                missing_count += 1

            normalized.append(item)

        linked_report[key] = normalized

    linked_report["schema_version"] = REPORT_SCHEMA_VERSION
    linked_report["evidence_integrity"] = {
        "protocol": EVIDENCE_PROTOCOL_VERSION,
        "linked_findings": linked_count,
        "evidence_missing_findings": missing_count,
        "total_findings": linked_count + missing_count,
    }

    return linked_report