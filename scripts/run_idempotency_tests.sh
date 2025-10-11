#!/usr/bin/env bash
# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/scripts/run_idempotency_tests.sh
# Description: Dedicated script for running idempotency tests
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-11

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$ROOT_DIR"

PYTHON=${PYTHON:-python3}
VENV=.venv

echo "[idempotency] Running comprehensive idempotency test suite"

# Ensure we have the test environment
if [[ ! -d "$VENV" ]]; then
  echo "[setup] creating venv for idempotency tests"
  "$PYTHON" -m venv "$VENV"
  "$VENV/bin/pip" install -U pip
  "$VENV/bin/pip" install -e . -r requirements-dev.txt
fi

# Run dedicated idempotency tests
echo "[idempotency] Running main idempotency test suite..."
"$VENV/bin/pytest" tests/test_idempotency.py -v --tb=short

# Run idempotency tests in existing test files
echo "[idempotency] Running config idempotency tests..."
"$VENV/bin/pytest" tests/test_config.py::test_add_model_idempotent tests/test_config.py::test_save_config_idempotent -v --tb=short

# Run integration idempotency tests if they exist
echo "[idempotency] Running integration idempotency tests..."
"$VENV/bin/pytest" tests/test_idempotency.py::TestIntegrationIdempotency -v --tb=short

echo "[idempotency] ✅ All idempotency tests passed!"
echo "[idempotency] Operations are safe to retry without side effects."