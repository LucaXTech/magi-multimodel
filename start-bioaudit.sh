#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python -m bioaudit.web --host 0.0.0.0 --port 8081
