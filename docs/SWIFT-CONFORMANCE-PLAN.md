# Swift Conformance Pass — Execution Plan

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/SWIFT-CONFORMANCE-PLAN.md
**Description:** Step-by-step plan to bring `gui-macos/` into conformance with [docs/SWIFT-AGENT-STANDARD.md](SWIFT-AGENT-STANDARD.md). Designed so each phase is independently shippable and guaranteed not to break existing functionality.
**Author:** Libor Ballaty <libor@arionetworks.com> (drafted by Claude agent)
**Created:** 2026-06-19
**Last Updated:** 2026-06-19
**Last Updated By:** Libor Ballaty (via Claude agent)
**Status:** DRAFT — awaiting operator approval before execution.

---

## 0. Non-Break Guarantees (apply to every phase)

These rules are mandatory for every change made under this plan. They are the operator's stated condition for approval: **no existing function will be broken**.

1. **No symbol renames.** Class, struct, enum, method, property, and case names stay byte-identical. The only exception is intentionally renaming a method to break a bad pattern, which is explicitly out of scope for this plan.
2. **No behavior changes.** Logic, control flow, conditionals, sequencing, side effects, and error handling stay the same. The plan is a *structural* and *additive* refactor only.
3. **No API surface changes.** `internal` stays `internal`. Nothing becomes `private` that wasn't already, and nothing becomes `public` that wasn't already.
4. **No deletions in this pass.** Code moves between files but is not removed (with one allowed exception: removing a `private` qualifier on a type so it can move to another file — see §2.3).
5. **Every phase ends with `llamacpp-manager install-gui --force` passing** (build succeeds, app launches, menu bar icon appears). If a phase fails the build, the phase is reverted, root cause documented, and re-planned before retry. No partial-broken commits.
6. **Every phase ends with the existing test suite passing.** `cd gui-macos && swift test` must succeed with the same set of tests passing as before the phase started. New tests are added in Phase 7 only; phases 1–6 do not change test pass/fail status.
7. **Manual smoke-test checklist runs after each phase.** Defined in §10. Operator confirms before next phase begins.
8. **Each phase is one git commit.** Phases are independently revertable. If a defect is found two phases later, `git revert` of the offending phase is the recovery path.
9. **No signing / entitlements / bundle ID / deployment target / `Package.swift` `path:` changes.** The Swift Package target stays `path: "Sources"` — moving files into subfolders is legal per the standard SPM behavior verified in inventory §9.
10. **`build_app.sh` ABOUT_FILE reference is updated atomically** with any move of `App.swift` (inventory §10 flagged this as the only hardcoded source path in build scripts). In this plan, `App.swift` does **not** move — only shrinks. So `build_app.sh` requires no edits.

---

## 1. Scope and Source of Truth

This plan executes the five top-priority remediation items identified in the conformance audit (delivered in the same session that produced this doc):

| # | Item | Audit severity | Phase |
|---|------|----------------|-------|
| 1 | App.swift oversized (2,732 lines) → extract per inventory | HIGH | 3, 4 |
| 2 | Missing `@MainActor` on `StatusViewModel`, `ChatViewModel`, `DownloadViewModel` | MEDIUM | 2 |
| 3 | 13 icon-only buttons missing `.accessibilityLabel(...)` | HIGH | 1 |
| 4 | Flat folder structure → `Sources/{Models,Views,ViewModels,Services,...}/` | MEDIUM | 3 (folder moves), 4 (new files land in folders) |
| 5 | Sparse test coverage; no mock services | HIGH | 6 (test scaffolding), 7 (tests) |

Authoritative inputs:
- The structural inventory of `App.swift` (table of 22 top-level declarations with line ranges, dependencies, and suggested target files) — produced this session.
- The accessibility-button inventory (13 sites across 3 files) — produced this session.
- [docs/SWIFT-AGENT-STANDARD.md](SWIFT-AGENT-STANDARD.md) sections referenced inline.

If the inventory ever conflicts with the actual code, the code wins and the plan is revised before execution.

---

## 2. Phase Sequence Overview

Phases are ordered low-risk → high-risk. Each adds value standalone; you can stop after any phase.

| Phase | Title | Risk | Est. effort | Reversible? | Standard refs |
|-------|-------|------|-------------|-------------|---------------|
| 0 | Pre-flight baseline | — | 30 min | n/a | §3, §19 |
| 1 | Accessibility labels (13 sites) | Low | 1 h | Yes | §15.2 |
| 2 | `@MainActor` on view models | Low | 1 h | Yes | §8.1, §9.2 |
| 3 | Folder reorganization (existing files only) | Medium | 2 h | Yes (git mv) | §5.1 |
| 4 | App.swift extraction (split into ~15 files) | Medium-High | 4–6 h | Yes (revert) | §5.1, §7.2 |
| 5 | StatusViewModel decomposition *(OPTIONAL / DEFERRABLE)* | High | 4–6 h | Yes | §7.1, §8 |
| 6 | Test scaffolding: mock services + protocols | Medium | 2 h | Yes | §10.3, §18.2 |
| 7 | New unit tests | Low | 3–4 h | Yes | §18.2 |

**Total estimated effort:** 17–22 h (Phase 5 included) / 13–16 h (Phase 5 deferred).

**Recommendation:** execute phases 0–4, 6, 7 in this pass. Defer Phase 5 until after the structural refactor settles — splitting `StatusViewModel` is the only phase that *changes* the class graph (vs. just moving symbols between files) and is the highest-risk change. Decoupling it from this plan keeps the no-break guarantee tractable.

---

## 3. Phase 0 — Pre-flight Baseline

**Goal:** Establish a recorded baseline so we can prove no-break after each phase.

### Steps
1. From repo root, run `git status` — must be clean before starting (the plan commit itself excepted).
2. Capture baseline build: `cd gui-macos && swift build 2>&1 | tee /tmp/swift-conformance-baseline-build.log`. Result must succeed.
3. Capture baseline tests: `cd gui-macos && swift test 2>&1 | tee /tmp/swift-conformance-baseline-tests.log`. Record pass/fail count and the names of any failing tests as the **pre-existing failure set**. Per §2 of the standard, agent records pre-existing failures; subsequent phases are only required to not *worsen* this set.
4. Capture line counts: `wc -l gui-macos/Sources/*.swift` → save to `/tmp/swift-conformance-baseline-loc.txt` for before/after comparison.
5. Run `llamacpp-manager install-gui --force` and confirm the rebuilt menu-bar app launches and shows the brain icon. This is the **functional baseline**.
6. Operator confirms baseline OK before Phase 1 starts.

### Exit criteria
- Baseline logs exist.
- Functional baseline confirmed by operator.
- No code changed.

---

## 4. Phase 1 — Accessibility Labels (Standard §15.2)

**Goal:** Add `.accessibilityLabel(...)` (and where appropriate `.accessibilityHint(...)`) to all 13 icon-only `Image(systemName:)` call sites identified in the inventory.

### Sites (file:line — system image — proposed label)

| File | Line | systemName | Proposed `.accessibilityLabel` | Optional `.accessibilityHint` |
|------|------|-----------|---------------------------------|--------------------------------|
| `App.swift` | 129 | `arrow.down.circle.fill` | `"Active downloads section"` | — |
| `App.swift` | 756 | `brain.head.profile` | `"llamaCPPManager menu"` | `"Opens the model management menu"` |
| `App.swift` | 2610 | `exclamationmark.triangle` | `"Error"` | — |
| `ModelDownloaderView.swift` | 644 | `arrow.clockwise` | `"Refresh catalog"` | — |
| `ModelDownloaderView.swift` | 659 | `magnifyingglass` | `"Search"` | — |
| `ModelDownloaderView.swift` | 665 | `xmark.circle.fill` | `"Clear search"` | — |
| `ModelDownloaderView.swift` | 728 | `exclamationmark.triangle` | `"Error"` | — |
| `ModelDownloaderView.swift` | 740 | `doc.on.doc` | `"Copy model info"` | — |
| `ModelDownloaderView.swift` | 769 | `tray` | `"No models available"` | — |
| `ModelDownloaderView.swift` | 812 | `brain.head.profile` | `"Model"` | — |
| `ModelDownloaderView.swift` | 830 | `checkmark.circle.fill` | `"Downloaded"` | — |
| `ModelDownloaderView.swift` | 882 | `cpu` | `"Hardware requirements"` | — |
| `DockerColimaView.swift` | 280 | `minus.circle` / `network` | `"Port status"` | — |

### Safety
- These are pure additive modifiers. They cannot change layout, identity, or behavior.
- Line numbers in the table are approximate — implementer must locate each site by `systemName` string and context, not by line number alone.

### Verification
1. `swift build` succeeds.
2. `swift test` shows the same pass/fail set as baseline.
3. `llamacpp-manager install-gui --force` launches; menu icon appears.
4. Manual: enable VoiceOver (Cmd-F5) and confirm the menu bar icon now announces "llamaCPPManager menu" instead of generic "image".

### Commit message
`accessibility: add labels to 13 icon-only buttons (Standard §15.2)`

---

## 5. Phase 2 — `@MainActor` Annotations (Standard §8.1, §9.2)

**Goal:** Add `@MainActor` to view models whose `@Published` properties drive UI updates.

### Changes
| File | Symbol | Current | New |
|------|--------|---------|-----|
| `App.swift:883` | `StatusViewModel` | `final class StatusViewModel: ObservableObject` | `@MainActor final class StatusViewModel: ObservableObject` |
| `App.swift:2500` | `ChatViewModel` | `final class ChatViewModel: ObservableObject` | `@MainActor final class ChatViewModel: ObservableObject` |
| `ModelDownloaderView.swift:89` | `DownloadViewModel` | `final class DownloadViewModel: ObservableObject` | `@MainActor final class DownloadViewModel: ObservableObject` |

### Safety / no-break analysis
Adding `@MainActor` to a class isolates *all* its members to the main actor. This **can** trigger compile errors if a method was being invoked from a background context without `await` — that is, the compiler will surface latent thread-safety bugs.

**Risk assessment from inventory:**
- `StatusViewModel` already uses `MainActor.run { ... }` blocks (App.swift:1102) and explicit `@MainActor in` closures (App.swift:2532, ModelDownloaderView.swift:250, 335) for cross-actor handoffs. Suggests the author already treats it as main-isolated. Adding `@MainActor` should largely cement existing intent.
- The one detached background task (`Task.detached(priority: .background)` at App.swift:966 for external server scanning) calls back via `applyExternalServerScan()` which is already `@MainActor` (App.swift:1026). After `@MainActor` is added to the class, the call site must hop with `await`. If the call isn't already awaited, the build will fail — fixable by adding `await` inside the detached task body.

### Sub-steps
1. Add `@MainActor` to all three classes.
2. Run `swift build`. If errors:
   - Any method call from a non-isolated context (e.g. inside `Task.detached`) gains `await`.
   - Any `nonisolated` method that legitimately runs off-main is annotated `nonisolated`. From the inventory, `CLIService` runs subprocess work and is *not* a view model — so should not be marked `@MainActor`; it stays as-is.
3. If a build error reveals a real concurrency bug (e.g. UI state mutated from a background thread), STOP. Document the bug. Operator decides whether to fix it here or open a separate ticket and revert this phase.

### Verification
1. `swift build` succeeds.
2. `swift test` shows the same pass/fail set as baseline.
3. `llamacpp-manager install-gui --force`. Smoke-test: refresh, start a model, open chat, watch active downloads update — all UI updates land without hangs or crashes.

### Commit message
`concurrency: mark view models @MainActor (Standard §8.1, §9.2)`

---

## 6. Phase 3 — Folder Reorganization (Existing Files Only)

**Goal:** Move existing `.swift` files into the folder structure recommended by Standard §5.1 *without* splitting any file yet. Just `git mv`.

### Why this phase exists separately from Phase 4
Splitting `App.swift` (Phase 4) and reshuffling folders (Phase 3) are independently risky. Doing them together makes a bad commit much harder to bisect. Phase 3 is a pure `git mv` set — Git records renames, diffs are clean, and no source contents change.

### File moves
Per Package.swift inventory §9, the target is `path: "Sources"` with no exclude/sources list, so SPM picks up `.swift` files recursively. Subfolders are safe.

| From | To |
|------|-----|
| `Sources/App.swift` | `Sources/App.swift` *(stays — see §0 guarantee #10)* |
| `Sources/ModelDownloaderView.swift` | `Sources/Views/ModelDownloaderView.swift` |
| `Sources/DockerColimaView.swift` | `Sources/Views/DockerColimaView.swift` |
| `Sources/PreferencesView.swift` | `Sources/Views/PreferencesView.swift` |
| `Sources/GeneralPreferencesView.swift` | `Sources/Views/GeneralPreferencesView.swift` |
| `Sources/DisplayPreferencesView.swift` | `Sources/Views/DisplayPreferencesView.swift` |
| `Sources/AdvancedPreferencesView.swift` | `Sources/Views/AdvancedPreferencesView.swift` |
| `Sources/PreferencesManager.swift` | `Sources/Managers/PreferencesManager.swift` |
| `Sources/DockerService.swift` | `Sources/Services/DockerService.swift` |

### Safety
- Swift module is flat — type visibility is unchanged by moving files within the same target.
- No `import` statements change (the project is one module).
- `git mv` preserves history.
- `build_app.sh` references `Sources/App.swift` (line 47) which stays at its current path.

### Verification
1. `swift build` succeeds.
2. `swift test` shows the same pass/fail set as baseline.
3. `git log --follow gui-macos/Sources/Views/ModelDownloaderView.swift` shows history continuity.
4. `llamacpp-manager install-gui --force` launches.

### Commit message
`refactor: organize Sources/ into Models/Views/Services/Managers folders (Standard §5.1)`

---

## 7. Phase 4 — App.swift Extraction (Move-Only Splits)

**Goal:** Split `App.swift` (2,732 lines) into ~15 files. Each move is a cut-and-paste of one or more top-level declarations from `App.swift` to a new file in an appropriate folder. **No symbol changes, no logic changes.**

### Scope boundary
This phase moves *whole top-level declarations* between files. It does **not** split any class or struct internally. `StatusViewModel` stays as one ~1,323-line class in `ViewModels/StatusViewModel.swift`. Decomposing `StatusViewModel` itself is Phase 5 (deferrable).

### Extractions

The table below comes directly from inventory §1. Line ranges are *original line numbers in App.swift before any change* — the implementer uses them to locate each block; they do not need to match after extraction.

| Order | Symbol | Original lines | New file | Folder |
|-------|--------|----------------|----------|--------|
| 4.1 | `APP_VERSION` global | 6–8 | `AppConstants.swift` | `Sources/` |
| 4.2 | `formatDownloadETA` global func | 69–75 | `Formatting.swift` | `Sources/Utils/` |
| 4.3 | `LifecycleLog` enum | 15–66 | `LifecycleLog.swift` | `Sources/Logging/` |
| 4.4 | `AppLogger` enum | 78–106 | `AppLogger.swift` | `Sources/Logging/` |
| 4.5 | `StatusRow` struct | 779–807 | `StatusRow.swift` | `Sources/Models/` |
| 4.6 | `InfrastructureRow` struct | 809–824 | `InfrastructureRow.swift` | `Sources/Models/` |
| 4.7 | `AnyCodable` struct | 827–859 | `AnyCodable.swift` | `Sources/Models/` |
| 4.8 | `LoggingConfig` struct | 861–866 | `LoggingConfig.swift` | `Sources/Models/` |
| 4.9 | `StatusResponse` struct | 868–872 | `StatusResponse.swift` | `Sources/Models/` |
| 4.10 | `ModelStartupProgress` struct | 876–881 | `ModelStartupProgress.swift` | `Sources/Models/` |
| 4.11 | `ChatMessage` struct | 2493–2498 | `ChatMessage.swift` | `Sources/Models/` |
| 4.12 | `CLIError` enum | 2210–2226 | `CLIError.swift` | `Sources/Errors/` |
| 4.13 | `CLIService` class | 2228–2488 | `CLIService.swift` | `Sources/Services/` |
| 4.14 | `StatusViewModel` class | 883–2206 | `StatusViewModel.swift` | `Sources/ViewModels/` |
| 4.15 | `ChatViewModel` class | 2500–2556 | `ChatViewModel.swift` | `Sources/ViewModels/` |
| 4.16 | `ChatView` struct | 2558–2646 | `ChatView.swift` | `Sources/Views/` |
| 4.17 | `ChatMessageView` struct | 2648–2693 | `ChatMessageView.swift` | `Sources/Views/` |
| 4.18 | `ChatWindowDelegate` class | 2695–2706 | `ChatWindowDelegate.swift` | `Sources/Delegates/` |
| 4.19 | `ModelDownloaderWindowDelegate` class | 2708–2719 | `ModelDownloaderWindowDelegate.swift` | `Sources/Delegates/` |
| 4.20 | `PreferencesWindowDelegate` class | 2721–2732 | `PreferencesWindowDelegate.swift` | `Sources/Delegates/` |
| — | `LlamaCPPManagerApp` struct | 111–777 | **stays** in `App.swift` | `Sources/` |

After Phase 4, `App.swift` contains only `LlamaCPPManagerApp` + its imports — roughly **~670 lines** (the SwiftUI scene + `MenuBarExtra` body). Standard §7.2 still says "break up when `body` is difficult to read" — that's Phase 5's concern.

### Per-extraction recipe
For each row in the table:
1. Create the new file with the standard file header (Markdown-style adapted for Swift comments per the global standard):
   ```swift
   //
   //  <name>.swift
   //  llamacpp-gui
   //
   //  File: <absolute path>
   //  Description: <one-line purpose from inventory>
   //  Author: Libor Ballaty <libor@arionetworks.com>
   //  Created: <date moved>
   //
   ```
2. Add the minimum imports needed by the moved code:
   - SwiftUI types → `import SwiftUI`
   - AppKit delegates → `import AppKit`
   - Logging → `import os.log`
   - `Combine` only when `@Published`/`Cancellable` is used
3. Cut the declaration from `App.swift`.
4. Paste into the new file, preserving formatting verbatim.
5. Run `swift build` after **each** extraction. If it fails, the only acceptable fix is adding a missing `import` or fixing access level if a `private` qualifier blocks cross-file access (none expected — the inventory found no file-level `private` extensions).
6. Stage the change (`git add -A`) but do not commit until the whole phase is done.

### Ordering rationale
The order in the table is dependency-leaf-first:
- Globals and pure-data structs first (no dependencies).
- Models next.
- Errors before services that throw them.
- Services before view models that use them.
- View models before views.
- Delegates last (smallest, isolated).

This ordering means every intermediate `swift build` succeeds.

### Special case: private nested helpers
The inventory found no file-private extensions or nested helpers that would block extraction. If during execution an implementer hits a private member referenced cross-class, the only acceptable change is widening visibility (`private` → `internal`) on the specific member with a comment `// widened from private to support extraction (Phase 4)`. No renames.

### Verification
1. `swift build` succeeds after each individual extraction *and* at end of phase.
2. `swift test` final state shows the same pass/fail set as baseline.
3. `wc -l gui-macos/Sources/App.swift` shows ~670 lines (down from 2,732).
4. `llamacpp-manager install-gui --force` launches; full smoke-test (§10) passes.

### Commit message
`refactor: extract 20 declarations from App.swift to per-symbol files (Standard §5.1, §7.2)`

### Rollback
Single `git revert` of this commit restores prior state. No external references to moved symbols exist (Swift module is flat), so revert is clean.

---

## 8. Phase 5 — StatusViewModel Decomposition *(DEFERRED / OPTIONAL)*

**Goal:** Decompose the ~1,323-line `StatusViewModel` into 5–7 focused coordinators per inventory §11.

**Recommendation:** **Do not execute in this pass.** Reasons:
1. The no-break guarantee is significantly harder when one class is split into many — the call graph changes.
2. Phases 1–4 already get the codebase past the worst structural issues. Phase 5 is polish.
3. Operator should review the result of Phase 4 before committing to this scope.

If/when scheduled, this phase will get its own follow-up plan document with the same no-break discipline.

---

## 9. Phase 6 — Test Scaffolding (Standard §10.3, §18.2)

**Goal:** Introduce protocol seams that allow view models to be unit-tested without spawning real subprocesses.

### Changes
1. Add `Sources/Services/CLIServicing.swift`:
   - `protocol CLIServicing { ... }` containing the public methods `StatusViewModel` and `DownloadViewModel` currently call on `CLIService`.
   - Make existing `CLIService` conform: `extension CLIService: CLIServicing {}`. No method signature changes.
2. Update view-model `let service: CLIService` properties to `let service: CLIServicing` (one-line type widening). Verify no caller passes anything other than a `CLIService` instance — they don't (inventory §12).
3. Add `Sources/Services/DockerServicing.swift` similarly for `DockerService`.

### Safety
- Protocol introduction is purely additive — existing concrete types still flow through unchanged.
- Property type widening from concrete to protocol does not change any call site because all methods used appear in the protocol.
- No production behavior change.

### Verification
1. `swift build` succeeds.
2. `swift test` shows the same pass/fail set as baseline.
3. App still launches and behaves identically.

### Commit message
`refactor: introduce CLIServicing and DockerServicing protocols for testability (Standard §10.3, §18.2)`

---

## 10. Phase 7 — New Unit Tests

**Goal:** Add focused unit tests that exercise view-model logic against mock services. Tests are additive — no production code changes in this phase.

### New test files
Tests land in the existing layout (`gui-macos/Tests/Unit/` and `gui-macos/Tests/llamacpp_guiTests/`). The existing folder split is preserved; no consolidation in this phase.

| File | Subject | Scenarios |
|------|---------|-----------|
| `Tests/Unit/Mocks/MockCLIService.swift` | Fake `CLIServicing` | Records method calls; returns operator-configured responses or errors. |
| `Tests/Unit/Mocks/MockDockerService.swift` | Fake `DockerServicing` | Same pattern. |
| `Tests/Unit/CLIErrorTests.swift` | `CLIError` cases | LocalizedError text, equality, error-mapping behavior. |
| `Tests/Unit/AnyCodableTests.swift` | `AnyCodable` decoder | int / string / bool / null / nested JSON. |
| `Tests/Unit/ModelStartupProgressTests.swift` | `ModelStartupProgress` | Equatable behavior; transitions. |
| `Tests/Unit/StatusViewModelRefreshTests.swift` | `StatusViewModel.refresh()` happy path | Mocked CLI returns canned `StatusResponse`; assert `@Published rows` updated. |
| `Tests/Unit/StatusViewModelErrorTests.swift` | `StatusViewModel.refresh()` error paths | Mocked CLI throws; assert no crash, error surfaced. |
| `Tests/Unit/ChatViewModelTests.swift` | `ChatViewModel.sendMessage` | Mocked CLI; success path appends to `messages`, error path sets `errorMessage`. |
| `Tests/Unit/DownloadViewModelFilterTests.swift` | Filter combinators on `availableModels` | format / size / use-case / search interactions. |

### Test framework choice
Per Standard §4.4, new pure-Swift unit tests use Swift Testing (`import Testing`, `@Test`). Existing XCTest files in `Tests/Unit/` and `Tests/llamacpp_guiTests/` are not migrated.

### Verification
1. `swift test` shows the previous test set passing **and** the new tests passing.
2. No new test depends on a live subprocess, network call, file outside `FileManager.default.temporaryDirectory`, or `PreferencesManager.shared` mutation that persists.
3. CI (if added later) runs the same `swift test` invocation.

### Commit message
`test: add unit tests for view models with mock services (Standard §18.2)`

---

## 11. Manual Smoke-Test Checklist

Operator runs this list after every phase (it takes ~3 minutes). A phase is not "done" until every item passes.

1. `llamacpp-manager install-gui --force` succeeds and prints "Process running".
2. Brain icon appears in the menu bar.
3. Click the icon — menu opens within 1 second; tabs (Infrastructure, Native Models, Docker Models) render.
4. Refresh button works; row list updates without freeze.
5. Start a model → it transitions to "running" within the expected time.
6. Stop the model → it transitions back without leaving zombie processes (`pgrep -f mlx_lm.server` is empty).
7. Open Chat window → window appears, input field is focusable.
8. Open Preferences → all three tabs render.
9. Open Model Downloader → catalog loads or shows the error banner cleanly.
10. Quit via menu → process exits cleanly (`pgrep -f llamacpp-gui` is empty after 2 seconds).

If any item fails, the phase is reverted (`git revert HEAD`), root cause documented, and the phase is re-planned.

---

## 12. Risk Register

| Risk | Phase | Likelihood | Impact | Mitigation |
|------|-------|------------|--------|------------|
| `@MainActor` exposes latent off-main UI write | 2 | Medium | Medium | Fix surfaces as a build error; either add `await` or revert phase and open a bug. |
| Move-only extraction misses a `fileprivate` reference | 4 | Low | Low | Inventory found none; if hit, widen to `internal` with a comment. |
| Build script breaks because `App.swift` moved | 3, 4 | Very Low | Medium | Plan explicitly keeps `App.swift` at `Sources/App.swift`. |
| Protocol widening (Phase 6) reveals an unused public method | 6 | Low | Low | Acceptable — leave the method, plan does not delete code. |
| New tests flake on CI without local sim parity | 7 | Low | Low | Tests are pure-Swift unit tests with mocked services — no UI, no subprocess. |
| Operator stops mid-phase, working tree dirty | All | Medium | Low | Each phase ends with a single commit; mid-phase state is "do not commit yet." Worst case: `git stash`. |
| Inventory line ranges drift due to in-flight edits | 4 | Low | Low | Implementer locates each symbol by name, not line number; line numbers are reference only. |

---

## 13. Phase-by-Phase Acceptance Gates

The operator's stated acceptance flow: **plan committed → operator reviews → operator approves → execution proceeds**.

Within execution, each phase has its own gate:

```
Phase N starts
  → implementer follows §N steps
  → swift build passes
  → swift test pass/fail set unchanged
  → llamacpp-manager install-gui --force succeeds
  → manual smoke-test checklist passes
  → operator confirms
  → single git commit
  → Phase N+1 starts (or stop)
```

Operator may stop after any phase. The codebase remains in a buildable, shippable state at every commit boundary.

---

## 14. What This Plan Does NOT Do

- Does not introduce new third-party dependencies (Standard §17).
- Does not change signing, entitlements, bundle ID, or deployment target.
- Does not modify the Python CLI side of the repo.
- Does not touch `pyproject.toml`, `src/llamacpp_manager/`, or any tests outside `gui-macos/Tests/`.
- Does not rename any symbol.
- Does not remove any code.
- Does not change `Package.swift` `path:` or target structure.
- Does not migrate `ObservableObject` to `@Observable` (Standard §8.2 explicitly says do not migrate without intent — deferred).
- Does not migrate XCTest to Swift Testing for existing tests (Standard §4.4 — coexistence is fine).
- Does not refactor `StatusViewModel` internals (Phase 5, deferred).
- Does not change anything related to Keychain, ATS, or signing (no secrets in scope).

---

## 15. Open Questions for the Operator

These are not blockers for plan approval but should be answered before Phase 6 starts:

1. **Mock framework.** Hand-rolled mock classes (planned), or pull in a small library like `Mockable`? *Recommendation: hand-rolled, zero deps.*
2. **Swift Testing vs XCTest for new tests.** Plan uses Swift Testing. Confirm OK or override.
3. **Phase 5 scheduling.** Defer entirely, or schedule a follow-up plan after Phase 4?
4. **Phase 7 coverage target.** Plan delivers ~8 new test files. Want a coverage % goal, or "best effort on the listed scenarios"?

---

## 16. Approval

Operator: please review and indicate one of:

- **Approve as-is** — execution may begin from Phase 0.
- **Approve with edits** — list changes; plan is revised and re-committed before execution.
- **Reject** — reasons noted; plan is rewritten.

Execution begins only after explicit operator approval.
