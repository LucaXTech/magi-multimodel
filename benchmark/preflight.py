from __future__ import annotations

import argparse
from collections import Counter

from .protocol import select_cases, sha256_file, verify_lock
from .validate_objective import validate


def main() -> int:
    parser = argparse.ArgumentParser(description="Preflight MAGI Objective Benchmark v3")
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260806)
    parser.add_argument("--selection", choices=("stratified", "ordered"), default="stratified")
    parser.add_argument("--category", action="append")
    parser.add_argument("--difficulty", action="append", choices=("intermediate", "hard"))
    args = parser.parse_args()

    errors = validate()
    if errors:
        print("PRE-FLIGHT FALLITO")
        for error in errors:
            print("-", error)
        return 1
    ok, message = verify_lock()
    if args.split == "test" and not ok:
        print("PRE-FLIGHT FALLITO:", message)
        return 2
    selected = select_cases(
        split=args.split,
        limit=args.limit,
        seed=args.seed,
        categories=set(args.category or []),
        difficulties=set(args.difficulty or []),
        selection=args.selection,
    )
    print("PRE-FLIGHT OK")
    print("Protocol SHA256:", sha256_file())
    print("Lock:", message)
    print("Split:", args.split, "| Casi:", len(selected), "| Seed:", args.seed, "| Selection:", args.selection)
    print("Categorie:", dict(Counter(case["category"] for case in selected)))
    print("Tipi:", dict(Counter(case["type"] for case in selected)))
    print("Difficoltà:", dict(Counter(case["difficulty"] for case in selected)))
    print("Critical:", sum(bool(case["critical"]) for case in selected))
    print("ID selezionati:")
    for case in selected:
        print(f"- {case['id']} [{case['category']} | {case['type']} | {case['difficulty']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
