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
- [x] Implement `config.py` (paths, YAML load/save, validation)
- [x] Implement `utils.py` (paths, atomic write, expanduser)
- [x] Implement `cli.py` with commands: `init`, `config list|add|update|remove`
- [x] Write basic unit tests for config parsing/validation
- [x] Update README with quick start for M1
- [x] Add `config migrate` (safe copy/move with backup)

## M2 — Process Control + Logs (Direct)
- [x] Implement `process.py` (spawn/terminate, signals)
- [x] Implement `logs.py` (log file mgmt + rotation)
- [x] CLI: `start <name|all> [--dry-run]`, `stop <name|all>`, `restart`
- [x] Tests with mocked `subprocess` and log writes
- [x] README/examples for starting/stopping models

## M3 — Discovery, Status, Health
- [x] Add process discovery (map running llama-server → models)
- [x] Implement `health.py` (TCP + HTTP checks, latency, version)
- [ ] CLI: `status [--watch]` (table) and `status --json`
- [x] CLI: `config list --json`
- [x] Tests for health and JSON serialization
 - [x] CLI: `ensure-running` to auto-start missing autostart models

## M4 — launchd Autostart
- [x] Implement `launchd.py` (render/load/unload plists)
- [x] CLI: `launchd install|uninstall <name|all>`
- [x] Integrate `--launchd` mode in start/stop/restart
- [x] Tests for plist rendering

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

## M7 — Unified Model Manager (In Progress)
- [ ] Add model groups with mutual exclusion to config schema
- [ ] Implement unified ModelManager supporting native + container deployments
- [ ] Add on-demand model lifecycle management
- [ ] Create model downloader module for large coding models
- [ ] Extend MCP server with coding model tools
- [ ] Add model groups view to GUI
- [ ] Download Qwen Coder 32B, 14B, DeepSeek Coder Lite
- [ ] Document flexible deployment options

## M8 — Container Support (Optional)
- [ ] Create containers/ module (docker_client.py, lifecycle.py, templates.py)
- [ ] Add container deployment type to ModelManager
- [ ] Implement llama.cpp and MLX container templates
- [ ] Add container CLI commands (--container flag)
- [ ] Extend GUI with container indicators
- [ ] Test native-to-container migration

## M9 — Infrastructure Management (Completed)
- [x] Infrastructure module for cloudflared and llm_controller
- [x] Health monitoring with auto-restart
- [x] launchd and script-managed component types
- [x] Uptime tracking for all components
- [x] GUI integration for infrastructure status
- [x] Hung process detection and cleanup

## Stretch / Backlog
- [ ] Prometheus endpoint/sidecar for metrics
- [ ] Workspace profiles (multiple configs)
- [ ] Raycast commands / VS Code tasks
- [ ] Warnings/auth for non-local binds
- [ ] VS Code extension for model management
- [ ] Inactivity auto-stop for large models
- [ ] Model preloading and fast-switching
- [ ] Resource usage monitoring dashboard

## Done
- [x] Add requirements (granular, acceptance criteria)
- [x] Add design with architecture + GUI diagrams
- [x] Add implementation plan document
- [x] Infrastructure management (Phases 1-4)
- [x] Health monitoring with retry policies
- [x] MCP server implementation
