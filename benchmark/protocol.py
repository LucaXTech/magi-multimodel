from __future__ import annotations

import hashlib
import json
import random
import re
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

CASES_PATH = Path(__file__).with_name("objective_cases_v3.jsonl")
LOCK_PATH = Path(__file__).with_name("protocol_lock_v3.json")
PROTOCOL_VERSION = "objective_v3"
VALID_SPLITS = {"dev", "test"}
VALID_TYPES = {"mcq", "multi_select", "numeric"}
VALID_DIFFICULTIES = {"intermediate", "hard"}
OPTION_LABELS = ("A", "B", "C", "D")


def load_cases(path: Path = CASES_PATH) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalized_question(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def sha256_file(path: Path = CASES_PATH) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_case_ids(cases: Iterable[dict[str, Any]] | None = None) -> list[str]:
    items = list(cases) if cases is not None else load_cases()
    return sorted(str(case["id"]) for case in items if case.get("split") == "test")


def write_lock(path: Path = LOCK_PATH) -> dict[str, Any]:
    cases = load_cases()
    payload = {
        "protocol_version": PROTOCOL_VERSION,
        "dataset_sha256": sha256_file(),
        "test_case_ids": test_case_ids(cases),
        "primary_endpoint": "exact_accuracy",
        "secondary_endpoints": [
            "critical_error_rate",
            "brier_score",
            "latency_seconds",
            "estimated_cost_per_correct",
        ],
        "selection_rule": "test set fixed before real test runs",
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def verify_lock(path: Path = LOCK_PATH) -> tuple[bool, str]:
    if not path.exists():
        return False, f"Protocol lock mancante: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"Protocol lock non leggibile: {type(exc).__name__}: {exc}"
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        return False, "Versione del protocol lock non coerente."
    current_hash = sha256_file()
    if payload.get("dataset_sha256") != current_hash:
        return False, "Il dataset è cambiato dopo il congelamento del protocollo."
    if payload.get("test_case_ids") != test_case_ids():
        return False, "Gli ID del test set non corrispondono al protocol lock."
    return True, "Protocol lock valido."


def stratified_select(
    cases: list[dict[str, Any]],
    limit: int | None,
    seed: int,
) -> list[dict[str, Any]]:
    """Round-robin by category after deterministic within-category shuffling.

    This prevents ``--limit`` from selecting a contiguous topic block while keeping
    the selection reproducible from the manifest seed.
    """
    if limit is None or limit >= len(cases):
        return list(cases)
    rng = random.Random(seed)
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        buckets[str(case["category"])].append(case)
    for category, items in buckets.items():
        # Sort first so results do not depend on physical JSONL order.
        items.sort(key=lambda item: str(item["id"]))
        rng.shuffle(items)
    categories = sorted(buckets)
    rng.shuffle(categories)
    selected: list[dict[str, Any]] = []
    cursor = 0
    while len(selected) < limit:
        made_progress = False
        for category in categories:
            items = buckets[category]
            if cursor < len(items):
                selected.append(items[cursor])
                made_progress = True
                if len(selected) == limit:
                    break
        if not made_progress:
            break
        cursor += 1
    return selected


def select_cases(
    *,
    split: str,
    limit: int | None,
    seed: int,
    categories: set[str] | None = None,
    difficulties: set[str] | None = None,
    case_ids: set[str] | None = None,
    selection: str = "stratified",
) -> list[dict[str, Any]]:
    cases = [case for case in load_cases() if split == "all" or case["split"] == split]
    if categories:
        cases = [case for case in cases if case["category"] in categories]
    if difficulties:
        cases = [case for case in cases if case["difficulty"] in difficulties]
    if case_ids:
        by_id = {case["id"]: case for case in cases}
        missing = case_ids - set(by_id)
        if missing:
            raise ValueError("Case ID non trovati nello split selezionato: " + ", ".join(sorted(missing)))
        # Preserve explicit user order only if the caller supplied an ordered iterable;
        # here sets are sorted for reproducibility.
        return [by_id[case_id] for case_id in sorted(case_ids)]
    if selection == "ordered":
        return cases if limit is None else cases[:limit]
    if selection != "stratified":
        raise ValueError(f"Strategia di selezione non valida: {selection}")
    return stratified_select(cases, limit, seed)


def permute_case_options(case: dict[str, Any], seed: int) -> tuple[dict[str, Any], dict[str, str]]:
    """Permute option texts and remap the answer using one reproducible seed.

    The same presented case must be sent to every system for a given case/repeat.
    Mapping is ``new_label -> original_label`` and is stored in the result manifest.
    """
    if case["type"] == "numeric":
        return deepcopy(case), {}
    original_options = dict(case["options"])
    labels = list(original_options)
    if len(labels) != 4 or set(labels) != set(OPTION_LABELS):
        raise ValueError(f"{case['id']}: le opzioni devono essere esattamente A-D")
    original_labels = labels[:]
    random.Random(seed).shuffle(original_labels)
    new_options = {
        new_label: original_options[old_label]
        for new_label, old_label in zip(OPTION_LABELS, original_labels, strict=True)
    }
    old_to_new = {
        old_label: new_label
        for new_label, old_label in zip(OPTION_LABELS, original_labels, strict=True)
    }
    presented = deepcopy(case)
    presented["options"] = new_options
    if case["type"] == "multi_select":
        presented["answer"] = sorted(old_to_new[str(label)] for label in case["answer"])
    else:
        presented["answer"] = old_to_new[str(case["answer"])]
    mapping = {
        new_label: old_label
        for new_label, old_label in zip(OPTION_LABELS, original_labels, strict=True)
    }
    return presented, mapping
