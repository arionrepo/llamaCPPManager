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

### Open items from 2026-06-23 session

- [ ] **LOW — Add search field to Native LLM tab; pin running models to top** *(requested 2026-06-23)*
  - User request: the Native Models tab has many models and no way to filter. Add a text search field that filters model rows by name. When the search field is empty, running models should be pinned to the top of the list.
  - Implementation notes: add a `@State var searchText: String` to the tab view; filter the displayed list against model name case-insensitively; when `searchText.isEmpty`, sort so `modelStatus[name] == .running` entries come first. The rendered list is already array-driven — just needs a computed filtered+sorted property feeding the `ForEach`.
  - Estimated effort: ~30 min in `App.swift` (or extracted view file when refactoring). No backend changes needed.

- [ ] **LOW — Show the active `mode` label for running models** in the Native Models tab. When a model is up, the mode Picker is correctly hidden (mode is locked-in for a live server and can only change at restart), but currently there's no indication of what mode it was started with. Add a one-line `Mode: <basic|tools|performance|extended>` (or `basic|think` for MLX) display next to the uptime / health info. Source: `spec.mode` from the YAML row (also returned by `llamacpp-manager status --json` as `m["mode"]`). Small UX polish, ~15 min in `App.swift` around the row-render block.

- [ ] **LOW — Add `--ctx-size` and `--n-gpu-layers` flags to `llamacpp-manager config update`.** Currently set via direct YAML edit only. The new fields exist on `ModelSpec` (since v2026.06.23.1) and are honored by `build_argv` — just no CLI affordance to set them. ~15 min in `cli.py` `cmd_config_update`.

- [ ] **Delete the bash launcher after soak.** `restart-llm-interactive.sh` (outside repo, in `~/llms/`) and the `start-script` CLI subcommand are kept around as a safety net during the GGUF-source-of-truth migration (landed 2026-06-23 in v2026.06.23.1). Once a few models have been confirmed working under the new `start` path for GGUF, delete both. The CLI deletion involves: remove `sp_start_script` argparser registration in `cli.py`, remove `cmd_start_script` handler, and any tests referencing it.

### Open items from 2026-06-22 session

- [ ] **MEDIUM — Download progress not visible in the Native Models tab (confirmed 2026-06-22)**
  - User repro confirmed: the `hf download unsloth/diffusiongemma-26B-A4B-it-GGUF` that wrote ~7 GB to `~/llms/diffusiongemma-26b/.cache/huggingface/download/*.incomplete` was completely invisible in the GUI's "Active Downloads & Loading" section throughout its lifetime.
  - **Root cause (confirmed via code read):** `vm.downloadViewModel.downloads` is populated ONLY by downloads initiated through the GUI's own Model Downloader window. External invocations — `hf download` from a shell, `huggingface-cli`, or `llamacpp-manager models download` from any non-GUI source — never enter that dict. Same architectural gap as the original "external mlx_lm.server processes" problem which was already solved by the external-server scanner.
  - **Proposed fix (mirrors the existing external-server scanner pattern in `StatusViewModel`):**
    1. Add a background `Task.detached` scanner that periodically walks each configured model's `model_path` directory looking for `.cache/huggingface/download/*.incomplete` files, OR scans for active `hf download` / `models download` subprocesses (the cleanup module already has `find_stale_downloads` which can be extended).
    2. For each detected active download, post a synthetic entry into a new `@Published var externalDownloads: [String: ExternalDownloadProgress]` field on `StatusViewModel`.
    3. Render those alongside the existing GUI-initiated downloads in the "Active Downloads & Loading" section.
  - Effort: ~1-2 hours. Touches `cleanup.py` (extend with `find_active_downloads`), `StatusViewModel.swift` (new scanner + field), `App.swift` (render external downloads).
  - Secondary issue (still hypothetical, not confirmed):
    - `parseStartupLog` regex may not match the current mlx-lm 0.31.3 log format. The "Fetching N files" pattern was added when MLX models lazy-download weights on first start. Worth a re-check, but only AFTER a controlled repro: clear `~/.cache/huggingface/hub/models--mlx-community--gemma-3-1b-it-4bit`, click Start, compare log output to parseStartupLog patterns.

- [ ] **MEDIUM — Model Downloader UI doesn't allow downloading all listed models** (especially diffusion models)
  - User report (2026-06-22): the in-app Model Downloader window lists models but doesn't let the user download some of them, particularly diffusion-class models.
  - Probable causes:
    1. **Curated catalog filter** — the downloader UI may filter to a known-good subset (GGUF-only? text-only?). Diffusion / multimodal entries may be displayed but Download button is disabled/missing.
    2. **Download command incompatibility** — the CLI's `models download <name>` may only support a specific path (e.g., HF-Hub via huggingface_hub library); diffusion models may need different download tooling.
    3. **Static catalog list** — entries hardcoded in the GUI / CLI that haven't been updated for newer model classes (DiffusionGemma was released 2026-06-10).
  - Investigation needed:
    - Read `ModelDownloaderView.swift` to see filter / disable conditions.
    - Read `src/llamacpp_manager/models/downloader.py` to see what `llamacpp-manager models download <name>` supports.
    - Compare against the displayed catalog to see which entries can't be acted on.
  - Acceptance criteria for fix: every model row in the downloader UI has a working Download button OR a clearly displayed reason why it's unavailable (e.g., "requires GUI version >= X" / "diffusion class — use direct hf download to ~/llms/X").

- [ ] **Per-model `llama_server_path` config field (generalizable infra improvement)** — Today every native/GGUF model goes through the same `restart-llm-interactive.sh` which picks llama-server via PATH fallback. Adding an optional per-model `llama_server_path` field would allow: (a) pinning a known-good llama.cpp build per model, (b) running an experimental fork for one model without breaking others, (c) eventually pointing diffusion-class models at a diffusion-capable server when that exists. ~30 min to wire: extend config schema → extend `start-script` arg passing → update `restart-llm-interactive.sh` to honor an env var or extra arg. Low risk, high optionality.

- [ ] **DiffusionGemma via llama.cpp — DO NOT pursue until upstream catches up** *(research notes 2026-06-22)*
  - Mainline `llama.cpp` does **not** support DiffusionGemma as of 2026-06-22.
  - PR [`ggml-org/llama.cpp#24427`](https://github.com/ggml-org/llama.cpp/pull/24427) is open, draft, 35+ commits, 0 reviews, with merge conflicts. Adds `DIFFUSION_GEMMA4` arch + conversion path.
  - Sibling PR `#24423` ships a separate `llama-diffusion-cli` binary with a custom entropy-bounded sampler (`--diffusion-eb`, `--diffusion-eb-max-steps`, `--diffusion-eb-t-max/min`, `--diffusion-eb-entropy-bound`).
  - **Critical gap for our use case**: the PR is **CLI-only — no `llama-server`**. Our entire GUI assumes a server with /health and /v1/chat/completions. A CLI-only binary can't plug in.
  - Sampler / arch summary: 256-token canvas, parallel denoising, block-autoregressive chaining, ~15-20 tokens per forward pass, optional KV cache over committed prompt prefix.
  - Recommendation: ignore the GGUF route until both (a) PR merges and (b) server mode lands. Use `mlx-diffusiongemma` (MLX-VLM) which already works.
  - The in-progress download was cancelled 2026-06-22 with ~7 GB partial in `~/llms/diffusiongemma-26b/.cache/` (operator to `rm -rf` the cache dir to reclaim).
  - Sources: [PR #24427](https://github.com/ggml-org/llama.cpp/pull/24427), [unsloth/diffusiongemma-26B-A4B-it-GGUF](https://huggingface.co/unsloth/diffusiongemma-26B-A4B-it-GGUF), [diffusiongemma.dev/llama-cpp](https://diffusiongemma.dev/llama-cpp/), [ollama issue #16664](https://github.com/ollama/ollama/issues/16664).

### Audit findings from "check all modes for GGUF and MLX" sweep (2026-06-22)

- [ ] **MEDIUM — `restart-llm-interactive.sh` PATH lookup is fragile** (the user's personal script at `/Users/liborballaty/llms/restart-llm-interactive.sh:108`)
  - `LLAMA_SERVER=$(which llama-server 2>/dev/null || echo "/opt/homebrew/bin/llama-server")` falls back to a path that doesn't exist on this system. If `llama-server` isn't on the GUI subprocess's PATH (the LocalProjects build dir typically isn't), the script gets a "No such file or directory" before reaching mode-arg parsing. The GUI then sees the eventual exit code only.
  - Fix: replace the fallback with the actual local-build path (`/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llama.cpp/build/bin/llama-server`) OR have the GUI's `start-script` invocation export a PATH that includes the local build dir, OR pin the script to a config-read value.

- [ ] **MEDIUM — MLX models silently ignore the `mode` field**
  - `src/llamacpp_manager/mlx_process.py:build_mlx_argv` does not branch on `spec.mode`. So picking `performance`, `tools`, or `extended` for any MLX model has zero effect — only `--model`, `--host`, `--port`, and `spec.args` are appended.
  - User impact: confusing UX (mode picker appears active but does nothing for MLX). For MLX-relevant tuning (e.g. KV cache type, draft model, max_kv_size) `mlx_lm.server` has its own flag set; the GUI/CLI should either route an MLX-specific mode table OR hide the mode picker on MLX rows.
  - Affected: mlx-gemma-3-1b, mlx-gemma4-31b, gemma-270m-compliance-mlx, gemma-3-27b-mlx, mistral-05b-compliance-mlx, mlx-diffusiongemma.

- [ ] **LOW — `parseStartupLog` reads stale log lines and produces false "Issue detected" alerts**
  - `Sources/ViewModels/StatusViewModel.swift` `parseStartupLog()` scans the last 50 lines of `<model>.log` for the substring `error`. The log file is append-only across runs, so historical tracebacks from prior failed attempts (e.g. the gemma4 `ValueError: Model type gemma4 not supported` lines that lingered after the mlx-lm upgrade) keep triggering the false alert during legitimate new starts.
  - Three possible fixes (cheapest first): (1) anchor parsing to lines after the most recent "Starting httpd" / startup banner, (2) parse in reverse and let the most recent success/fail signal win, (3) truncate `<model>.log` on each fresh start (destructive — loses history).

- [x] **HIGH — Closing chat window quits the entire app** *(fixed v2026.06.23.6–7, verified by user)*
  - Root cause 1 (v2026.06.23.6): `ChatWindowDelegate.windowWillClose` called `onClose()` which removed the last strong ref to `self` while still on the call stack → use-after-free/SIGSEGV in `objc_release`. Fixed: deferred `onClose()` to `windowDidClose` in all three delegates (`ChatWindowDelegate`, `ModelDownloaderWindowDelegate`, `PreferencesWindowDelegate`).
  - Root cause 2 (v2026.06.23.7): `isReleasedWhenClosed = true` (Cocoa default) caused the NSWindow to be freed by ObjC runtime before `windowDidClose` fired, leaving dangling refs in `chatWindows`/`windowDelegates`. Fixed: `window.isReleasedWhenClosed = false` on all stored windows in `StatusViewModel`. Added `applicationShouldTerminateAfterLastWindowClosed → false` in `AppDelegate`.
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
- [ ] **Rewrite SWIFT-AGENT-STANDARD testing sections to remove mock guidance** (added 2026-06-24)
  - Trigger: testing-strategy decision this session — real-stack vertical-slice E2E tests, no mocks/fakes/protocol-mocking.
  - Affected canonical doc: `docs/SWIFT-AGENT-STANDARD.md` §4.4 + every other mention of "mock"/"fake"/"protocol so it can be mocked" (currently lines 87, 249, 628, 636, 765).
  - Affected derived doc: `docs/SWIFT-CONFORMANCE-PLAN.md` §9 (Phase 6) + §10 (Phase 7) — both now annotated SUPERSEDED with forward pointers; full rewrite still pending.
  - Required rewrite shape (sketch, to confirm before doing):
    1. §4.4 testing framework table: drop "Service tests with mocks/fakes"; replace with "Service tests against real subprocesses / real CLI / real model server (vertical-slice E2E)".
    2. Wherever the standard recommends "behind a protocol so it can be mocked", restate as "structured `CLIError` + comprehensive `LifecycleLog` coverage" so error paths stay debuggable without fakes.
    3. New section on vertical-slice E2E: setUp picks an already-configured model, exercises the real stack, asserts shape-only outcomes (non-empty rows, non-empty assistant message, state transition).
    4. Reference the existing real-subprocess tests (`RunCommandStreamingTests` against `/bin/echo`, `/bin/sleep`, `/usr/bin/false`) as the existing in-tree model.
  - Reference: today's session ended with this decision but did not write the rewrite. The minimal-safe annotations on the plan + standard are in place to prevent future agents from being pulled back to mocks.
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
