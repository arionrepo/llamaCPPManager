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

## Bugs (Inherited / Pre-existing, found 2026-06-22)
- [ ] **HIGH — Closing chat window quits the entire app** (found during Phase 3 smoke test)
  - Repro: start any LLM → click Chat → close the chat window (red dot or Cmd-W) → menu bar icon disappears, app process exits.
  - Root cause (confirmed via code read): `App.swift:1608-1631` creates the chat NSWindow with default `isReleasedWhenClosed = true`, calls `NSApp.activate(ignoringOtherApps: true)` (which promotes the menubar app to a regular foreground app), and there is NO `NSApplicationDelegate` overriding `applicationShouldTerminateAfterLastWindowClosed`. When the last window closes, Cocoa's default behavior terminates the foreground app. The chat window's `ChatWindowDelegate.windowWillClose` only cleans up internal references — it does not block termination.
  - Same code pattern in `openModelDownloader` (App.swift:1639+) and `openPreferences` — they likely have the same latent bug, masked when another window is still open.
  - Fix options: (a) `window.isReleasedWhenClosed = false` on all three windows, or (b) add an `NSApplicationDelegate` that returns `false` for `applicationShouldTerminateAfterLastWindowClosed`. Option (b) is the macOS-idiomatic fix for a MenuBarExtra app.
  - Effort: ~15 min. **Do not fix during conformance pass** — would mix feature change with structural refactor. Tackle after Phase 4 lands.
- [ ] **MEDIUM-HIGH — Some larger models fail to start with no UI feedback** (found 2026-06-22)
  - Symptom: click Start on a (typically larger) model → spinner appears briefly → spinner disappears → model stays stopped → no error message, no toast, no modal. No way for the user to know why.
  - Root cause (confirmed via code read): `App.swift:1278-1284` in `StatusViewModel.startWithScript` — when `service.run(...)` returns non-zero exit code, the code logs "Failed to start" to `AppLogger` (a file/os.log destination, not the UI) and removes the entry from `startupProgress` (which is why the spinner disappears). It does NOT set any UI-visible error. `StatusViewModel` doesn't even have an `errorMessage` property.
  - Additional limitation: `CLIService.run(_:)` returns only `Int32` exit code, discarding stderr text. Even if we surface the failure, we have no message to display unless we also capture stderr. CLIService does have `runAndCapture` for other call sites — should use it here.
  - Two possible underlying causes for the user-visible "can't start large models" bug, which the missing error surface is hiding:
    1. Models incompletely downloaded (e.g. partial GGUF shards) — CLI start fails with file-not-found-ish error.
    2. Insufficient RAM / VRAM at start time — llama-server / mlx_lm.server exits immediately.
  - Fix scope:
    - **Minimum:** add `errorMessage: String?` `@Published` on `StatusViewModel`, switch `service.run(...)` to `service.runAndCapture(...)` in `startWithScript`, set `errorMessage` on non-zero exit with the captured stderr, render an error banner in the menu bar dropdown (similar to how `ChatView` already does it).
    - **Better:** also surface the download-integrity check (verify file count / total size matches expected for completed downloads) before allowing Start. Catch problem #1 above before the start attempt.
  - Effort: 20-30 min for minimum scope; 1-2 h for "better" scope. **Do not fix during conformance pass** — feature change.

## Stretch / Backlog
- [ ] **Fix `version-bump.py` to also sync embedded version literals (GLOBAL — affects all repos)** (added 2026-06-19)
  - Tool: `~/.ai-dev-dotfiles/tools/version-bump.py`. Currently it updates only the `VERSION` file. It does NOT patch:
    - `gui-macos/Sources/App.swift` APP_VERSION literal (only `gui-macos/build_app.sh` does, via a perl regex, when install-gui runs)
    - `gui-macos/build/.../Info.plist` (build artifact updated by `build_app.sh`)
  - Result: after `version-bump.py` runs, `VERSION` says vN+1 but `App.swift` still says vN. The two files literally disagree until the next `install-gui` run.
  - The pre-commit hook at `.git/hooks/pre-commit` enforces tag == App.swift == Info.plist, so any commit between bump-time and install-gui-time fails. Chicken-and-egg with the documented release process in `.claude/CLAUDE.md`.
  - Proposed fix: make `version-bump.py` repo-aware. Discover patchable files via a config (e.g. `.versionbump.yaml` at repo root) or by scanning known patterns (`APP_VERSION = "x.y.z"`, `version: x.y.z` in Info.plist, `version = "x.y.z"` in pyproject.toml, etc.). Solution must work for ALL of the user's repos — not a llamaCPPManager-local hack.
  - Also: redesign the pre-commit hook to check `VERSION` file (not latest git tag) so tagging is truly optional as `.claude/CLAUDE.md` claims.
  - Workaround until fixed: after running `version-bump.py`, manually patch the App.swift literal (or run `install-gui --no-launch`), then commit. For commit, may need `--no-verify` if hook's git-tag check fails — or tag retroactively before commit.
  - Found during: Swift conformance pass Phase 3 (2026-06-19). Phase 3 was forced to ship as a no-bump structural commit to avoid the trap.
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
