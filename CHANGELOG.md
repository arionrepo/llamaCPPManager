# Changelog

This project uses date-based versioning: `YYYY.MM.DD.N`. The current version
is in the repo's `VERSION` file. Use `/version-bump` or
`python3 ~/.ai-dev-dotfiles/tools/version-bump.py` to bump.

## [Unreleased]

### Known Issues (carried forward)

- **`docs/SWIFT-AGENT-STANDARD.md` is referenced from `CLAUDE.md`
  but was authored mid-session and not yet applied to the work in
  this session.** Future Swift work in `gui-macos/` must read that
  doc before editing per the new mandatory rule in CLAUDE.md.
  The v.6 and v.7 Swift edits below were not retroactively audited
  against the standard but were inspected for no force-unwraps, no
  secrets, no `@unchecked Sendable` introductions.

## [2026.06.19.7] - 2026-06-19

### Added
- **"Copy spec from" dropdown in Create Profile form** — pick an
  existing Colima profile and its `cpus/memory/disk/runtime/arch`
  pre-fill the form for the new VM. Source-VM data is untouched;
  the new VM is independent with identical resource flags. Closes
  the gap between Colima's mental model (each profile is its own
  VM) and the user's "create another one like that" need.
- **Runtime + Architecture pickers** in the Create Profile form
  (`docker`/`containerd`, `aarch64`/`x86_64`). Default to
  `docker` and `aarch64` for M-series Macs.
- **Live streaming progress output** during VM creation — the
  form now shows a `ProgressView` plus a 100-pt scrollable mono
  log that streams colima's stdout/stderr in real time. New
  `runCommandStreaming` helper in `DockerService` uses
  `FileHandle.readabilityHandler` to deliver per-line callbacks
  to the main queue. VM provisioning takes 30-60s so feedback
  matters.
- **SSH button per running Colima profile** — opens Terminal.app
  via `osascript` and runs `colima ssh -p <profile>` so the user
  can drop into the VM without leaving the menu bar app. Profile
  names are escaped for AppleScript safety.

### Changed
- Create Profile form window expanded to 460x560 to accommodate
  the new fields and live log.
- Memory/disk field labels now explicitly say "GiB" (was
  ambiguous "Memory (optional)").

## [2026.06.19.6] - 2026-06-19

### Fixed
- **Create Profile silently failed (root-cause fix).** The form
  opened, accepted input, the Create button was clickable — but
  no profile was created and no error appeared. Root cause:
  `DockerService.createColimaProfile` invoked `colima create
  <name>`, which is not a real Colima subcommand. Colima creates
  a VM on first `colima start <profile>` (the `start` command
  both creates and starts). The `Bool` return was also discarded
  by the caller so any non-zero exit was swallowed silently.
  Fix:
  1. Use `colima start <name>` (with `--cpus` instead of `--cpu`).
  2. Change `createColimaProfile` signature to return `String?`
     (nil on success, error message on failure).
  3. `CreateProfileForm` now holds an `errorMessage` `@State`,
     displays it in red, and only auto-closes on success.
  4. Form is lenient about unit suffixes — strips trailing
     `G`/`GB`/`GiB` from memory/disk so old habits still work
     (Colima itself expects bare GiB integers).

## [2026.06.19.5] - 2026-06-19

### Fixed
- **Create Profile form was frozen** in the Infrastructure tab — could
  type the name field only; other fields and the Create button were
  unresponsive. Replaced SwiftUI `.sheet` (which fails inside
  MenuBarExtra because the modal can't steal focus from the menu's
  transient host window) with a real `NSWindow + NSHostingController`
  via new `CreateProfileForm` view and `CreateProfileWindowController`.
  Tab key now moves between fields; Return triggers Create.
- Removed unused `@State` vars (showCreateSheet,
  newProfileName/Cpus/Memory/Disk) — moved into the new form view.

## [2026.06.19.4] - 2026-06-19

### Fixed
- **Delete Profile dialog froze the entire menu** in the Infrastructure
  tab — clicking Delete on a stopped Colima profile presented a
  confirmation dialog that the user could not interact with at all
  (couldn't click Delete or Cancel). Same MenuBarExtra modal-focus
  issue as the Create Profile sheet. Replaced
  `.confirmationDialog` with `NSAlert.runModal()` + `NSApp.activate(ignoringOtherApps:)`.

## [2026.06.19.3] - 2026-06-19

### Fixed
- **CLIService.run / runAndCapture blocked the main thread** — every
  model start/stop/chat/status fetch and every model-download CLI call
  went through these two methods (~18 call sites). Both used synchronous
  `Process.waitUntilExit()` on the caller's thread, freezing the UI
  during any long-running CLI invocation. Refactored to use
  `withCheckedThrowingContinuation` + `DispatchQueue.global(qos: .userInitiated)`
  + `Process.terminationHandler`. Signatures unchanged.
- `parseStartupLog()` now reads only the last 64KB of a log via
  `FileHandle` seek instead of loading the whole file. Prevents log-polling
  task stalls on huge model log files.

## [2026.06.19.2] - 2026-06-19

### Fixed
- **`colima delete` froze the GUI** for the entire 5-30 second duration
  of the VM teardown. Root cause: `DockerService.runCommand` used
  synchronous `Process.waitUntilExit()` while
  `DockerColimaViewModel` is `@MainActor`. Refactored to background
  queue + `terminationHandler` so the UI stays responsive while colima
  works. Fix applies to all 11 docker/colima operations
  (getColimaProfiles, start/stop/restart/createColimaProfile,
  deleteColimaProfile, getDockerContainers, start/stop/restartDockerContainer,
  getContainerStats).

### Added
- **`/llamacpp-install-gui` slash command** (repo-local in
  `.claude/commands/`) — invokes `llamacpp-manager install-gui`. Renamed
  from generic `/install-gui` for repo-namespace clarity. Includes YAML
  frontmatter so Claude Code registers it.

## [2026.06.19.1] - 2026-06-19

### Added
- **Deterministic GUI installer** (`gui-macos/install_gui.sh`) — single
  command replaces the brittle `killall + rm + cp + open` pipeline.
  Auto-detects rebuild need, verifies MD5 of installed binary, reports
  version, confirms process is running. Distinct exit codes per failure mode.
- **CLI wrapper** `llamacpp-manager install-gui` with `--no-rebuild`,
  `--no-launch`, `--force`, `--quiet` flags. Lifecycle events:
  `cli.install_gui.{begin,result,interrupted}`.
- **Slash command** `/install-gui` in `.claude/commands/install-gui.md` for
  agentic / Claude Code use.
- **MLX-VLM deployment backend** for diffusion / vision-language models.
  - `src/llamacpp_manager/mlx_vlm_process.py` (new spawner with
    `start_new_session=True` for proper detachment + pre-flight check
    that emits actionable bootstrap-instruction errors).
  - `cmd_start` gained a new `elif spec.deployment_type == "mlx-vlm"` branch
    placed above existing branches so they remain byte-identical.
  - 4 new catalog entries: `mlx-diffusiongemma-26b-{4,5,6,8}bit` routed
    to `mlx_vlm.server`.
  - Legacy `diffusiongemma-26b` GGUF entry renamed to
    `-gguf-legacy` and marked `deprecated: true`.
- **`llamacpp-manager bootstrap mlx-vlm`** command — creates dedicated
  venv at `~/mlx_vlm_env`, installs mlx-vlm, auto-updates config with
  `mlx_vlm_python_path`. Lifecycle events:
  `bootstrap.mlx_vlm.{begin,success,failure,warning}`.
- **GUI awareness** of `deployment_type == "mlx-vlm"` (routes Start clicks
  through CLI `start`, which uses the Phase 1b branch). New pink
  `DIFFUSION` badge color in `formatBadgeColor()`.
- **JSON status payload** now carries `engine`, `deployment_type`,
  `experimental`, `deprecated`, `note` pass-through fields for the GUI.
- **README**: new "Supported Backends" table (native / container / mlx /
  mlx-vlm) and "Lifecycle Diagnostics" section.

### Changed
- `--deployment-type` argparse choices in `config add` now include
  `mlx-vlm` alongside `native`, `container`, `mlx`.
- `validate_model()` skips local-file-exists check for `mlx-vlm` models
  (they use HuggingFace repo IDs, downloaded lazily by `mlx_vlm.server`).
- `CLAUDE.md` GUI workflow now leads with `llamacpp-manager install-gui`;
  the 5-step manual sequence is preserved in a `<details>` block.
- `.claude/CLAUDE.md` versioning strategy clarified: date-based
  `YYYY.MM.DD.N` (not semver). Documents `/version-bump` and the
  canonical `VERSION` file.

### Notes
- Existing GGUF (`native`) and MLX (`mlx`) deployment paths verified
  unchanged across 7 phased commits (`git diff --stat` empty for
  `process.py`, `mlx_process.py`, `health.py`, `query.py`,
  `docker_manager.py`, `monitor.py`).

## [2026.06.16.2] - 2026-06-16
- Enriched model rows in GUI: filename, quantization badge, file size,
  live RAM / CPU% when running, catalog description.

## [2026.06.16.1] - 2026-06-16
- Structured lifecycle event log
  (`~/Library/Logs/llamaCPPManager/lifecycle.jsonl`).
- `llamacpp-manager lifecycle` diagnostic command with `--tail`, `--model`,
  `--follow`, `--path`.
- Fixed `start_process` Popen calls to use `start_new_session=True` so
  llama-server children survive the parent CLI exiting (was the cause of
  models dying ~25-30s after start).
- Active Downloads section pinned to top of menu bar; auto-detects
  externally-started downloads / loads.
- Catalog cleanup: filename case-sensitivity fixes + 7 stale repos replaced.

## [2026.03.26] - 2026-03-26
- Automated release
- Includes latest improvements and bug fixes
## [1.1.14] - 2025-10-11
- Automated release
- Includes latest improvements and bug fixes
## [1.1.13] - 2025-10-11
- Automated release
- Includes latest improvements and bug fixes
## [1.1.12] - 2025-10-11
### Fixed
- Version alignment across all artifacts (Info.plist, DMG filename, About dialog)
- DMG filename now uses numeric version without 'v' prefix
- Info.plist now uses numeric version per Apple standards
- Build script commits are now part of release process

## [1.1.11] - 2025-10-11
### Fixed
- About dialog now dynamically uses APP_VERSION constant
- Added Release Notes link to About dialog
- Improved version update mechanism with perl replacement

## [v1.1.0] - 2025-10-11
### Added
- Enhanced Model Downloader filtering mechanism
- More inclusive model filtering across different use cases
- Expanded search criteria for model categories (Agentic AI, Coding, Compliance, General)
- Improved versioning mechanism for GUI
- Added git-based version tracking in build script

### Improvements
- Model downloader now shows more diverse models
- Improved use case and description matching logic
- Better visibility of available models across different categories

### Fixed
- Model downloader filtering mechanism
- Potential issues with model list display
- Logging and error handling in the model download process

## [v1.0.0] - 2025-10-10
### Initial Release
- Basic model management functionality
- MenuBar extra interface for llamaCPP Manager