from __future__ import annotations

from .protocol import write_lock
from .validate_objective import validate


def main() -> int:
    errors = validate()
    if errors:
        print("Impossibile congelare: dataset non valido")
        for error in errors:
            print("-", error)
        return 1
    payload = write_lock()
    print("Protocollo congelato.")
    print("Versione:", payload["protocol_version"])
    print("SHA256:", payload["dataset_sha256"])
    print("Casi test:", len(payload["test_case_ids"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
