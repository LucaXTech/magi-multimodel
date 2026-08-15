from __future__ import annotations

import json
from pathlib import Path

from .types import MagiRun


#       /\_/\
#      ( -.- )  The archivist keeps every run traceable.
#       > ^ <
def save_run(run: MagiRun, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{run.run_id}.json"
    path.write_text(
        json.dumps(run.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
