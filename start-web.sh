#!/usr/bin/env bash
set -euo pipefail
./.venv/bin/python -m magi.web --host 0.0.0.0 --port 8080
