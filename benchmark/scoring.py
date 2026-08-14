from __future__ import annotations

import re
import unicodedata
from typing import Any


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text).strip()


# Negazioni usate per evitare che una red flag positiva venga rilevata dentro
# frasi che la rifiutano, per esempio: "il bilanciamento NON è sufficiente".
_NEGATION_RE = re.compile(
    r"\b(?:non|mai|fals[oa]|errat[oa]|sbagliat[oa]|scorrett[oa]|"
    r"insufficiente|inadeguat[oa])\b",
    flags=re.IGNORECASE,
)

# Alcune red flag sono esse stesse formulate in negativo (es. "non cambia",
# "nessun problema"). In questi casi la negazione fa parte dell'errore e non
# deve neutralizzare il match.
_PATTERN_ENCODES_NEGATIVE_CLAIM_RE = re.compile(
    r"(?:\bnon\b|\bnessun|\bassenza\b|\bignorare\b|\bsenza\b)",
    flags=re.IGNORECASE,
)


def _evidence(text: str, start: int, end: int, radius: int = 70) -> str:
    lo = max(0, start - radius)
    hi = min(len(text), end + radius)
    return text[lo:hi].strip()


def _match_concept(text: str, patterns: list[str]) -> tuple[bool, str | None, str | None]:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return True, pattern, _evidence(text, match.start(), match.end())
    return False, None, None


def _match_critical(text: str, patterns: list[str]) -> tuple[bool, str | None, str | None]:
    """High-precision critical-error matching with basic negation handling.

    This remains a deterministic proxy, not a semantic judge. It is designed to
    prefer false negatives over false accusations of a critical error.
    """
    for pattern in patterns:
        explicit_negative_claim = bool(_PATTERN_ENCODES_NEGATIVE_CLAIM_RE.search(pattern))
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            if not explicit_negative_claim:
                preceding = text[max(0, match.start() - 55):match.start()]
                matched_text = text[match.start():match.end()]
                if _NEGATION_RE.search(preceding) or _NEGATION_RE.search(matched_text):
                    continue
            return True, pattern, _evidence(text, match.start(), match.end())
    return False, None, None


def score_response(text: str, case: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize(text)

    concepts = []
    for group in case.get("must_include", []):
        matched, pattern, evidence = _match_concept(normalized, group.get("patterns", []))
        concepts.append({
            "name": group.get("name", "concept"),
            "matched": matched,
            "matched_pattern": pattern,
            "evidence": evidence,
        })

    errors = []
    for group in case.get("critical_errors", []):
        matched, pattern, evidence = _match_critical(normalized, group.get("patterns", []))
        errors.append({
            "name": group.get("name", "critical_error"),
            "matched": matched,
            "matched_pattern": pattern,
            "evidence": evidence,
        })

    matched_count = sum(int(item["matched"]) for item in concepts)
    total = max(len(concepts), 1)
    concept_recall = matched_count / total
    critical_hits = sum(int(item["matched"]) for item in errors)

    # Proxy di copertura della rubrica, non accuratezza scientifica.
    score = max(0.0, min(100.0, 100.0 * concept_recall - 40.0 * critical_hits))
    auto_pass = score >= 80.0 and critical_hits == 0
    return {
        "score": round(score, 2),
        "concept_recall": round(concept_recall, 4),
        "matched_concepts": matched_count,
        "total_concepts": len(concepts),
        "critical_error": critical_hits > 0,
        "critical_error_count": critical_hits,
        # Backward compatibility. In reports this should be read as auto-pass,
        # not as human-verified correctness.
        "correct": auto_pass,
        "auto_pass": auto_pass,
        "concept_details": concepts,
        "critical_error_details": errors,
    }
