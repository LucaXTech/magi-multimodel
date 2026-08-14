from __future__ import annotations
import json
from pathlib import Path

PATH=Path(__file__).with_name("cases_v1.jsonl")

def main() -> int:
    ids=set(); count=0
    for lineno,line in enumerate(PATH.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        case=json.loads(line); count+=1
        required={"id","category","difficulty","question","must_include","critical_errors","reference_answer"}
        missing=required-set(case)
        if missing: raise ValueError(f"riga {lineno}: campi mancanti {sorted(missing)}")
        if case["id"] in ids: raise ValueError(f"ID duplicato: {case['id']}")
        ids.add(case["id"])
        if not case["must_include"]: raise ValueError(f"{case['id']}: must_include vuoto")
    print(f"Validi: {count} casi")
    return 0

if __name__ == "__main__": raise SystemExit(main())
