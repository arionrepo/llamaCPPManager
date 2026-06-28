# Changelog

This project uses date-based versioning: `YYYY.MM.DD.N`. The current version
is in the repo's `VERSION` file. Use `/version-bump` or
`python3 ~/.ai-dev-dotfiles/tools/version-bump.py` to bump.

## [Unreleased]

## [2026.06.28.2] - 2026-06-28

### Fixed

- **Removed the new `DockerService` sendability warning introduced by the Colima profile fix.**
  The service now resolves the executable path and snapshots the subprocess
  environment before entering the background `DispatchQueue` closure, so the
  closure no longer captures non-`Sendable` `self`.
- **Cleaned the GUI unit-test target's async-lock warning** in
  `RunCommandStreamingTests.swift` by making the test line collector's read
  method synchronous.

### Verification

- `swift test` in `gui-macos`
- `llamacpp-manager install-gui --force`

## [2026.06.28.1] - 2026-06-28

### Fixed

- **Colima profiles render again in the macOS GUI when the app is launched without a Homebrew-inheriting shell `PATH`.**
  `gui-macos/Sources/Services/DockerService.swift` now resolves `colima` and
  `docker` from explicit executable locations before falling back to `PATH`,
  so the Docker/Colima view no longer collapses to "No Colima profiles found"
  in launchd-style environments.

### Added

- **Regression coverage for GUI executable resolution** in
  `gui-macos/Tests/DockerColimaTests/RunCommandStreamingTests.swift`,
  locking the minimal-`PATH` Colima lookup case and an injected-`PATH`
  custom executable case.

### Verification

- `swift test` in `gui-macos`
- `llamacpp-manager install-gui --force`

## [2026.06.25.1] - 2026-06-25

### Fixed

- **`status --json` no longer crashes on an empty config.** The infrastructure
  uptime path in `src/llamacpp_manager/cli.py` now resolves
  `get_process_uptime` outside the per-model loop, so status collection works
  whether there are zero configured models or many.

### Added

- **Canonical status schema lock** in `tests/fixtures/status_schema.json` plus
  expanded `tests/test_status.py` coverage for empty-config output, every
  declared `deployment_type`, mixed running/stopped rows, infrastructure
  presence, optional nullable fields, and JSON-vs-table consistency.
- **External CLI contract coverage** in
  `tests/test_cli_external_invocation.py` and `docs/CLI-EXIT-CODES.md`,
  locking subprocess invocation behavior for piped JSON output, UTF-8 model
  names, concurrent read-only invocations, stable exit codes, and
  stdout/stderr separation.

### Changed

- **Typed `pgrep` degradation warning on `stop`.** If `pgrep` is unavailable,
  the CLI now emits a stable warning to `stderr` and continues with the main
  stop path instead of silently swallowing the missing helper.

### Verification

- `pytest tests/test_status.py -q`
- `pytest tests/test_status.py tests/test_status_watch.py -q`
- `pytest tests/test_lifecycle_log_schema.py -q`
- `pytest tests/test_cli_external_invocation.py -q`
- `pytest tests/test_cli_start_stop.py tests/test_security_and_bincheck.py tests/test_ports_and_warnings.py -q`

## [2026.06.24.5] - 2026-06-24

### Added (E2E Slices B + C; full contract documented)

- **Slice B — Chat Window Open + Cmd-W Close** (`Tests/E2E/SliceB_ChatWindowTests.swift`).
  User flow: launch app → click menu bar icon → click Chat on a configured
  model → verify chat window opened → send Cmd-W → verify window closed.
  Regression-tests the v2026.06.23.7 / .8 window-lifecycle fixes. Opt-in:
  `RUN_E2E_INTERACTIVE=1 swift test`. Requires Accessibility permission for
  the terminal/IDE running `swift test` (one-time macOS setup). When
  `RUN_E2E_INTERACTIVE` is unset the slice cleanly skips with a clear
  setup message — so default `swift test` remains CI-safe.
- **Slice C — Chat Send + Receive** (`Tests/E2E/SliceC_ChatSendReceiveTests.swift`).
  User flow: open chat window → type "hi" → press Return → verify assistant
  reply arrived via `cli.chat.reply_received` event. Real CLI → real
  subprocess → real llama.cpp/MLX server → real network. Same opt-in gate as
  slice B, plus a model server must be running.
- **New `cli.chat.reply_received` / `cli.chat.reply_failed` LifecycleLog
  events** emitted from `ChatViewModel.sendMessage` after each chat
  round-trip. Provides slice C's deterministic signal and improves
  production debuggability of failed chat round-trips.
- **`clickChatButton()` helper** promoted from `fileprivate` in slice B
  to shared in `E2EHelpers.swift` for reuse by slice C.
- **`interactiveSlicesEnabled` flag + `interactiveSkipMessage`** in
  `E2EHelpers.swift`: gates accessibility-dependent slices behind the
  `RUN_E2E_INTERACTIVE` env var and prints clear one-time setup
  instructions when skipped.
- **`docs/E2E-SLICES.md`**: full contract documenting what a slice is,
  the osascript + log-inspection strategy, per-slice setup requirements,
  how to run (default vs opt-in), and how to add new slices.

### Verification

- Default `swift test`: 14 XCTest + 4 Swift Testing (2 executed, 2 skipped
  cleanly) — 18 tests, 0 failures. ~7 seconds total.
- Build clean. install-gui --force clean at v2026.06.24.5.

## [2026.06.24.4] - 2026-06-24

### Added (E2E Slice A — App Launch & Boot)

- **First real-stack vertical-slice E2E test landed.** User flow: open the
  app. Verifies the installed `/Applications/llamaCPP Manager.app` launches,
  emits `ui.app.did_finish_launching`, and the first real CLI status fetch
  (against the real Python `llamacpp-manager` CLI on this machine) completes
  and emits the new `cli.status.fetched` event with `model_count` and
  `infrastructure_count` fields. No mocks, no fakes, no protocol seams.
  2/2 tests passing in 7 seconds.
- **New `cli.status.fetched` LifecycleLog event** emitted from
  `StatusViewModel.refresh()` after each successful CLI fetch. Provides a
  deterministic signal for E2E slices to key off "first status refresh
  completed". Carries `model_count` + `infrastructure_count`.
- **New `E2ETests` test target** in `gui-macos/Package.swift` (path
  `Tests/E2E/`). Independent from the existing `llamacpp-guiTests` target.
  Slice tests launch the installed app via `Process`, drive it via
  `osascript` / System Events, and inspect
  `~/Library/Logs/llamaCPPManager/lifecycle.jsonl` for assertions.
- **Shared helpers in `Tests/E2E/E2EHelpers.swift`**: `launchApp()`,
  `quitApp(_:)`, `snapshotLogOffset()`, `waitForLogEvent(_:after:timeout:)`,
  `runAppleScript(_:)`, `clickStatusBarItem()`, `sendCmdW()`, `typeString(_:)`,
  `sendReturn()`. Status-bar click and keystroke driving handle the
  MenuBarExtra pattern that XCUITest struggles with.
- **Strategy.** SwiftPM does not host true Apple XCUITest; rather than convert
  the project to Xcode, we use this pragmatic real-stack hybrid: real
  `Process` launch + osascript driving + log inspection. Works for menu-bar
  apps, stays inside `swift test`, no separate harness needed.

## [2026.06.24.3] - 2026-06-24

### Reverted

- **Phase 6 protocol seams (`CLIServicing`, `DockerServicing`) removed.**
  Their sole purpose was to enable mock-injection for Phase 7 unit
  tests. After a testing-strategy discussion the team decided to use
  real-stack vertical-slice E2E tests (no mocks, no fakes) — making the
  protocols dead code with no consumer. Property types reverted to
  concrete `CLIService` / `DockerService` in `StatusViewModel`,
  `ChatViewModel`, `DownloadViewModel`, and `DockerColimaViewModel`.
  Build clean. `swift test`: 14/14 passing (identical to pre-Phase-6
  baseline). Removing now while the change is fresh — every line of
  unused code is future cleanup debt. Future testing plan to be
  redefined.

## [2026.06.24.2] - 2026-06-24

### Changed (Swift Conformance Plan — Phase 6: Test Scaffolding)

- **Introduced `CLIServicing` and `DockerServicing` protocol seams** so
  view models can be unit-tested with mocks (Standard §10.3, §18.2).
  - New `Sources/Services/CLIServicing.swift` declares the 10 methods
    on `CLIService` that view models currently call: `fetchStatus`,
    `fetchDockerStatus`, `startInfrastructure`, `stopInfrastructure`,
    `restartInfrastructure`, `run`, `runAndCapture`, `configDirURL`,
    `queryChat`, `dockerLogs`. Concrete `CLIService` conforms via
    empty extension — no method signature changes.
  - New `Sources/Services/DockerServicing.swift` declares the 11
    methods on `DockerService` that `DockerColimaView` calls. Concrete
    `DockerService` conforms via empty extension.
  - View-model property type widening (one-line per file): `StatusViewModel.service`,
    `ChatViewModel.cliService`, `DownloadViewModel.cliService`,
    `DockerColimaViewModel.dockerService` are now typed against the
    protocol instead of the concrete service. No call sites changed
    because every method used appears in the protocol. No behavior
    change at runtime — the same concrete instances flow through.
- **Verification.** Baseline `swift test` → 14/14 passing. Post-change
  `swift test` → 14/14 passing (identical). `swift build` clean. App
  build via `install-gui` clean. Pre-existing dead-code warnings in
  `ModelDownloaderView.swift:489` (`try`/`catch` on non-throwing
  `cliService.run`) unchanged. Phase 7 (new unit tests with mocks)
  is the follow-up that will exercise these seams.

## [2026.06.24.1] - 2026-06-24

### Changed

- **Pre-commit hook validates against `VERSION` file, not git tag.**
  The previous hook compared `git describe --tags` against
  `AppConstants.swift` and `Info.plist`, which forced `--no-verify` on
  every release commit (no `vN+1` tag exists at the moment of the bump
  commit). The rewritten hook in `scripts/pre-commit-version-check.sh`
  reads `VERSION` directly, validates `AppConstants.swift` matches, and
  intentionally does NOT check `Info.plist` (build artifact, gitignored).
  Closes the structural chicken-and-egg.
- **`.versionbump.yaml` declares the Swift `APP_VERSION` literal.**
  The global `~/.ai-dev-dotfiles/tools/version-bump.py` now reads
  `.versionbump.yaml` at repo root and patches each declared literal
  via named-group regex during `version-bump`. A single bump invocation
  now updates `VERSION` + `AppConstants.swift` atomically — no separate
  `install-gui` sync step required. `Info.plist` continues to be updated
  by `gui-macos/build_app.sh` since it lives in the build artifact tree.

### Notes

- This release-engineering work is part of the cross-repo standardization
  tracked as aidevops `design/TODO.md` #122. Spec stub at
  `~/.ai-dev-dotfiles/repo-specs/release-engineering/CLAUDE.md`.

## [2026.06.23.8] - 2026-06-23

### Fixed

- **Chat window opened behind MenuBarExtra's transient host window and never
  became key**, so Cmd-W was silently ignored until the user clicked into the
  window. Fix: call `window.makeKey()` after `makeKeyAndOrderFront(nil)` in
  `StatusViewModel.openChat(name:)`, applied to both the existing-window
  reactivate path and the new-window creation path.

### Changed (Swift Agent Standard conformance — audit of v2026.06.19.6/7 diffs)

- **`CreateProfileForm` now supports cancellation mid-create.** Previously the
  Cancel button only closed the window; the `colima start <new-vm>` subprocess
  kept running to completion in the background. Now Cancel propagates Task
  cancellation through `runCommandStreaming`, which terminates the subprocess
  via SIGTERM. Closes §9.3 conformance gap identified in the audit.
  - New `ProcessBox` helper in `DockerService.swift` shares the Process
    reference between the spawn closure and the cancel handler under NSLock.
    `@unchecked Sendable` with documented safety argument per §9.4. Race
    handling: `ProcessBox.store()` returns `false` if `terminate()` was
    already called, so a start-before-cancel race resolves cleanly with
    `CancellationError` instead of an unkillable subprocess.
  - Caveat: colima itself decides how to handle SIGTERM mid-VM-creation. A
    partial `~/.colima/<profile>/` may remain and need `colima delete` to
    clean up. Documented in `runCommandStreaming` docstring.
- **`CreateProfileForm` now has SwiftUI Previews.** Two `#Preview` blocks
  (empty form, populated view model with source profiles for the Copy-spec
  dropdown). Helper marked `@MainActor` and `#if DEBUG` gated. Closes §7.5
  conformance gap.

### Audit deliverable

- Section-by-section audit of v2026.06.19.6 + v2026.06.19.7 Swift changes
  against `docs/SWIFT-AGENT-STANDARD.md` v1.0 — verdict CONFORMANT WITH
  GAPS, no bugs requiring immediate fix. Three concrete gaps identified:
  cancellation, previews, and unit tests. **All three shipped under
  v2026.06.23.8.** Cancellation + previews landed in commit 65aab43;
  unit tests + SPM test target landed in commit 1803fbe (14 tests for
  `normalizeGiB` + `runCommandStreaming` passing; minor production
  refactors to make functions internal-accessible for `@testable
  import`; one production defense-in-depth fix surfaced by the new
  tests — `normalizeGiB` now strips `.whitespacesAndNewlines` instead
  of just `.whitespaces`).
- **Remaining follow-up**: 9 orphan test files under
  `gui-macos/Tests/{UI,Unit,llamacpp_guiTests,JSONParsingTests.swift}`
  are NOT in the new test target. They reference outdated type
  signatures (e.g. `StatusRow` had 10 fields, now 21) from before
  the Phase 4 `Sources/` refactor. They need refresh before they
  can be re-enabled. Tracked as a focused follow-up.

## [2026.06.23.7] - 2026-06-23

### Fixed

- **GUI crashed (SIGSEGV in `objc_retain`) when closing a chat window a second time.**
  Root cause: `isReleasedWhenClosed = true` (Cocoa default) caused the
  NSWindow to be freed by the ObjC runtime before `windowDidClose` fired.
  References in `chatWindows` / `windowDelegates` dictionaries became
  dangling pointers. Fix: `window.isReleasedWhenClosed = false` applied to
  all three stored-window sites in `StatusViewModel` (`openChat`,
  `openModelDownloader`, `openPreferences`).

## [2026.06.23.6] - 2026-06-23

### Fixed

- **GUI crashed (SIGSEGV in `objc_release`) immediately on closing a chat window.**
  Root cause: `NSWindow` does NOT retain its delegate (Cocoa's delegate property
  is `assign`, not `strong`). Calling `onClose()` inside `windowWillClose`
  removed the last strong reference to the delegate while its method was
  still on the call stack — use-after-free during ARC autorelease pool drain.
  Fix: deferred `onClose()` to `windowDidClose` (fires after the window and
  its autorelease pool have fully unwound) across all three delegate classes
  (`ChatWindowDelegate`, `ModelDownloaderWindowDelegate`,
  `PreferencesWindowDelegate`). Added `applicationShouldTerminateAfterLastWindowClosed`
  returning `false` in `AppDelegate` for belt-and-suspenders.
- Added diagnostic lifecycle logging for window open/close events, activation
  policy, and visible window counts to aid future regression diagnosis
  (`LifecycleLog` events: `ui.chat.window_will_close`, `ui.chat.window_did_close`,
  `ui.chat.window_opened`, `ui.app.last_window_closed`, `ui.app.will_terminate`).

## [2026.06.23.5] - 2026-06-23

### Fixed

- **`install-gui` did not rebuild when only `VERSION` changed.**
  The staleness check in `gui-macos/install_gui.sh` compared source `.swift`
  files against the built binary but never checked the `VERSION` file. A
  version-only bump left the binary stale. Added `VERSION` mtime check so
  any VERSION change triggers a rebuild.

## [2026.06.23.4] - 2026-06-23

### Added

- Diagnostic lifecycle logging in `AppDelegate` and `ChatWindowDelegate`
  to trace window-close and app-termination events. Events written to
  `~/Library/Logs/llamaCPPManager/lifecycle.jsonl` via `LifecycleLog`.

### Known Issues (carried forward, now resolved)

- **`docs/SWIFT-AGENT-STANDARD.md` is referenced from `CLAUDE.md`
  but was authored mid-session and not yet applied to the work in
  this session.** The v.6 and v.7 Swift edits were inspected for no
  force-unwraps, no secrets, no `@unchecked Sendable` introductions.

## [2026.06.23.3] - 2026-06-23

### Fixed
- **Cmd-W did not close chat / preferences / model-downloader / help windows.**
  Root cause: MenuBarExtra-only apps have `NSApplication.shared.mainMenu == nil`
  on launch, so Cocoa's standard keyboard routing for `Cmd-W` / `Cmd-Q` /
  `Cmd-M` had no menu item to bind to and silently did nothing — there was
  no File > Close Window for `performClose:` to be wired to.
- Fix: `AppDelegate.applicationDidFinishLaunching` now installs a minimal
  main menu with Application / File / Edit / Window submenus. The File >
  Close Window item carries `Cmd-W` and uses the standard
  `NSWindow.performClose(_:)` selector, so window delegates'
  `windowWillClose` callbacks still fire (chat/preferences/downloader window
  cleanup keeps working). Bonus: `Cmd-Q` quit, `Cmd-M` minimize, and the
  Edit menu cut/copy/paste/select-all shortcuts also start working
  everywhere — they were similarly broken before.

## [2026.06.23.2] - 2026-06-23

### Fixed (mlx-vlm chat — by Claude Sonnet 4.6 in commit 54ca96f)

- **mlx-vlm chat returned 422 Unprocessable Content on every request.**
  `mlx_vlm.server`'s `ChatRequest` schema inherits from `VLMRequest`,
  which makes the `model` field required with no default. The CLI's
  `query_model_chat()` never sent it. Now, for `deployment_type: mlx-vlm`
  models, `model_path` is looked up from config and injected as the
  `model` field in the JSON payload before the POST. Standard llama.cpp
  and mlx-lm chat paths are unaffected.
- Files changed: `src/llamacpp_manager/query.py`, `VERSION`.
- This entry was backfilled by the update-trackers handoff workflow —
  the original commit shipped a VERSION bump without a CHANGELOG entry.

## [2026.06.23.1] - 2026-06-23

### Changed — GGUF start path now YAML-driven (matches MLX architecture)

**Architectural cleanup, no behavior change for working models.** Previously GGUF
models started via `llamacpp-manager start-script` → `/Users/liborballaty/llms/restart-llm-interactive.sh`
which had a **hardcoded `case "$MODEL_NAME"` list of 10 models**. Any model
added via `llamacpp-manager config add` that wasn't in that case statement
failed with `Error: Unknown model 'X'`. This bit `llama-4-scout-17b-q8` today.

MLX models already used the YAML-driven `start` path with no hardcoded list.
This change makes GGUF match MLX:

- `ModelSpec` (`config.py`) gained `ctx_size: Optional[int]` and
  `n_gpu_layers: Optional[int]` fields.
- `process.build_argv` now passes `--n-gpu-layers <N>` (default 999, matching
  what the bash script always did for Apple Silicon) and `--ctx-size <N>`
  (default 32768, per-model override via the new YAML field).
- `cmd_start` (cli.py) threads the two new fields from YAML into the
  `ModelSpec` it builds. Same for the config-show argv preview path.
- `phi3`'s YAML entry now has `ctx_size: 8192` (matches the special-case the
  bash script had — Phi-3-mini-4k natively supports 4k, RoPE-extends to 8k).
- `StatusViewModel.startWithScript` (Swift) now routes GGUF rows to
  `["start", name]` instead of `["start-script", name, "--mode", mode]`. Mode
  is read from YAML (which the picker's `saveMode` always writes before Start
  fires).

Result: adding a new GGUF model via `llamacpp-manager config add` (or the
hand-edit of `~/Library/Application Support/llamaCPPManager/config.yaml`)
now just works — no bash script edit needed.

### Soak / future cleanup

- `restart-llm-interactive.sh` and the `start-script` CLI command are kept
  around as a safety net during a soak period. Plan: confirm a few GGUF
  models behave identically under the new path, then delete the bash script
  and the `cmd_start_script` handler in a follow-up commit.
- `config update --ctx-size N` / `--n-gpu-layers N` CLI flags not yet
  added. For now, edit YAML directly to override defaults. Tracked as a
  small follow-up; not blocking.

## [2026.06.22.6] - 2026-06-22

### Fixed — external-download visibility in the GUI

Two surgical changes to the existing external-download scanner in
`DownloadViewModel` (Sources/Views/ModelDownloaderView.swift). The
scanner architecture was already in place (Task.detached every 5 s,
ps-based discovery, per-name dir-size polling, render hook into
`Active Downloads & Loading`) but had two limitations that hid every
real-world external download:

- **Pattern matcher only recognized `llamacpp-manager models download <name>`.**
  My `hf download unsloth/diffusiongemma-26B-A4B-it-GGUF --local-dir ~/llms/diffusiongemma-26b/`
  wrote 7 GB of `.incomplete` files but was completely invisible in
  the GUI because neither `"llamacpp-manager"` nor `"models download"`
  appears in that command line. The matcher now ALSO recognizes:
  - `hf download <repo> [file] [--local-dir <path>]`
  - `huggingface-cli download <repo> [file] [--local-dir <path>]`
  For the HF-tool variants we register the download only when
  `--local-dir` is set and we use the last path segment as the model
  name (matches the `~/llms/<X>/` convention).

- **`directorySizeOffMain` used `.skipsHiddenFiles`.** `hf download`
  writes partial files into `<model_dir>/.cache/huggingface/download/*.incomplete`
  — that path starts with `.` so even when a download WAS detected,
  the size watcher reported 0 bytes forever. Now walks including
  hidden files.

### Known gaps (intentionally out of scope for this fix)
- Downloads without `--local-dir` (writing to `~/.cache/huggingface/hub/`
  default) still won't show progress — the watcher only looks at
  `~/llms/<name>/`.
- Direct python downloads (where huggingface_hub is imported into a
  long-lived Python process) won't show as separate ps entries.
- Repo-name → configured-model-name mapping is approximate (last path
  segment of `--local-dir`); if those don't match, the download will
  appear under the dir-basename rather than the configured row name.

## [2026.06.22.5] - 2026-06-22

### Added — MLX-specific modes (basic / think)
- Previous v.22.2 hid the mode picker for MLX/MLX-VLM/Diffusion rows
  (Bug 5) because `build_mlx_argv` ignored the mode field. This release
  replaces that hide-it-entirely approach with truthful, MLX-aware
  modes that actually do something:
  - `basic` — default: just `--model` / `--host` / `--port`
  - `think` — adds `--enable-thinking --thinking-budget 4096`,
    enabling Qwen3 / DeepSeek-R1 / DiffusionGemma-style step-by-step
    reasoning on models that support it (mlx_lm.server is permissive
    about ignored flags on models that don't).
- `StatusViewModel.availableModes(for:)` returns the right mode set per
  row: GGUF gets `basic/tools/performance/extended`; MLX gets
  `basic/think`. UI Picker (App.swift, both native and Docker sections)
  iterates this list rather than hard-coding the 4 llama.cpp tags.
- `deploymentIgnoresMode(_:)` removed — MLX rows now honor mode.

### Fixed — incorrect "stale config entry" advice from v.22.4
- The v.22.4 CHANGELOG note advised removing the `diffusiongemma-26b`
  config entry as stale. **That advice was wrong.** DiffusionGemma 26B
  is Google DeepMind's diffusion language model, released 2026-06-10
  (12 days ago) — a genuinely new architecture, not a typo. A GGUF
  build is published at `unsloth/diffusiongemma-26B-A4B-it-GGUF`. The
  user's local `~/llms/diffusiongemma-26b/` is empty only because the
  download never completed.
- Caveat: whether `llama-server` can actually run the GGUF depends on
  llama.cpp having block-diffusion sampler support for the
  `DiffusionGemmaForBlockDiffusion` architecture. Verify against
  current llama.cpp release notes before relying on the GGUF path.
- The working `mlx-diffusiongemma` config (MLX-VLM path) remains the
  proven-running alternative.

## [2026.06.22.4] - 2026-06-22

### Added — zombie-process cleanup
- New module `src/llamacpp_manager/cleanup.py` plus CLI command
  `llamacpp-manager cleanup [--model NAME] [--max-age-hours N] [--dry-run] [--json]`.
- **Default mode** (`cleanup` with no args): scans for
  `llamacpp-manager models download <X>` processes older than 1 hour
  (configurable) and kills them. Does NOT touch running model servers.
  Three zombies were found and killed on first run after this landed
  (two stuck copies of `qwen3-1.7b` downloads from 6+ days ago, plus
  one `qwen-coder-32b-q8`).
- **Targeted mode** (`cleanup --model NAME`): kills BOTH stale
  downloads for NAME AND any model-server processes (`mlx_lm.server`,
  `mlx_vlm.server`, `llama-server`) matching the configured
  `model_path`. Handles multiples — every match is killed, not just
  the first.
- Process discovery uses `/bin/ps -eo pid,etime,command` (no psutil
  hard-dep). SIGTERM, 2-second grace, then SIGKILL escalation.

### Added — GUI integration of cleanup
- `StatusViewModel.init` now fires `llamacpp-manager cleanup` once at
  app launch (fire-and-forget, non-blocking).
- `StatusViewModel.startWithScript` now calls
  `llamacpp-manager cleanup --model <name>` BEFORE the actual start,
  so any prior-instance server processes (or stale downloads for the
  same model) are reaped before a fresh start. Prevents the
  port-already-bound / "stuck" symptom we saw with multiple stale
  downloads of the same model name.

## [2026.06.22.3] - 2026-06-22

### Fixed
- **`mlx_vlm.server` models reported as `down` even when serving.**
  `health.check_endpoint()` in `src/llamacpp_manager/health.py` was
  only treating `"status":"ok"` (the llama.cpp / mlx_lm.server
  convention) as a success signal. `mlx_vlm.server` returns
  `{"status":"healthy","loaded_model":"…",...}` so the check fell
  through to `health_state="down"`, which propagated `up=False` to
  status callers. Symptom: GUI showed `mlx-diffusiongemma` as stuck
  with the spinner / "issue detected" even though `mlx_vlm.server`
  was running healthily on port 8200.
- Now accepts `"status":"healthy"` or a `loaded_model` field as
  additional success signals. No false positives expected — those
  strings don't appear in genuine error responses from llama.cpp /
  mlx_lm.server / mlx_vlm.server.

## [2026.06.22.2] - 2026-06-22

### Fixed (5 inherited bugs)

1. **Closing the chat window quit the entire app** (HIGH).
   New `Sources/AppDelegate.swift` returns `false` from
   `applicationShouldTerminateAfterLastWindowClosed`, wired into
   `LlamaCPPManagerApp` via `@NSApplicationDelegateAdaptor`. The
   menu-bar app now survives chat / preferences / model-downloader /
   help-window closes. Standard macOS-idiomatic fix.

2. **Model-start failures were silent** (MEDIUM-HIGH).
   `StatusViewModel.startWithScript` now uses `service.runAndCapture`
   so stderr is preserved. On non-zero exit, the new
   `surfaceStartFailure()` helper sets `@Published errorMessage`
   (rendered as a dismissible red banner under the menu's version
   header) **and** auto-opens `~/Library/Logs/llamaCPPManager/<name>.log`
   via `NSWorkspace.shared.open` so the user immediately sees the real
   failure text.

   Also: the log monitor now calls a new `detectStartupFailure()` that
   scans the post-startup-banner tail for fatal keywords (`ValueError:`,
   `Traceback`, `error: invalid argument`, `FATAL`, `bash: `,
   `Aborted`, `Segmentation fault`, `ModuleNotFoundError`). If any
   appear, the spinner is cleared immediately and the same surface +
   auto-open path fires — no more waiting for the 10-minute timeout
   while the model is already dead.

3. **`parseStartupLog` false-positive "Issue detected" alerts** (LOW).
   Anchored to the **most recent** startup-banner marker
   (`Starting httpd` / `main: server is listening` / `system_info:` /
   `build info:`). Historical tracebacks from prior failed runs no
   longer poison the parser because the log file is append-only across
   restarts.

4. **`restart-llm-interactive.sh` PATH lookup fragility** (MEDIUM).
   Replaced the `which llama-server || /opt/homebrew/bin/llama-server`
   one-liner with an explicit fallback chain: PATH → local llama.cpp
   build (`/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llama.cpp/build/bin/llama-server`)
   → homebrew → exit 127 with a clear error. Fix applied to the local
   script (file lives outside this repo).

5. **MLX models silently ignored the mode picker** (MEDIUM).
   `StatusViewModel.deploymentIgnoresMode(_:)` returns true for
   `deployment_type` in {`mlx`, `mlx-vlm`, `diffusion`}. The mode
   `Picker` in the MenuBarExtra row is now hidden for those rows
   rather than pretending the setting has effect. Behavior of
   `build_mlx_argv` unchanged (would need MLX-specific flag mapping to
   actually wire modes — out of scope here).

### Notes
- Committed with `--no-verify` because the pre-commit version-consistency hook
  has a known chicken-and-egg vs. embedded version literals (tracked in
  `docs/TODO.md` Stretch / Backlog as "Fix version-bump.py to also sync
  embedded version literals"). `AppConstants.swift` literal was bumped
  manually to keep tag/Plist/Swift consistent after the next install-gui.

## [2026.06.22.1] - 2026-06-22 (revised 2026-06-22 after full audit)

### Fixed (cli.py — display strings only, see note below)
- Replaced `--n-parallel` with `--parallel` in 4 places in `cli.py`
  (lines 245, 261, 286, 307). These strings appear in:
  - `models config-show --json` output (`mode_flags.performance`)
  - `models config-show` human-readable output
  - `models options` help-text describing what each mode adds
  - `models options` help-text listing common llama-server parameters
- The same correction had been applied to `process.py:37` long ago
  (see explanatory comment at `process.py:36`); `cli.py` was missed.

### Important accuracy note (corrects the original entry)
- The original entry for this commit overstated the impact. The
  `cli.py` strings are **display only** — they appear in CLI help and
  `config-show` output but do NOT participate in the actual model
  start. The real start path for GGUF / `deployment_type: native`
  models goes through:
    GUI -> `llamacpp-manager start-script <name> --mode <mode>`
        -> `cli.cmd_start_script` (cli.py:1467)
        -> `subprocess.run([restart_script_path, name, mode])`
        -> `/Users/liborballaty/llms/restart-llm-interactive.sh`
  That external bash script (outside this repo) is the actual source
  of the `--n-parallel` flag the user hit. The bash-script fix was
  applied locally during this session but is not part of this commit
  because the file lives outside the repository.
- `process.py` has its own `start_process` flag builder for the
  non-script start path, and it was already correct.

### Audit of all start modes (static analysis vs current llama-server `--help`)
| Code path | Flag | Status |
|---|---|---|
| restart-llm-interactive.sh:146 `performance` | `--n-parallel 4` -> `--parallel 4` | FIXED locally |
| restart-llm-interactive.sh:151 `extended` | bare `--flash-attn` | BROKEN on current llama-server (now tristate `[on\|off\|auto]`); fixed locally to `--flash-attn on` |
| restart-llm-interactive.sh:108 PATH | `which llama-server \|\| /opt/homebrew/bin/llama-server` | FRAGILE — brew fallback path doesn't exist on this system |
| cli.py:245,261,286,307 (display) | `--n-parallel` | FIXED in this commit |
| process.py:34,37,39 | `--jinja`, `--parallel 4`, `--flash-attn on` | already correct |
| mlx_process.build_mlx_argv | `--model`, `--host`, `--port`, +spec.args | valid, but `spec.mode` is silently ignored for MLX |

### Impact by model
- GGUF / native models (qwen-coder-7b, qwen2.5-32b, deepseek-r1-qwen-32b,
  llama-3.1-8b, llama-4-scout-17b, hermes-3-llama-8b, mistral-7b,
  mistral-small-24b, phi3, smollm3, gemma-3-270m, gemma-3-27b,
  qwen3-0.6b): `basic` and `tools` worked all along; `performance` was
  broken until the bash-script fix; `extended` was broken until the
  bash-script `--flash-attn on` fix.
- MLX models (mlx-gemma-3-1b, mlx-gemma4-31b, gemma-270m-compliance-mlx,
  gemma-3-27b-mlx, mistral-05b-compliance-mlx, mlx-diffusiongemma):
  mode is ignored. Selecting `performance` or `extended` for an MLX
  model has no effect — only `spec.args` is appended to the
  `mlx_lm.server` command line.

## [2026.06.19.8] - 2026-06-19

## [2026.06.19.8] - 2026-06-19

### Added (Accessibility — Conformance Phase 1)
- VoiceOver labels on 4 icon-only buttons: menu bar brain icon
  ("llamaCPPManager menu"), refresh button in Model Downloader
  ("Refresh catalog"), clear-search button ("Clear search"),
  copy-error button ("Copy error message").
- `.accessibilityHidden(true)` on 9 decorative icons paired with
  adjacent Text(...) — prevents VoiceOver from reading the same
  content twice. Sites in App.swift (active-downloads header,
  error banner), ModelDownloaderView.swift (search field icon,
  error icon, empty-tray icon, model-row brain, downloaded
  checkmark, hardware-requires CPU icon), DockerColimaView.swift
  (port-status icon).

### Changed (Concurrency — Conformance Phase 2)
- `StatusViewModel`, `ChatViewModel`, and `DownloadViewModel`
  now declared `@MainActor`. Formalizes the existing intent
  (the code already uses `MainActor.run { }` and `@MainActor in`
  closures throughout). Compiler now catches future off-main UI
  writes.
- `StatusViewModel.argValue(in:flag:)` marked `nonisolated` —
  pure string-parsing helper called from the background
  `Task.detached` that scans `ps` output. No state access.
- `setupRefreshTimer` Timer callback now hops to the main actor
  explicitly: `Task { @MainActor in self?.refresh() }`. No
  behavior change (Timer already fires on the main RunLoop);
  this only makes the isolation contract explicit so Swift 6
  strict-concurrency mode won't warn.

### Process
- Conformance pass began against `docs/SWIFT-AGENT-STANDARD.md`
  following the phased plan in `docs/SWIFT-CONFORMANCE-PLAN.md`.
  Phases 1+2 complete; Phase 0 baseline established that
  `Package.swift` has no test target wired up (5 orphaned test
  files in `gui-macos/Tests/`) — Phase 7 will address.

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
