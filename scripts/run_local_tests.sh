#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

PYTHON=${PYTHON:-python3}
VENV=.venv

if [[ ! -d "$VENV" ]]; then
  echo "[setup] creating venv"
  "$PYTHON" -m venv "$VENV"
  "$VENV/bin/pip" install -U pip
fi

echo "[setup] installing dev deps"
"$VENV/bin/pip" install -e . -r requirements-dev.txt

echo "[test] running pytest"
"$VENV/bin/pytest" -q

