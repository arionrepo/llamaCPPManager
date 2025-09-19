# TODO (Project Task List)

This file tracks actionable tasks using GitHub task list checkboxes. Update as work progresses.

## Conventions
- Use short, actionable items; prefer verbs (Implement, Add, Wire, Test).
- Check items when merged to `main`.
- Keep milestone headers in sync with `docs/implementation-plan.md`.

## Links
- Requirements: docs/requirements.md
- Design: docs/design.md
- Implementation Plan: docs/implementation-plan.md

## M1 — CLI + Config (Current)
- [x] Add project scaffold (pyproject.toml, package dir)
- [x] Create package `src/llamacpp_manager/__init__.py`
- [ ] Implement `config.py` (paths, YAML load/save, validation)
- [ ] Implement `utils.py` (paths, atomic write, expanduser)
- [ ] Implement `cli.py` with commands: `init`, `config list|add|update|remove`
- [ ] Write basic unit tests for config parsing/validation
- [ ] Update README with quick start for M1

## M2 — Process Control + Logs (Direct)
- [ ] Implement `process.py` (spawn/terminate, signals)
- [ ] Implement `logs.py` (log file mgmt + rotation)
- [ ] CLI: `start <name|all> [--dry-run]`, `stop <name|all>`, `restart`
- [ ] Tests with mocked `subprocess` and log writes
- [ ] README/examples for starting/stopping models

## M3 — Discovery, Status, Health
- [ ] Add process discovery (map running llama-server → models)
- [ ] Implement `health.py` (TCP + HTTP checks, latency, version)
- [ ] CLI: `status [--watch]` (table) and `status --json`
- [ ] CLI: `config list --json`
- [ ] Tests for health and JSON serialization

## M4 — launchd Autostart
- [ ] Implement `launchd.py` (render/load/unload plists)
- [ ] CLI: `launchd install|uninstall <name|all>`
- [ ] Integrate `--launchd` mode in start/stop, reflect `autostart`
- [ ] Tests/instructions for launchd behavior

## M5 — Packaging + Docs
- [ ] Verify pipx install (`pipx install .`) and console script
- [ ] Expand README with troubleshooting and examples
- [ ] (Optional) Homebrew tap formula draft

## M6 — GUI (SwiftUI Menu Bar)
- [ ] Create SwiftUI menu bar app skeleton (`gui-macos/`)
- [ ] Parse `status --json` and render model list
- [ ] Wire actions: Start/Stop/Restart, Tail Logs, Open Config
- [ ] Preferences (paths, refresh interval); call CLI `config set|get`
- [ ] App icon and packaging (.app)

## Stretch / Backlog
- [ ] Prometheus endpoint/sidecar for metrics
- [ ] Workspace profiles (multiple configs)
- [ ] Raycast commands / VS Code tasks
- [ ] Warnings/auth for non-local binds

## Done
- [x] Add requirements (granular, acceptance criteria)
- [x] Add design with architecture + GUI diagrams
- [x] Add implementation plan document
