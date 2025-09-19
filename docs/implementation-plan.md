# Implementation Plan

This plan tracks milestones and concrete tasks for building llamaCPPManager.

## Milestones
- M1: CLI skeleton + config
- M2: Start/stop + logs (direct mode)
- M3: Status/health + JSON outputs
- M4: launchd autostart
- M5: Packaging (pipx) + docs
- M6: GUI (SwiftUI) stub + CLI integration

## M1 — CLI + Config
- Scaffold project: `pyproject.toml`, `src/llamacpp_manager/*`, entry point `llamacpp-manager`.
- Config module:
  - Load/save YAML at `~/Library/Application Support/llamaCPPManager/config.yaml`.
  - Expand `~`; validate `llama_server_path`, `model_path`, `host`, `port`.
- CLI commands: `init`, `config list|add|update|remove` with atomic writes and validation.
- Tests: unit tests for config load/validate and path handling.
- Acceptance: `llamacpp-manager init` creates config/dirs; CRUD persists and validates.

## M2 — Process Control + Logs (Direct)
- Process module to spawn/terminate `llama-server` with configured args/env.
- CLI: `start <name|all> [--dry-run]`, `stop <name|all>`, `restart`.
- Logging: per-model logs in `~/Library/Logs/llamaCPPManager` with rotation (e.g., 10MB × 5).
- Tests: mock subprocess to verify argv, logging, and signal behavior.
- Acceptance: Start/stop/restart work; logs written and rotate.

## M3 — Discovery, Status, Health
- Discover running `llama-server` PIDs and map to models/ports (direct and launchd where possible).
- Health checks: TCP connect + HTTP GET `/v1/models` or `/` with timeout; measure latency; parse version when present.
- CLI: `status [--watch]` (table) and `status --json`; `config list --json`.
- Acceptance: Accurate human and JSON status outputs suitable for GUI.

## M4 — launchd Autostart
- Generate per-model plists at `~/Library/LaunchAgents/ai.llamacpp.<name>.plist`.
- CLI: `launchd install|uninstall <name|all>`; use `launchctl bootstrap/kickstart/bootout`.
- Integrate with `autostart` flag in config and optional `--launchd` mode for start/stop.
- Acceptance: Agents install, run, and are reflected in status.

## M5 — Packaging + Docs
- Package via `pyproject.toml`, expose console script; ensure `pipx install .` works.
- README: quick start and examples; docs adjustments as features land.
- (Optional) Homebrew tap formula.
- Acceptance: Installable CLI with documented usage.

## M6 — GUI (SwiftUI Menu Bar)
- SwiftUI menu bar app in `gui-macos/`.
- Polls `llamacpp-manager status --json`; actions to Start/Stop/Restart; Tail Logs; Open Config; Preferences.
- Preferences: paths and refresh interval, persisted via CLI `config set|get`.
- Packaging: `.app` bundle with icon.
- Acceptance: Menu shows models and controls; preferences persist.

## File Layout
- pyproject.toml
- src/llamacpp_manager/
  - __init__.py
  - cli.py
  - config.py
  - process.py
  - health.py
  - logs.py
  - launchd.py
  - utils.py
- tests/
- gui-macos/
- docs/

## Next Actions
- Complete M1 scaffold: implement `cli.py` and `config.py` for `init` and `config` CRUD.
- Add basic tests for config parsing/validation.
