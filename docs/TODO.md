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
- [ ] **MCP server visibility & GUI lifecycle management** (added 2026-06-19, see discussion in conformance-pass session)
  - Status today: `src/llamacpp_manager/mcp_server.py` exists (464 lines, 8 tools, registered as `llamacpp-mcp-server` console script via `pyproject.toml`). Documented in `docs/mcp-server-api.md`. **But it is invisible in the GUI and the README — agentic users don't know it exists.**
  - Proposed scope (revisit *after* Swift conformance pass completes, since adding an infra row to the current 2,732-line `App.swift` would make that file worse):
    1. Add MCP server as a first-class infrastructure component in the GUI (same row pattern as cloudflared / llm_controller): status indicator, start/stop toggle, last-restart timestamp.
    2. Add a "Copy agent config" button that writes the right `claude_desktop_config.json` / Codex / Gemini snippet to clipboard, pointing at the user's installed `llamacpp-mcp-server` path.
    3. Add a one-liner to `README.md` and `CLAUDE.md` advertising that the repo ships an MCP server (current docs only mention CLI + GUI).
    4. Verify the pipx-install gotcha (CLAUDE.md "Python CLI Development" section) doesn't silently break the MCP console-script entry point after `pipx reinstall`.
    5. Product question to answer before building: are the existing 8 tools sufficient, or are `compare_models` / `chat_history` / `query_multi` agent tools also needed?
  - Explicitly out of scope: reimplementing the MCP server in Swift inside the macOS app. That was evaluated and rejected as overkill.
  - Dependency: do *not* start before `docs/SWIFT-CONFORMANCE-PLAN.md` phases 0–4 are complete.
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
