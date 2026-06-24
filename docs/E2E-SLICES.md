# E2E Vertical-Slice Tests — Contract & How To Run

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/E2E-SLICES.md
**Description:** Contract for the real-stack vertical-slice E2E tests under `gui-macos/Tests/E2E/`. Each slice exercises one user-visible flow end-to-end with no mocks, no fakes, and no protocol seams.
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2026-06-24
**Last Updated:** 2026-06-24
**Last Updated By:** Libor Ballaty

---

## What a slice is

A slice is one Swift Testing `@Test` function that:

1. Starts at "user opens the app" (screen 0).
2. Drives the running app the way a user would — clicks, keystrokes, menu navigation.
3. Asserts the resulting state via inspection of the existing `LifecycleLog` JSON log at `~/Library/Logs/llamaCPPManager/lifecycle.jsonl` and (where applicable) accessibility queries.
4. Uses the real installed `/Applications/llamaCPP Manager.app`, the real Python `llamacpp-manager` CLI, real subprocesses, and real model servers wherever those are part of the flow being tested.

No mocks. No fakes. No protocol seams. Hard-to-trigger failure modes (subprocess hang, OOM, network partition) are accepted as untested in CI and rely on structured `CLIError` + `LifecycleLog` for incident debuggability.

## Strategy: why osascript + log inspection

SwiftPM does not host true Apple XCUITest — the canonical UI-testing framework lives in Xcode projects with separate test bundles and signing. Rather than convert this project to an Xcode project, slices use a pragmatic hybrid:

- **Launch:** `Process` invokes `/Applications/llamaCPP Manager.app/Contents/MacOS/llamacpp-gui` directly.
- **Drive:** `/usr/bin/osascript` runs AppleScript / System Events for clicks, keystrokes, menu navigation. This works for MenuBarExtra apps, which XCUITest struggles with.
- **Assert:** Read `~/Library/Logs/llamaCPPManager/lifecycle.jsonl` for `LifecycleLog` events emitted by production code. No test-only hooks in production.

All shared helpers live in `gui-macos/Tests/E2E/E2EHelpers.swift`.

## Current slices

### Slice A — App Launch & Boot (`SliceA_LaunchTests.swift`)

**Runs in:** default `swift test` (no opt-in needed).
**Setup required:** app installed via `llamacpp-manager install-gui`. The `llamacpp-manager` CLI must be on PATH and the user must have at least one model configured (any model — the slice only asserts that a status fetch completes with non-negative counts).

**Tests:**
1. `appLaunchEmitsDidFinishLaunching` — launches the app, waits for `ui.app.did_finish_launching` in the log.
2. `firstStatusRefreshCompletes` — additionally waits for `cli.status.fetched` and asserts `model_count` + `infrastructure_count` fields exist and are non-negative.

**Runtime:** ~7 seconds.

### Slice B — Chat Window Open + Cmd-W Close (`SliceB_ChatWindowTests.swift`)

**Runs in:** opt-in only (`RUN_E2E_INTERACTIVE=1 swift test`).
**Setup required:** all of Slice A's setup, plus:
- One-time grant: System Settings → Privacy & Security → Accessibility → enable for whichever process runs `swift test` (Terminal, iTerm, Xcode, VS Code, etc.). Without this, `osascript` cannot drive the UI and the slice is skipped with a clear message.
- At least one configured model so the menu has a row with a "Chat" button.

**Test:** `openChatThenCmdW` — opens the menu bar popover, clicks the first "Chat" button, waits for `ui.chat.window_opened`, sends Cmd-W, waits for `ui.chat.window_did_close`. This is the regression test for the v2026.06.23.7 / .8 window-lifecycle fixes (use-after-free crash, releaseWhenClosed crash, makeKey focus bug).

**Runtime:** ~5 seconds when actually running.

### Slice C — Chat Send + Receive (`SliceC_ChatSendReceiveTests.swift`)

**Runs in:** opt-in only (`RUN_E2E_INTERACTIVE=1 swift test`).
**Setup required:** all of Slice B's setup, plus:
- A model server actually running so the chat request can be served. The model can be any GGUF or MLX model configured via `llamacpp-manager config add ...` and started via `llamacpp-manager start <name>`. No specific test model is required — the slice asserts only that *some* non-empty reply arrives.

**Test:** `sendChatGetReply` — opens chat window, types "hi", presses Return, waits for `cli.chat.reply_received` log event with a positive `reply_length`. Real CLI → real subprocess → real llama.cpp/MLX server → real network → real response.

**Runtime:** depends on model latency. Timeout is 60 seconds.

## How to run

### Default run (CI-safe — Slice A only)

```bash
cd gui-macos
swift test
```

Slices B and C will print a SKIPPED message and pass instantly.

### Full interactive run (local dev only)

1. Grant Accessibility permission to your terminal once (System Settings → Privacy & Security → Accessibility → add your terminal/IDE).
2. Ensure you have at least one model configured: `llamacpp-manager config list`.
3. For Slice C, ensure at least one model is *running*: `llamacpp-manager start <name>`.
4. Run with the opt-in flag:

```bash
cd gui-macos
RUN_E2E_INTERACTIVE=1 swift test
```

### Filter to a single slice

```bash
swift test --filter SliceA
RUN_E2E_INTERACTIVE=1 swift test --filter SliceB
RUN_E2E_INTERACTIVE=1 swift test --filter SliceC
```

## Adding a new slice

1. Identify a user flow that exercises something the existing slices don't cover.
2. Decide whether the flow needs accessibility/UI driving. If yes → gate behind `interactiveSlicesEnabled` like B and C. If no → ship in default run like A.
3. If the flow needs a new deterministic signal (a specific moment to assert "this user-visible thing happened"), add a `LifecycleLog.log(...)` call in production code at the right point. Don't add test-only hooks.
4. Write the slice in `Tests/E2E/SliceX_YourName.swift` using the helpers in `E2EHelpers.swift`.
5. Document it in this file.

## What slices intentionally do NOT cover

- **Subprocess hang / OOM / network partition** — hard to trigger reliably; rely on `LifecycleLog` coverage + structured `CLIError` in production for incident debuggability.
- **Visual regression / screenshot diffs** — out of scope for this style of test.
- **CI without a display** — slices that launch a GUI app cannot run on headless CI. If headless coverage is wanted later, the Python CLI side already has `pytest tests/` which is fully real-stack and headless.

## Related

- `docs/SWIFT-AGENT-STANDARD.md` §4.4 — project caveat noting this codebase rejects mock-based tests.
- `docs/SWIFT-CONFORMANCE-PLAN.md` §9, §10 — both marked SUPERSEDED 2026-06-24 with forward pointers here.
- `docs/TODO.md` — entry tracking the full rewrite of the standard's testing sections.

---

Questions: libor@arionetworks.com
