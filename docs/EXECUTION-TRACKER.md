# Execution Tracker — Test Coverage + AIDevOps Registration

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/EXECUTION-TRACKER.md
**Description:** Operational tracker for executing the current test-coverage and AIDevOps registration work from the already-approved slice implementation plan. Complements `docs/SLICE-IMPLEMENTATION-PLAN.md` by recording what is already done, what is blocked locally, and the exact next actions to run.
**Author:** Codex
**Created:** 2026-06-25
**Last Updated:** 2026-06-25
**Primary plan:** `docs/SLICE-IMPLEMENTATION-PLAN.md`
**Primary state file:** `.plan-state.json`
**Platform manifest:** `.aidevops/test-manifest.json`

---

## 1. Current execution state

### Completed in this run

- Phase 0 — prerequisites and coverage audit
- Phase 1 — O / X / T contract-lock foundation
- Phase 2 — Inst deployment work
- Phase 3.1 — `D.1` implemented in code
- AIDevOps manifest registration file created at `.aidevops/test-manifest.json`

### Current hard facts

- `deploy.sh` exists and is verified locally.
- `.aidevops/test-manifest.json` exists and parses as valid JSON.
- `.aidevops-stack.yml` exists only as a valid repo-specs stub.
- `slice-D.1` code exists in `gui-macos/Tests/E2E/SliceD_StartStopTests.swift`.
- Interactive Swift slices `B`, `C`, and `D` are registered for future managed execution, but currently run as `runner_kind: "custom"` because aidevops does not yet support `swift`.

### Local automation blocker

- On this machine, `System Events` can click the menu bar item but cannot see the opened `MenuBarExtra` popover contents as accessible buttons.
- This affects automated verification of slices `B`, `C`, and `D`.
- The product behavior is believed good; the current limitation is the automation surface.
- The Swift slices now skip cleanly with an explicit reason instead of failing misleadingly.

---

## 2. What is already shippable

These can be committed and seeded into aidevops immediately:

- `tests/test_status.py`
- `tests/test_lifecycle_log_schema.py`
- `tests/test_cli_external_invocation.py`
- `tests/test_deploy_sh.py`
- `gui-macos/Tests/E2E/SliceInst_DeploymentTests.swift`
- `gui-macos/Tests/E2E/SliceD_StartStopTests.swift`
- `.aidevops/test-manifest.json`
- `deploy.sh`
- associated docs and `.plan-state.json`

---

## 3. Immediate execution queue

Execute these in order.

### Queue 1 — Repository checkpoint

**Status:** ready now

1. Review working tree for scope sanity.
2. Commit current work in logical groups:
   - foundation contract tests
   - deployment / installation
   - GUI slice D + interactive-skip hardening
   - aidevops manifest registration
3. Push to origin.

**Done when:**
- local working tree is clean
- commits are pushed
- commit messages clearly separate contract tests, deployment, GUI slices, and manifest registration

### Queue 2 — Seed managed suites in aidevops

**Status:** ready after repo checkpoint

1. Ensure `llamaCPPManager` is registered in aidevops with the correct `local_path`.
2. Trigger manifest seeding for `.aidevops/test-manifest.json`.
3. Confirm the following suites appear in aidevops:
   - GUI Slice Smoke — Launch + Install
   - GUI Slice B — Chat Window Lifecycle
   - GUI Slice C — Chat Send + Receive
   - GUI Slice D — Start/Stop Consistency
   - Python Status + Lifecycle Contracts
   - Python CLI External Invocation Contracts
   - Python Deploy Workflow Contracts
4. Verify suite metadata:
   - `repo_local_path` set
   - `working_dir` set for GUI suites
   - Python suites registered as `pytest`
   - GUI suites registered as `custom`

**Done when:**
- aidevops reports `manifest_found=true`
- expected suites are visible in the platform
- no manifest-seeder errors

### Queue 3 — Platform runner support for Swift

**Status:** cross-repo, next highest leverage

This is the single most important platform improvement for future automated execution.

1. In aidevops, add `swift` to `KNOWN_RUNNER_KINDS`.
2. Add execution support for commands like:
   - `swift test --filter SliceA`
   - `env RUN_E2E_INTERACTIVE=1 swift test --filter SliceD`
3. Decide whether env-prefixed commands remain `custom` or whether the `swift` runner supports env injection via suite config.
4. Update manifest strategy:
   - convert GUI slice suites from `custom` to `swift`, or
   - keep `custom` temporarily but document the expected migration.
5. Add at least one aidevops smoke or regression test for the new `swift` runner.

**Done when:**
- aidevops can execute a Swift suite for a managed repo
- this repo’s GUI suites no longer need `runner_kind: "custom"`

---

## 4. Remaining llamaCPPManager execution work

These are the next in-repo steps after manifest seeding / checkpointing.

### Step 3.2 — Extend Slice D with D.5–D.10

**Status:** next in-repo coding task

Add to `gui-macos/Tests/E2E/SliceD_StartStopTests.swift`:

- D.5 — Start already-running model
- D.6 — Stop already-stopped model
- D.7 — Port conflict
- D.8 — Start then immediate stop
- D.9 — `start all`
- D.10 — Restart Active

**Implementation guidance:**

- Reuse the isolated temp-config harness from `D.1`.
- Keep variants skip-capable under the current local MenuBarExtra automation limitation.
- For D.7, use a placeholder listener on the configured port.
- For D.9 and D.10, prefer a fixture with multiple small native models rather than the full user inventory.

**Done when:**
- code exists for all six variants
- focused `swift test --filter SliceD` passes or skips cleanly with explicit reason

### Step 3.3 — Slice P shutdown coverage

**Status:** pending

Create `gui-macos/Tests/E2E/SliceP_ShutdownTests.swift`.

Cover:

- normal quit cleanup
- quit with open windows
- quit after active model lifecycle events
- model child cleanup
- force-kill edge where possible

**Done when:**
- shutdown assertions exist
- smoke checklist dependency can point to automated coverage instead of manual-only notes

### Step 3.4 — Slice Y.1 version verification

**Status:** pending

Create or extend a small UI slice so the About/version display is checked against `VERSION`.

**Done when:**
- one focused test exists
- version mismatch becomes an automated failure

### Phase 4 — Slice H crash detection

**Status:** highest remaining product-risk gap

1. Create the missing Python test file for crash/monitor behavior.
2. Add the Swift E2E for GUI/monitor interaction.
3. Verify lifecycle log events on crash + recovery.

**Done when:**
- the auto-restart path is exercised by tests rather than only manual trust

---

## 5. Managed-suite policy for the current state

Until aidevops ships `swift` runner support:

- Python suites should be executed from aidevops directly.
- GUI Swift suites should be managed and visible in aidevops, but may run through `custom`.
- Interactive GUI suites must carry explicit notes that they require:
  - Accessibility-granted runner
  - a machine where the `MenuBarExtra` popover is visible to automation

This is acceptable as an intermediate state. The registration problem and the execution problem are separate.

---

## 6. Tracker checklist

Use this list as the operator-facing tracker.

- [ ] Commit current llamaCPPManager work
- [ ] Push current llamaCPPManager work
- [ ] Register / verify repo in aidevops
- [ ] Seed `.aidevops/test-manifest.json`
- [ ] Confirm 7 suites appear in aidevops
- [ ] Add `swift` runner support in aidevops
- [ ] Migrate GUI suites from `custom` to `swift`
- [ ] Implement `slice-D.idempotent-bulk`
- [ ] Implement `slice-P.shutdown`
- [ ] Implement `slice-Y.1`
- [ ] Implement Phase 4 Slice H crash-detection coverage
- [ ] Resume remaining phases from `docs/SLICE-IMPLEMENTATION-PLAN.md`

---

## 7. Resume commands

### Resume in this repo

```text
/execute-plan docs/SLICE-IMPLEMENTATION-PLAN.md
```

### Resume from this execution tracker

1. Read `docs/EXECUTION-TRACKER.md`
2. Read `.plan-state.json`
3. Start at the first unchecked item in section 6

### Seed suites in aidevops

Use the repo’s `.aidevops/test-manifest.json` after the repo is registered in the platform.

