# Slice Implementation Plan — Autonomous Execution

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/SLICE-IMPLEMENTATION-PLAN.md
**Description:** Step-by-step executable plan for landing the planned vertical-slice E2E tests cataloged in `docs/E2E-SLICES.md`. Designed to be consumed by `/execute-plan` for autonomous execution. Steps have explicit dependencies (DAG), exit criteria, and fatal-on-failure flags. The plan respects the bump-before-commit rule from the operating standard and the no-mocks rule from the Swift Agent Standard §18.
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2026-06-25
**Last Updated:** 2026-06-25
**Last Updated By:** Libor Ballaty
**Companion document:** `docs/E2E-SLICES.md` (canonical slice catalog)
**Linked TODOs:** llamaCPPManager `docs/TODO.md` (testing rewrite — done); aidevops `design/TODO.md` #122 (release engineering), #123 (LLM Manager review)

---

## 0. How to execute this plan

1. **Manually:** read this document top-to-bottom. Each phase contains numbered steps with explicit IDs. Execute them in dependency order.
2. **Autonomously via `/execute-plan`:** invoke the skill with this file as input. The skill will walk the dependency DAG, invoke `/troubleshoot` on failures, and maintain a resumable `.plan-state.json` checkpoint.

Each step declares:
- `id` — stable identifier
- `depends_on` — list of step IDs that must complete first
- `slice` — slice ID this step contributes to (per `docs/E2E-SLICES.md`)
- `work` — concrete actions
- `exit_criteria` — observable pass conditions
- `files_touched` — paths the step will edit/create
- `fatal_on_failure` — `yes` (block downstream) or `no` (continue, surface in recap)
- `estimated_minutes` — wall-clock estimate for a focused agent run

## 1. Plan-wide invariants

- **Bump rule:** any commit that touches code under `src/` or `gui-macos/Sources/` MUST be preceded by `version-bump.py` and accompanied by a `CHANGELOG.md` entry. Pure-doc and pure-test commits do not bump. See `~/.codex/memories/agentic-operating-standard.md` → "Version bumps and release engineering."
- **No mocks:** every test added by this plan uses the real stack (real CLI, real subprocesses, real model servers). See `docs/SWIFT-AGENT-STANDARD.md` §18.
- **File reservation:** every step claims its files via `queuectl reserve` before first write and releases on completion.
- **Existing pytest:** many slices have partial coverage in existing pytest files. Plan steps **audit + extend + label** rather than rewrite. New pytest files are only added where the slice has no existing test file (most notably `test_monitor.py` for Slice H).
- **Per-slice exit criterion:** a slice variant is "covered" when (1) a test exists that exercises its specific code path against the real stack, (2) the test passes, and (3) the slice catalog entry is marked ✅ with version.
- **No assumption of one-variant-covers-all:** each variant in `docs/E2E-SLICES.md` is its own pass/fail. Per-deployment-type variants (native / MLX / MLX-VLM / Docker) must each be exercised against a model of that type.

## 2. Phase overview

| Phase | Theme | Slices in phase | Estimated effort |
|---|---|---|---|
| **0** | Prerequisites — environment + first audits | (none) | 30 min |
| **1** | Foundation — schema locks + contract tests | O, X, T | 90 min |
| **2** | Deployment & Installation — Slice Inst + new deploy.sh | Inst | 4–6 h |
| **3** | Quick wins — GUI ↔ CLI consistency + shutdown | D (subset), P (subset), Y (subset) | 3 h |
| **4** | Reliability gap — Crash detection & auto-restart | H | 3 h |
| **5** | Slice A/B/C variant fill-ins | A.2–A.6, B.2–B.6, C.2–C.12 | 4 h |
| **6** | Deployment-type fan-out for D | D.2–D.4 | 3 h |
| **7** | Preferences, Logs viewer, Discovery | L, M, Q | 4 h |
| **8** | MCP audit + harden | N.10–N.16 | 3 h |
| **9** | Infrastructure + MCP visibility | K | 2 h |
| **10** | Config CRUD remaining + Bootstrap + Cleanup + Logging + Health | E, R, V, U, W | 4 h |
| **11** | Heavy: Download, Compare, Concurrency, Docker Colima | F, G, S, J | 6 h |
| **12** | aidevops platform registration | (cross-repo) | 2 h |
| **13** | Final tidy: smoke checklist refresh + docs index | (docs) | 30 min |

**Total estimate:** ~38 hours of focused agent execution. Each phase is independently shippable; phases 1, 2, 4 are the highest priority by ROI.

## 3. Phase 0 — Prerequisites

### Step 0.1 — Verify environment
- **id:** `prereq.environment`
- **depends_on:** none
- **slice:** N/A
- **work:**
  - Verify `llamacpp-manager` is installed via pipx (`which llamacpp-manager`).
  - Verify `swift` toolchain present (`swift --version`).
  - Verify `~/.llamacpp-manager/config.yaml` exists with at least one configured model of each deployment_type if possible (native / MLX / MLX-VLM / Docker). Record which types are available — variants for missing types are documented as "skipped: type not available locally" rather than failures.
  - Verify `/Applications/llamaCPP Manager.app` is installed at current `VERSION`.
- **exit_criteria:** report of available environment in plan-state log.
- **files_touched:** `.plan-state.json` (created by execute-plan if used).
- **fatal_on_failure:** no (record gaps, continue).
- **estimated_minutes:** 5.

### Step 0.2 — Baseline test run
- **id:** `prereq.baseline`
- **depends_on:** `prereq.environment`
- **work:**
  - `cd gui-macos && swift test` → record passing/failing count.
  - `cd <repo-root> && .venv/bin/pytest tests/ -q` → record passing/failing count.
- **exit_criteria:** both runs complete; baseline counts recorded. Any pre-existing failures noted for triage but do not block downstream steps.
- **fatal_on_failure:** no.
- **estimated_minutes:** 10.

### Step 0.3 — Audit existing partial coverage
- **id:** `prereq.audit-existing`
- **depends_on:** `prereq.baseline`
- **work:** open each existing pytest file and note which slice + variants it touches. Produce `docs/SLICE-COVERAGE-AUDIT.md` mapping `tests/test_*.py` → slice IDs.
- **exit_criteria:** audit doc created.
- **files_touched:** `docs/SLICE-COVERAGE-AUDIT.md` (new).
- **fatal_on_failure:** no.
- **estimated_minutes:** 15.

## 4. Phase 1 — Foundation (schema locks)

These slices protect every consumer of the system (aidevops, MCP clients, Codex, future agents). Tiny investment, high blast-radius prevention.

### Step 1.1 — Slice O: `status --json` schema lock
- **id:** `slice-O.lock`
- **depends_on:** `prereq.audit-existing`
- **slice:** O.1–O.7
- **work:**
  - Define a canonical JSON schema in `tests/fixtures/status_schema.json` documenting every key with type + optionality + enum constraint.
  - Extend `tests/test_status.py` with a test that runs `llamacpp-manager status --json` and validates the live output against the schema using `jsonschema`.
  - Cover variants O.1 (empty config), O.2 (each deployment_type), O.3 (mixed running/stopped), O.4 (infra present), O.5 (optional fields), O.6 (JSON vs TTY), O.7 (schema versioned).
- **exit_criteria:** `pytest tests/test_status.py` includes 7 new variant checks, all passing. Schema file committed.
- **files_touched:** `tests/test_status.py`, `tests/fixtures/status_schema.json`.
- **fatal_on_failure:** no (record, continue).
- **estimated_minutes:** 60.

### Step 1.2 — Slice X: Lifecycle log schema lock
- **id:** `slice-X.lock`
- **depends_on:** `prereq.audit-existing`
- **slice:** X.1–X.4
- **work:**
  - Define canonical event schema in `docs/LIFECYCLE-LOG-SCHEMA.md`: every emitted event name + required fields + types.
  - Add a pytest `tests/test_lifecycle_log_schema.py` that triggers a representative subset of events (start, stop, chat, refresh) and validates each line in `~/Library/Logs/llamaCPPManager/lifecycle.jsonl` matches the schema.
  - X.4 (rotation): verify events survive log rotation.
- **exit_criteria:** new test passes; schema doc committed.
- **files_touched:** `tests/test_lifecycle_log_schema.py` (new), `docs/LIFECYCLE-LOG-SCHEMA.md` (new).
- **fatal_on_failure:** no.
- **estimated_minutes:** 30.

### Step 1.3 — Slice T: External CLI invocation contract
- **id:** `slice-T.contract`
- **depends_on:** `slice-O.lock`
- **slice:** T.1–T.6
- **work:**
  - Extend `tests/test_cli_*.py` or add `tests/test_cli_external_invocation.py` with:
    - T.1 piped output preserves JSON shape
    - T.2 UTF-8 safety
    - T.3 missing `pgrep` produces typed error
    - T.4 concurrent invocations don't corrupt config (use temp config + flock check)
    - T.5 exit-code contract: locked map of exit codes per error class
    - T.6 stderr clean separation (parseable stdout JSON even with stderr noise)
- **exit_criteria:** new test file passes; exit-code mapping documented in `docs/CLI-EXIT-CODES.md`.
- **files_touched:** `tests/test_cli_external_invocation.py` (new), `docs/CLI-EXIT-CODES.md` (new).
- **fatal_on_failure:** no.
- **estimated_minutes:** 60.

## 5. Phase 2 — Deployment & Installation (Slice Inst + deploy.sh)

This phase is structurally important: aidevops platform's Release Workflow (TODO #122) expects every consumer repo to have a `deploy.sh`. Without it, llamaCPPManager cannot be deployed via the platform.

### Step 2.1 — Author repo-root `deploy.sh`
- **id:** `inst.deploy-sh`
- **depends_on:** `prereq.audit-existing`
- **slice:** Inst.10–Inst.18
- **work:**
  - Create `deploy.sh` at repo root implementing the aidevops Release Workflow contract:
    - `deploy.sh build` — runs `swift build` for GUI, `python -m build` for Python package.
    - `deploy.sh install` — pipx install/reinstall of Python package, install-gui for app bundle, verifies `llamacpp-manager` + `llamacpp-mcp-server` are on PATH after install.
    - `deploy.sh verify` — runs `llamacpp-manager status --json` (must succeed), checks GUI app at `/Applications/llamaCPP Manager.app`, verifies MCP server entry point invokable, checks all declared deps (Python ≥3.10, Swift ≥5.9, macOS ≥13, pipx) and reports missing.
    - `deploy.sh deploy-local` — convenience: build + install + verify.
    - `deploy.sh check-deps` — standalone dep check; exit code reflects pass/fail.
    - All subcommands respect `--source-revision <sha>` for aidevops source_revision pin.
    - Idempotency: running install twice in a row must succeed both times.
  - Documented exit codes in script header (mirrors `install_gui.sh` pattern).
  - File header per global standard.
- **exit_criteria:** `bash deploy.sh check-deps` exits 0; `bash deploy.sh verify` exits 0 on the dev machine.
- **files_touched:** `deploy.sh` (new), `docs/DEPLOY-SCRIPT.md` (new — contract documentation).
- **fatal_on_failure:** YES (later steps depend on this contract existing).
- **estimated_minutes:** 90.

### Step 2.2 — Slice Inst E2E tests
- **id:** `slice-Inst.tests`
- **depends_on:** `inst.deploy-sh`
- **slice:** Inst.1–Inst.18
- **work:**
  - Create `gui-macos/Tests/E2E/SliceInst_DeploymentTests.swift` with Swift Testing tests covering Inst.1–Inst.9 (`install_gui.sh` variants). These drive `bash install_gui.sh` from inside Swift tests via `Process` and assert via filesystem checks + lifecycle log + `pgrep`.
  - Create `tests/test_deploy_sh.py` with pytest covering Inst.10–Inst.18 (`deploy.sh` variants). Use `subprocess.run("./deploy.sh ...", ...)`.
  - For Inst.5 (stale build detection): bump VERSION, do not rebuild, assert install-gui detects staleness and rebuilds.
  - For Inst.8 (permission failure): use a non-writable temp `/Applications`-like dir via env override if supported, or document as not-auto-testable.
  - For Inst.17 (upgrade): install older artifact via git checkout of prior tag, then install new, verify upgrade works.
- **exit_criteria:** all Inst variants pass for the variants that can be exercised on the current machine; un-exercisable variants documented as skipped with reason (e.g. "Inst.8 permission failure requires sandboxed run").
- **files_touched:** `gui-macos/Tests/E2E/SliceInst_DeploymentTests.swift` (new), `tests/test_deploy_sh.py` (new).
- **fatal_on_failure:** no.
- **estimated_minutes:** 120.

### Step 2.3 — Register Inst in `.aidevops-stack.yml` (preparatory)
- **id:** `inst.platform-stub`
- **depends_on:** `slice-Inst.tests`
- **slice:** Inst (registration)
- **work:** add a stub entry to `.aidevops-stack.yml` (created in Step 12.1) declaring the Inst suite. Full platform registration is Phase 12; this stubs only the Inst row.
- **exit_criteria:** entry exists and validates against the schema.
- **files_touched:** `.aidevops-stack.yml` (new — stub).
- **fatal_on_failure:** no.
- **estimated_minutes:** 10.

## 6. Phase 3 — Quick wins (GUI ↔ CLI consistency + shutdown + Y.1)

### Step 3.1 — Slice D.1: GUI start/stop ↔ CLI status agreement (native)
- **id:** `slice-D.1`
- **depends_on:** `slice-X.lock`
- **work:** `Tests/E2E/SliceD_StartStopTests.swift` — opens menu, clicks Start on a configured native model, waits for `ui.start.cli_result`, invokes `llamacpp-manager status --json` from the test, asserts the model row reports `up=true`. Reverse for Stop.
- **exit_criteria:** test passes opt-in.
- **estimated_minutes:** 60.

### Step 3.2 — Slice D.5–D.10: idempotency, race, port-conflict, bulk
- **id:** `slice-D.idempotent-bulk`
- **depends_on:** `slice-D.1`
- **work:** extend the same test file with variants for D.5 (start already-running), D.6 (stop already-stopped), D.7 (port-conflict — simulated by starting a placeholder Python `python -m http.server <port>` on the model's port), D.8 (start then immediate stop), D.9 (`start all`), D.10 (Restart Active bulk).
- **exit_criteria:** all 6 variants pass.
- **estimated_minutes:** 90.

### Step 3.3 — Slice P: Clean shutdown
- **id:** `slice-P.shutdown`
- **depends_on:** `slice-D.1`
- **work:** `Tests/E2E/SliceP_ShutdownTests.swift` — for each variant P.1–P.5, launch + drive into the relevant state, Quit, assert `pgrep -f llamacpp-gui` empty + model child processes cleaned. P.6 (force-kill) + P.7 (cleanup CLI) + P.8 (monitor stays) as separate functions.
- **exit_criteria:** all 8 P variants pass; smoke item 10 supplanted by this slice.
- **estimated_minutes:** 60.

### Step 3.4 — Slice Y.1: About dialog version match
- **id:** `slice-Y.1`
- **depends_on:** `slice-D.1`
- **work:** extend an existing slice or add a tiny `SliceY_MinorUITests.swift` with Y.1 — drive About dialog, scrape the version string via accessibility query, assert it matches `cat VERSION`.
- **exit_criteria:** test passes.
- **estimated_minutes:** 30.

## 7. Phase 4 — Crash detection & auto-restart (Slice H)

Largest current reliability gap. No `test_monitor.py` exists today.

### Step 4.1 — Create `tests/test_monitor.py` (unit + integration)
- **id:** `slice-H.pytest`
- **depends_on:** `slice-X.lock`
- **slice:** H.1, H.2, H.5, H.7, H.8, H.10
- **work:** new pytest file covering the monitor daemon's track/untrack/crash-detect/restart logic against a real subprocess. Uses `multi_query.py` style fixtures to start a real model, `kill -9`s the model's PID, asserts monitor detects within N seconds and restarts. Variants H.1 (native), H.2 (MLX) require respective models available.
- **exit_criteria:** new test file passes.
- **files_touched:** `tests/test_monitor.py` (new).
- **fatal_on_failure:** no.
- **estimated_minutes:** 90.

### Step 4.2 — Slice H Swift E2E
- **id:** `slice-H.swift`
- **depends_on:** `slice-H.pytest`
- **slice:** H.3 (MLX-VLM), H.4 (Docker), H.6 (chat-in-progress crash), H.9 (autostart=false tracking design call)
- **work:** `Tests/E2E/SliceH_AutoRestartTests.swift` — for each variant, drive the GUI / monitor daemon, force a crash, assert recovery via lifecycle log events.
- **exit_criteria:** all available variants pass.
- **estimated_minutes:** 90.

## 8. Phase 5 — A/B/C variant fill-ins

### Step 5.1 — A.2–A.6 (launch variants)
- **id:** `slice-A.variants`
- **depends_on:** `slice-X.lock`
- **work:** extend `SliceA_LaunchTests.swift`. For A.3 (CLI not installed), rename the binary temporarily; for A.5 (already-running), launch twice; for A.6 (sub-2s relaunch), quit + relaunch in a loop.
- **estimated_minutes:** 60.

### Step 5.2 — B.2–B.6 (chat window variants)
- **id:** `slice-B.variants`
- **depends_on:** `slice-D.1`
- **work:** extend `SliceB_ChatWindowTests.swift`.
- **estimated_minutes:** 60.

### Step 5.3 — C.2–C.4 (chat send to MLX / MLX-VLM / Docker)
- **id:** `slice-C.deployment-types`
- **depends_on:** `slice-D.1`
- **work:** extend `SliceC_ChatSendReceiveTests.swift`. Each variant skips if no model of that type is available locally.
- **estimated_minutes:** 60.

### Step 5.4 — C.5–C.12 (error paths, streaming, persistence, edge cases)
- **id:** `slice-C.error-and-edges`
- **depends_on:** `slice-C.deployment-types`
- **work:** extend `SliceC_ChatSendReceiveTests.swift` with the remaining 8 variants.
- **estimated_minutes:** 90.

## 9. Phase 6 — D.2–D.4 deployment-type fan-out

### Step 6.1 — D.2 (MLX), D.3 (MLX-VLM), D.4 (Docker) start/stop
- **id:** `slice-D.deployment-types`
- **depends_on:** `slice-D.idempotent-bulk`, `slice-H.pytest`
- **work:** extend `SliceD_StartStopTests.swift`. Skip if model of type not available.
- **estimated_minutes:** 60.

## 10. Phase 7 — Preferences, Logs viewer, Discovery

### Step 7.1 — Slice L: Preferences edit & persist
- **id:** `slice-L`
- **depends_on:** `slice-P.shutdown`
- **work:** `Tests/E2E/SliceL_PreferencesTests.swift` covering L.1–L.6. L.1 (persist across restart) needs quit + relaunch cycle.
- **estimated_minutes:** 90.

### Step 7.2 — Slice M: Logs viewer
- **id:** `slice-M`
- **depends_on:** `slice-D.1`
- **work:** `Tests/E2E/SliceM_LogsViewerTests.swift` covering M.1–M.7.
- **estimated_minutes:** 60.

### Step 7.3 — Slice Q: Discovery & auto-detection variants
- **id:** `slice-Q`
- **depends_on:** `slice-X.lock`
- **work:** extend `test_discovery_parse.py` / `test_discovery_status.py` with Q.3 (MLX-VLM), Q.4 (symlinks), Q.5 (permission denied), Q.6 (race).
- **estimated_minutes:** 45.

## 11. Phase 8 — MCP audit + harden

### Step 8.1 — Audit `test_mcp_server.py`
- **id:** `slice-N.audit`
- **depends_on:** `prereq.audit-existing`
- **work:** for each of the 9 MCP tools, verify happy + error path tests exist. Produce gap list.
- **estimated_minutes:** 30.

### Step 8.2 — Extend MCP tests
- **id:** `slice-N.harden`
- **depends_on:** `slice-N.audit`
- **work:** fill gaps from audit. Add N.12 (schema lock per tool), N.13 (mid-session reconnect), N.15 (no models configured), N.16 (concurrent calls).
- **estimated_minutes:** 120.

## 12. Phase 9 — Infrastructure components + MCP visibility (Slice K)

### Step 9.1 — Slice K.1, K.2: cloudflared + llm_controller
- **id:** `slice-K.1-2`
- **depends_on:** `slice-X.lock`
- **work:** extend `test_infrastructure.py` and add a small Swift E2E covering GUI Infrastructure tab.
- **estimated_minutes:** 45.

### Step 9.2 — Slice K.3: MCP server visibility (closes long-standing backlog)
- **id:** `slice-K.3`
- **depends_on:** `slice-K.1-2`, `slice-N.harden`
- **slice:** K.3 + closes auto-memory `mcp-server-gui-followup`
- **work:**
  - Add MCP server as a first-class row in the GUI Infrastructure tab (status indicator, start/stop, last-restart timestamp).
  - Add "Copy agent config" button generating MCP config snippets.
  - Add `Tests/E2E/SliceK_InfrastructureTests.swift` covering the new MCP row driving.
- **exit_criteria:** GUI shows MCP server row; start/stop works; copy-config produces valid JSON snippet for Claude Desktop / Codex / Gemini.
- **files_touched:** `gui-macos/Sources/Views/InfrastructureView*.swift` (or wherever the infra tab lives), `gui-macos/Tests/E2E/SliceK_InfrastructureTests.swift`.
- **fatal_on_failure:** no.
- **estimated_minutes:** 90.

### Step 9.3 — K.4–K.7 remaining variants
- **id:** `slice-K.4-7`
- **depends_on:** `slice-K.3`
- **estimated_minutes:** 30.

## 13. Phase 10 — Config CRUD remaining + Bootstrap + Cleanup + Logging + Health

### Step 10.1 — Slice E remaining variants
- **id:** `slice-E.rest`
- **depends_on:** `prereq.audit-existing`
- **work:** extend `test_cli_config.py` for E.2–E.4 (per-type adds), E.7 (remove-while-running), E.11 (exclusive group). Add a Swift E2E for E.9 (GUI Configure button after download).
- **estimated_minutes:** 60.

### Step 10.2 — Slice R: Bootstrap mlx-vlm
- **id:** `slice-R`
- **depends_on:** `inst.deploy-sh`
- **work:** new `tests/test_bootstrap.py` covering R.1–R.4. R.1 needs venv + mlx-vlm install (heavy).
- **estimated_minutes:** 60.

### Step 10.3 — Slice V: Cleanup
- **id:** `slice-V`
- **depends_on:** `slice-P.shutdown`
- **work:** new `tests/test_cleanup.py` covering V.1–V.5. Set up controlled orphan state, run `llamacpp-manager cleanup`, assert cleanup.
- **estimated_minutes:** 45.

### Step 10.4 — Slice U.5: Logging apply-to-running semantics
- **id:** `slice-U.5`
- **depends_on:** `prereq.audit-existing`
- **work:** extend `test_logs.py` with U.5 — change logging via CLI while a model is running, verify documented semantics.
- **estimated_minutes:** 20.

### Step 10.5 — Slice W.3, W.4: Health edge cases
- **id:** `slice-W.edges`
- **depends_on:** `prereq.audit-existing`
- **work:** extend `test_health.py` with W.3 (model hang detection) and W.4 (missing health-check tool resilience).
- **estimated_minutes:** 30.

## 14. Phase 11 — Heavy: Download, Compare, Concurrency, Docker Colima

### Step 11.1 — Slice F: Model download from catalog
- **id:** `slice-F`
- **depends_on:** `slice-E.rest`
- **slice:** F.1–F.12
- **work:** `Tests/E2E/SliceF_DownloadCatalogTests.swift`. F.8 (interrupted) and F.9 (disk-full) require synthetic trigger setup. F.11 (auto-scan) drops a placeholder file and waits.
- **estimated_minutes:** 120.

### Step 11.2 — Slice G: Comparison
- **id:** `slice-G`
- **depends_on:** `slice-C.deployment-types`
- **work:** `Tests/E2E/SliceG_CompareTests.swift` + extend `test_query.py` for `multi_query.py` paths.
- **estimated_minutes:** 60.

### Step 11.3 — Slice S: Multi-model concurrency
- **id:** `slice-S`
- **depends_on:** `slice-G`, `slice-H.swift`
- **work:** `Tests/E2E/SliceS_ConcurrencyTests.swift` covering S.1–S.6. S.7 (OOM) covered by logging instead — not a test, a logging-coverage audit.
- **estimated_minutes:** 90.

### Step 11.4 — Slice J: Docker / Colima profile lifecycle
- **id:** `slice-J`
- **depends_on:** `slice-D.deployment-types`
- **work:** `Tests/E2E/SliceJ_DockerProfileTests.swift`. Skip cleanly if `colima` not installed.
- **estimated_minutes:** 120.

## 15. Phase 12 — aidevops platform registration

### Step 12.1 — `.aidevops-stack.yml` full registration
- **id:** `platform.stack-yml`
- **depends_on:** `slice-Inst.tests` (so Inst is at least testable)
- **slice:** N/A (cross-repo)
- **work:**
  - Create / expand `.aidevops-stack.yml` at repo root declaring every slice as a test suite entry.
  - Each entry: `id`, `name`, `runner_kind` (`swift` or `pytest`), `command`, `tier`, `requires`, `env`.
  - Follows the schema in `aidevops/schemas/aidevops-stack.schema.json` (already shipped per aidevops commits).
- **exit_criteria:** `node aidevops/tools/validate-stack-profile.js` passes against the file.
- **files_touched:** `.aidevops-stack.yml`.
- **fatal_on_failure:** YES.
- **estimated_minutes:** 60.

### Step 12.2 — Add `swift` runner_kind to aidevops command-router
- **id:** `platform.swift-runner`
- **depends_on:** `platform.stack-yml`
- **slice:** N/A (cross-repo edit in aidevops)
- **work:**
  - In aidevops repo: edit `server/modules/tests/command-router.js` to add `'swift'` to `KNOWN_RUNNER_KINDS` and wire execution path (likely `swift test --filter ...`).
  - Add a tiny test in aidevops for the new runner_kind.
  - Open as a separate PR in aidevops — this is not a llamaCPPManager-side edit.
- **exit_criteria:** aidevops accepts the new runner_kind; llamaCPPManager registration via `.aidevops-stack.yml` succeeds.
- **files_touched:** (cross-repo) `aidevops/server/modules/tests/command-router.js`.
- **fatal_on_failure:** no (llamaCPPManager-side registration still useful even before runner lands).
- **estimated_minutes:** 60.

### Step 12.3 — Verify registration end-to-end
- **id:** `platform.verify`
- **depends_on:** `platform.swift-runner`
- **work:** in aidevops UI, browse to llamaCPPManager's Repo Specs tab, see slice suites listed, trigger one (probably Slice A — default tier, fast), watch results land.
- **estimated_minutes:** 30.

## 16. Phase 13 — Final tidy

### Step 13.1 — Refresh manual smoke checklist
- **id:** `final.smoke-refresh`
- **depends_on:** all slice phases complete
- **work:** rewrite `docs/SWIFT-CONFORMANCE-PLAN.md` §11 manual smoke checklist to reference slice IDs and add items for flows still in manual-tier (Y.2–Y.5, P.6 if not automated, visual checks).
- **estimated_minutes:** 30.

### Step 13.2 — Mark `docs/E2E-SLICES.md` entries ✅
- **id:** `final.catalog-update`
- **depends_on:** all slice phases
- **work:** for every variant landed, flip status from `planned` to ✅ with version. Document any deferred variants with reason.
- **estimated_minutes:** 20.

## 17. Per-step commit & version-bump policy (executes during every step that changes code)

For each step that modifies code under `src/` or `gui-macos/Sources/`:

1. Reserve files via `queuectl reserve`.
2. Make edits.
3. Run relevant tests (`pytest` and/or `swift test --filter Slice...`).
4. If green, run `python3 ~/.ai-dev-dotfiles/tools/version-bump.py`.
5. Add a `CHANGELOG.md` entry under the new version.
6. Run `llamacpp-manager install-gui --force --no-launch` to sync Info.plist if GUI code changed.
7. Path-form commit with all touched files; descriptive message naming the slice ID(s) covered.
8. Release queue reservation.
9. Push.

For each step that modifies ONLY tests, docs, or scripts (no source code shipping to users):

- Steps 4 and 6 are skipped (no version bump).
- All other steps apply.

## 18. Fatal-on-failure declarations

Steps that are fatal (block all downstream work if they fail):

- `inst.deploy-sh` — every later phase assumes the deploy.sh contract exists.
- `platform.stack-yml` — Phase 12 can't proceed without it.

Steps that are NOT fatal (failure is recorded, downstream proceeds):

- All slice implementation steps (a failed slice variant becomes a logged gap, not a stop).
- All audit steps (gaps surfaced, plan continues).
- Cross-repo `platform.swift-runner` (aidevops change can land independently).

## 19. Recovery & resumability

If `/execute-plan` is interrupted (context limit, system restart, operator stop), the resumable plan state lives in `.plan-state.json` at repo root. To resume: re-invoke `/execute-plan` pointing at this file; it skips completed steps based on the state file + git history check.

## 20. Exit verdict for the whole plan

The plan is "complete" when:

1. Every variant in `docs/E2E-SLICES.md` is either ✅ landed or marked deferred-with-reason.
2. `cd gui-macos && swift test` reports ≥ baseline + new slice counts; 0 failures.
3. `pytest tests/` reports ≥ baseline + new test counts; 0 failures.
4. `bash deploy.sh verify` exits 0 on the dev machine.
5. `.aidevops-stack.yml` validates against the platform schema.
6. The full smoke checklist (`docs/SWIFT-CONFORMANCE-PLAN.md` §11) passes.

---

Questions: libor@arionetworks.com
