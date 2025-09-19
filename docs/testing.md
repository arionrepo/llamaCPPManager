# Testing Strategy

This document explains how tests are organized and how to run them locally.

## Goals
- Validate core logic (config, process control, logging, health checks) quickly and deterministically.
- Enable end‑to‑end checks without relying on external services.
- Prepare for GUI unit/UI tests once the SwiftUI app is scaffolded.

## Structure
- Unit tests (fast, isolated):
  - `tests/test_config.py` — YAML load/save, CRUD, validation (port uniqueness).
  - `tests/test_cli_config.py` — CLI init + config subcommands.
  - `tests/test_logs.py` — log rotation and append helper.
  - `tests/test_process.py` — argv building and signals (subprocess mocked).
  - `tests/test_health.py` — health checker using an in‑process HTTP server.
- Integration tests (opt‑in via marker):
  - Placeholder for future discovery/status with a spawned `llama-server` (behind `@pytest.mark.integration`).
  - GUI UI tests (XCUITest) will live under `gui-macos/` once the app is present.

## Running Tests
- With Makefile:
  - `make test` — all tests
  - `make test-unit` — unit tests only (excludes `@integration`)
  - `make test-integration` — only integration tests
- With script:
  - `bash scripts/run_local_tests.sh`
- With pytest directly:
  - `python3 -m venv .venv && . .venv/bin/activate && pip install -e . -r requirements-dev.txt`
  - `pytest -q`

## Test Conventions
- Environment isolation: tests inject `LLAMACPP_MANAGER_CONFIG_DIR`, `LLAMACPP_MANAGER_LOG_DIR`, and `LLAMACPP_MANAGER_PID_DIR` into a temp directory per test.
- No network dependency: connectivity tests use a local HTTP server bound to `127.0.0.1` on an ephemeral port.
- Subprocess control: process tests monkeypatch `subprocess.Popen` (or call wrappers) to avoid launching real binaries.
- Deterministic IO: YAML writes are atomic; file paths are resolved under test temp dirs.

## GUI Testing (Planned)
- Unit tests (XCTest): ViewModel parsing of `status --json`, command invocation wrapper, and state transitions.
- UI tests (XCUITest): exercise menu interactions via a debug “window mode” that mirrors menu content for accessibility.
- Local run target: `make gui-test` will invoke `xcodebuild test` for the macOS app target.

