# E2E Vertical-Slice Tests — Canonical Catalog

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/docs/E2E-SLICES.md
**Description:** Canonical inventory of every vertical-slice E2E test (existing + planned) for llamaCPPManager. Each slice corresponds to one user-visible flow tested against the real stack — no mocks, no fakes. Variations within a slice enumerate code paths that genuinely diverge (different deployment_type, different process manager, different error mode). Companion document: `docs/SLICE-IMPLEMENTATION-PLAN.md` (the executable plan for landing the missing slices).
**Author:** Libor Ballaty <libor@arionetworks.com>
**Created:** 2026-06-24
**Last Updated:** 2026-06-25
**Last Updated By:** Libor Ballaty

---

## 1. What a slice is

A slice is **one user-visible flow** tested from intent to outcome against the real installed app, real CLI, real subprocesses, real model servers. No mocks. No fakes. No protocol seams whose only purpose is test injection. See `docs/SWIFT-AGENT-STANDARD.md` §18 for the testing philosophy.

A slice's **variations** are sub-tests where the code path genuinely diverges (e.g. native GGUF vs MLX vs MLX-VLM vs Docker — four different process managers). Pure input-only differences (different prompts, different model names) stay as parameterizations *within* a single variant, not as separate variants.

## 2. Strategy: real-stack hybrid

SwiftPM does not host true Apple XCUITest. Rather than convert this project to an Xcode project, slices use a pragmatic real-stack hybrid:

- **Launch:** `Process` invokes `/Applications/llamaCPP Manager.app/Contents/MacOS/llamacpp-gui` directly.
- **Drive:** `/usr/bin/osascript` runs AppleScript / System Events for clicks, keystrokes, menu navigation. Works for MenuBarExtra apps, which XCUITest struggles with.
- **Assert:** Read `~/Library/Logs/llamaCPPManager/lifecycle.jsonl` for `LifecycleLog` events emitted by production code, and use file system + `pgrep` checks where appropriate. No test-only hooks in production.
- **CLI consistency:** When a slice asserts GUI ↔ CLI agreement, it invokes `llamacpp-manager status --json` or `llamacpp-manager <cmd>` from inside the Swift test via `Process`.

Shared helpers live in `gui-macos/Tests/E2E/E2EHelpers.swift`. The CLI-side equivalents live as pytest fixtures.

## 3. Slice ID convention

Single capital letter (`A` … `Z`) plus optional decimal sub-variant (`A.1`, `A.2`). Used as:

- Filename suffix: `gui-macos/Tests/E2E/Slice<X>_<Name>.swift`
- Suite name: `@Suite("E2E Slice <X> — <Name>")`
- aidevops platform test ID: `slice-<x>` (lowercase)
- Smoke checklist references in `docs/SWIFT-CONFORMANCE-PLAN.md` §11

Slice IDs **A–C** are in tree as of v2026.06.24.5. **D–Z + Inst** are planned in `docs/SLICE-IMPLEMENTATION-PLAN.md`.

## 4. Variation axes (master reference)

| Axis | Values | Where divergent |
|---|---|---|
| `deployment_type` | `native` (llama.cpp GGUF) / `mlx` / `mlx-vlm` / `container` (Docker) / `experimental` | `process.py` / `mlx_process.py` / `mlx_vlm_process.py` / `docker_manager.py` |
| Mode per model | llama.cpp: `basic` / `tools` / `performance` / `extended`; MLX: `basic` / `think` | Different CLI args + server flags |
| Query type | `complete` vs `chat`; `stream=True` vs `stream=False` | `query.py` separate paths |
| Exclusive group | None / member | `launch` auto-stops siblings |
| launchd | Foreground subprocess / launchd daemon | `launchd.py` plist generation + bootout |
| Infrastructure component | cloudflared / llm_controller / mcp_server | Each has its own start/stop |
| Chat history | Persisted (SQLite) / ephemeral | `chat_storage.py` involvement |
| Concurrency | One-at-a-time / parallel | Race surface |
| Permission gate | Default / `RUN_E2E_INTERACTIVE` / accessibility-granted | Skip vs execute |

## 5. Tier classification (for the platform + default `swift test`)

| Tier | Meaning | Runs in default `swift test`? |
|---|---|---|
| `default` | Real stack, no UI driving needed; safe for unattended runs | yes |
| `interactive` | UI-driving via osascript; requires Accessibility-granted runner | only when `RUN_E2E_INTERACTIVE=1` |
| `heavy` | Long runtime (model load, download, multi-model startup) or requires extra infrastructure (Colima) | only when `RUN_E2E_INTERACTIVE=1` and `RUN_E2E_HEAVY=1` |
| `manual-smoke` | Cannot reasonably be driven from `swift test` (visual polish, animation timing) | documented checklist, not auto-run |

## 6. Slice catalog

### A — App Launch & Boot

**Intent:** "Open the app and see my models."
**Flow:** install → launch → menu bar icon → status fetch → rows populated.
**Tier:** default for A.1; interactive for A.2–A.6 (some need UI driving).

| Variant | Status | Notes |
|---|---|---|
| A.1 — Fresh launch, models configured | ✅ v2026.06.24.4 | `SliceA_LaunchTests.swift` |
| A.2 — Fresh launch, **no models configured** | planned | Empty `rows` array, UI must not crash |
| A.3 — Fresh launch, **CLI not installed** (renamed binary on PATH) | planned | Typed error surfaced; no zombies |
| A.4 — Stale build detection (install-gui staleness check) | planned | Regression for v.5 fix |
| A.5 — Launch while another instance is already running | planned | Single-instance behavior |
| A.6 — Sub-2s relaunch after Quit | planned | Lifecycle log + window state shouldn't leak |

### B — Chat Window Lifecycle

**Intent:** "Open a chat with a model and close it cleanly."
**Tier:** interactive.

| Variant | Status |
|---|---|
| B.1 — Open chat, Cmd-W close, single model | ✅ v2026.06.24.5 |
| B.2 — Two model chat windows concurrently | planned |
| B.3 — Switch apps, switch back, Cmd-W | planned |
| B.4 — Close via red button, then reopen same model | planned |
| B.5 — Quit without explicit close, then relaunch | planned |
| B.6 — Open chat while model is stopping (race) | planned |

### C — Chat Send & Receive

**Intent:** "Send a message and get an answer."
**Tier:** interactive (C.1) / interactive+heavy (others).

| Variant | Status |
|---|---|
| C.1 — Native GGUF, blocking, basic mode | ✅ v2026.06.24.5 |
| C.2 — **MLX** model | planned |
| C.3 — **MLX-VLM** model with image input | planned |
| C.4 — **Docker-wrapped** model | planned |
| C.5 — Send to model **not currently running** | planned |
| C.6 — Crash mid-reply (kill model during query) | planned |
| C.7 — Streaming mode | planned |
| C.8 — System prompt present | planned |
| C.9 — Chat history persisted across app restart | planned (SQLite) |
| C.10 — Long reply (>10KB) | planned |
| C.11 — Empty / whitespace-only message | planned |
| C.12 — Rapid-fire 3 messages before first reply | planned |

### D — Start/Stop + GUI↔CLI Consistency

**Intent:** "Start a model and stop it cleanly; CLI and GUI agree at all times."
**Tier:** interactive.

| Variant | Status |
|---|---|
| D.1 — Native GGUF start/stop, GUI ↔ CLI agree | planned |
| D.2 — MLX start/stop | planned |
| D.3 — MLX-VLM start/stop | planned |
| D.4 — Docker-wrapped start/stop | planned |
| D.5 — Start already-running model (idempotent) | planned |
| D.6 — Stop already-stopped model (idempotent) | planned |
| D.7 — Start with port conflict | planned (typed error) |
| D.8 — Start then immediately stop (race) | planned |
| D.9 — `start all` bulk operation | planned |
| D.10 — Restart Active (bulk) | planned |

### E — Model Configuration CRUD

**Intent:** "Add a model, update it, remove it."
**Tier:** default (CLI-driven E.1–E.8, E.10, E.11) + interactive (E.9).

| Variant | Status |
|---|---|
| E.1 — `config add` GGUF | partial via `test_cli_config.py` |
| E.2 — `config add` MLX | planned (verify type-specific defaults) |
| E.3 — `config add` MLX-VLM | planned |
| E.4 — `config add` Docker | planned |
| E.5 — `config update --port` | partial |
| E.6 — `config update --autostart` toggle | partial |
| E.7 — `config remove` while running | planned (force-stop semantics) |
| E.8 — `config migrate` from older schema | `test_migrate.py` exists; verify edges |
| E.9 — GUI "Configure" button after download | planned |
| E.10 — Invalid path / missing file validation | partial |
| E.11 — `config add` with exclusive group | planned |

### F — Model Download from Catalog

**Intent:** "Browse, filter, download, see it in my config."
**Tier:** interactive-heavy.

| Variant | Status |
|---|---|
| F.1 — Download GGUF from HuggingFace | planned |
| F.2 — Download MLX-format model | planned |
| F.3 — Download MLX-VLM model (multi-file) | planned |
| F.4 — Filter by format | planned |
| F.5 — Filter by size | planned |
| F.6 — Filter by use-case | planned |
| F.7 — Search text filter | planned |
| F.8 — Download interrupted (network drop / cancel) | planned |
| F.9 — Disk-full target | planned |
| F.10 — Re-download existing (overwrite) | planned |
| F.11 — External download auto-scan | planned |
| F.12 — Download → "Configure" → config entry | planned |

### G — Model Comparison (Multi-Model Query)

**Intent:** "Ask 2+ models the same question, see side-by-side answers."
**Tier:** interactive-heavy.

| Variant | Status |
|---|---|
| G.1 — Compare 2 GGUF | planned |
| G.2 — Compare 2 MLX | planned |
| G.3 — Compare GGUF + MLX (heterogeneous) | planned |
| G.4 — Compare 5 models | planned (stress) |
| G.5 — One model not running (partial result) | planned |
| G.6 — One model crashes mid-query | planned |
| G.7 — Same prompt vs per-model prompts | planned |

### H — Crash Detection & Auto-Restart

**Intent:** "When a model crashes, the system restarts it automatically."
**Tier:** default (pytest portion) + interactive (Swift slice).
**Reliability importance:** HIGH — largest current reliability gap (no `test_monitor.py` exists today).

| Variant | Status |
|---|---|
| H.1 — Native GGUF crash → monitor restarts | planned |
| H.2 — MLX crash recovery | planned |
| H.3 — MLX-VLM crash recovery | planned |
| H.4 — Docker model crash recovery | planned |
| H.5 — Repeated crashes (3+ in N min) → backoff/give-up | planned |
| H.6 — Crash during chat | planned |
| H.7 — One crashes, others stay healthy (isolation) | planned |
| H.8 — Monitor daemon itself dies → launchd restarts it | planned |
| H.9 — Track an autostart=false model | planned (design call) |
| H.10 — Untrack removes from watch | planned |

### I — Autostart on Boot

**Intent:** "When the Mac boots, autostart-tagged models come up."
**Tier:** default (no GUI; CLI + launchd).

| Variant | Status |
|---|---|
| I.1 — Single autostart model | partial via `test_ensure_running.py` |
| I.2 — Multiple autostart models in parallel | partial |
| I.3 — Autostart in exclusive group | planned |
| I.4 — Autostart with port taken | planned (clean failure) |
| I.5 — Plist installed but `ensure-running` not called | planned |
| I.6 — Mix of autostart + manual | planned |

### J — Docker / Colima Profile Lifecycle

**Intent:** "Create a Colima profile, run a model under it, manage the profile."
**Tier:** interactive-heavy.

| Variant | Status |
|---|---|
| J.1 — Create profile, minimal flags | planned |
| J.2 — Create profile, all flags | planned |
| J.3 — Create existing profile (error) | planned |
| J.4 — Create with colima not installed (pre-flight) | planned |
| J.5 — Profile lifecycle: start → list → start container → stop → restart | planned |
| J.6 — Stop profile with running containers | planned |
| J.7 — Delete profile (confirmation) | planned |
| J.8 — Mid-create cancellation (regression for v.7 fix) | planned |
| J.9 — Container logs tail | planned |

### K — Infrastructure Components

**Intent:** "Start/stop cloudflared, controller, MCP server."
**Tier:** default (pytest) + interactive (Swift).

| Variant | Status |
|---|---|
| K.1 — Cloudflared start/stop | partial via `test_infrastructure.py` |
| K.2 — llm_controller start/stop | partial |
| K.3 — **MCP server start/stop + GUI visibility** | planned (closes long-standing backlog item) |
| K.4 — Component fails to start (clear error) | planned |
| K.5 — All three running concurrently | planned |
| K.6 — Graceful timeout vs SIGKILL | planned |
| K.7 — Per-component log viewing | planned |

### L — Preferences Edit & Persist

**Intent:** "Change a setting, restart app, setting sticks."
**Tier:** interactive.

| Variant | Status |
|---|---|
| L.1 — Change logging level → persist across restart | planned |
| L.2 — Toggle timestamps | planned |
| L.3 — Bootstrap mlx-vlm preference | planned |
| L.4 — Reset to Defaults | planned |
| L.5 — Save while other ops running (no corruption) | planned |
| L.6 — Invalid value validation | planned |

### M — Logs Viewing & Filtering

**Intent:** "Open live logs for a model and follow them."
**Tier:** interactive.

| Variant | Status |
|---|---|
| M.1 — Open logs for running model (live tail) | planned |
| M.2 — Open logs for stopped model (historical) | planned |
| M.3 — Open logs for never-started model (empty) | planned |
| M.4 — Infrastructure component logs | planned |
| M.5 — Filter (severity/search) | planned |
| M.6 — Logs while logging disabled globally | planned |
| M.7 — Log rotation mid-view | planned |

### N — MCP Agentic Surface (9 tools)

**Intent:** "External LLM agent uses llamaCPPManager via MCP-over-stdio."
**Tier:** default.

| Variant | Status |
|---|---|
| N.1 — `list_models` happy + schema lock | partial via `test_mcp_server.py` |
| N.2 — `list_available_models` | partial |
| N.3 — `start_model` happy + invalid model error | partial |
| N.4 — `stop_model` happy + idempotent | partial |
| N.5 — `model_status` happy + not-found | partial |
| N.6 — `query_completion` real-stack | partial |
| N.7 — `query_chat` real-stack + multi-turn | partial |
| N.8 — `add_model` + validation errors | partial |
| N.9 — `remove_model` + while-running | partial |
| N.10 — Each tool: invalid arg validation | planned |
| N.11 — Each tool: model not running (where applicable) | planned |
| N.12 — Each tool: output schema lock | planned |
| N.13 — MCP server restart mid-session reconnect | planned |
| N.14 — `query_chat` with multi-turn history | planned |
| N.15 — No models configured (graceful empty) | planned |
| N.16 — Concurrent tool calls from one session | planned |

### O — `status --json` Schema Lock

**Intent (implicit):** "Anyone parsing my status output never silently breaks."
**Tier:** default.

| Variant | Status |
|---|---|
| O.1 — Empty config → schema valid | planned |
| O.2 — All deployment_type variants present | planned |
| O.3 — Mixed running/stopped | partial via `test_status.py` |
| O.4 — Infrastructure components included | planned |
| O.5 — Optional fields handled | planned |
| O.6 — JSON vs default output strict separation | planned |
| O.7 — Schema lock against versioned spec | planned |

### P — Clean Shutdown & Cleanup

**Intent:** "Quit cleans up — no zombies, no leaked files."
**Tier:** interactive.

| Variant | Status |
|---|---|
| P.1 — Quit with no models running | planned |
| P.2 — Quit with 1 model running (child cleanup) | planned |
| P.3 — Quit with multiple models | planned |
| P.4 — Quit with chat window open | planned |
| P.5 — Quit during download | planned |
| P.6 — Force-kill (SIGKILL) app process (recovery) | planned |
| P.7 — `cleanup` CLI for orphans | planned |
| P.8 — Quit with monitor daemon running (daemon stays) | planned |

### Q — Discovery & Auto-detection

**Intent:** "I dropped a model into `~/llms/` — the app finds it."
**Tier:** default.

| Variant | Status |
|---|---|
| Q.1 — GGUF file discovered | partial via `test_discovery_parse.py` |
| Q.2 — MLX folder structure discovered | partial |
| Q.3 — MLX-VLM model discovered | planned |
| Q.4 — Symlinked model directory followed | planned |
| Q.5 — Permission-denied directory graceful skip | planned |
| Q.6 — Catalog refresh during discovery (race) | planned |

### R — Bootstrap (mlx-vlm setup)

**Intent:** "Set up optional MLX-VLM backend."
**Tier:** default + heavy (downloads / venv).

| Variant | Status |
|---|---|
| R.1 — Fresh install (venv + mlx-vlm) | planned |
| R.2 — Re-run when already installed (idempotent) | planned |
| R.3 — Python version mismatch (clear error) | planned |
| R.4 — Intel Mac refusal (no MLX support) | planned |

### S — Multi-Model Concurrency

**Intent:** "Multiple models running simultaneously without interference."
**Tier:** heavy.

| Variant | Status |
|---|---|
| S.1 — 3 native models in parallel | planned |
| S.2 — Heterogeneous (native + MLX + MLX-VLM) concurrent | planned |
| S.3 — Failure isolation (one crashes, others healthy) | planned |
| S.4 — Chat with A while starting B (no deadlock) | planned |
| S.5 — Stop all during some starts (race resolution) | planned |
| S.6 — Exclusive group `launch` semantics | planned |
| S.7 — Memory pressure (OOM) → logged not silent | planned (logging coverage) |

### T — CLI Invocation from External Processes

**Intent (implicit):** "Other tools (aidevops, Codex, scripts) shell out to `llamacpp-manager` and parse output."
**Tier:** default.

| Variant | Status |
|---|---|
| T.1 — Invoked without TTY (piped) — same JSON shape | planned |
| T.2 — UTF-8 / encoding safety | planned |
| T.3 — Missing dependency tool (e.g. `pgrep`) — clear error | planned |
| T.4 — Concurrent invocations — file-lock safety | planned |
| T.5 — Exit-code contract locked | planned |
| T.6 — Stdout/stderr clean separation | planned |

### U — Logging Configuration Lifecycle

**Intent:** "Enable/disable logging, change verbosity."
**Tier:** default.

| Variant | Status |
|---|---|
| U.1 — `logging enable` → next start logs | partial via `test_logs.py` |
| U.2 — `logging disable` → next start silent | partial |
| U.3 — `logging timestamps` toggle | partial |
| U.4 — `logging set` per-model override | partial |
| U.5 — Apply-to-running vs next-start semantics locked | planned |

### V — Cleanup Command

**Intent:** "Clean up after a crash / leftover state."
**Tier:** default.

| Variant | Status |
|---|---|
| V.1 — Normal cleanup with no orphans (no-op) | planned |
| V.2 — Orphan model processes killed | planned |
| V.3 — Orphan launchd plists removed | planned |
| V.4 — Lock files / temp dirs cleaned | planned |
| V.5 — Doesn't kill legitimately running model | planned |

### W — Health Endpoint / Watch

**Intent (passive):** "Continuous health awareness of running models."
**Tier:** default.

| Variant | Status |
|---|---|
| W.1 — Model healthy → status reflects | partial via `test_health.py` |
| W.2 — Model warming up (started, not yet responsive) | partial via `test_status_watch.py` |
| W.3 — Model hangs (responsive then stops) | planned |
| W.4 — Health check tool missing (no poison) | planned |

### X — Lifecycle Log Schema Stability

**Intent (implicit):** "The lifecycle log is the contract for E2E slices and external observers."
**Tier:** default.

| Variant | Status |
|---|---|
| X.1 — Every event has timestamp + event + source + pid | planned |
| X.2 — Known events fire in expected order | implicitly enforced by every E2E slice |
| X.3 — Event names schema-locked | planned |
| X.4 — Log rotation doesn't lose events | planned |

### Y — Minor UI Flows (About / Help / Reveal / Open CLI / Open Config)

**Tier:** manual-smoke (most) + lightweight default (Y.1).

| Variant | Status |
|---|---|
| Y.1 — About dialog version matches APP_VERSION + VERSION file | planned (default tier) |
| Y.2 — Help opens documented destination | planned (smoke) |
| Y.3 — Open CLI opens Terminal in correct cwd | planned (smoke) |
| Y.4 — Open Config reveals `~/.llamacpp-manager/` | planned (smoke) |
| Y.5 — Row "Reveal" reveals model directory | planned (smoke) |

### Inst — Deployment & Installation 🆕

**Intent:** "Install or upgrade llamaCPPManager — backend (CLI + MCP server + deps) and frontend (macOS GUI) — on a fresh or upgrading machine, and verify it works."
**Tier:** default (most) + heavy (full fresh install simulation).

Coverage spans both the existing `gui-macos/install_gui.sh` (GUI installer) and a **new `deploy.sh` at repo root** (backend installer fulfilling aidevops Release Workflow contract per TODO #122).

| Variant | Status | Notes |
|---|---|---|
| Inst.1 — `install-gui` happy path (rebuild + replace + MD5 verify + launch) | partial (smoke item 1) | Promote to E2E |
| Inst.2 — `install-gui --no-rebuild` reuses existing build | planned | |
| Inst.3 — `install-gui --no-launch` installs but doesn't open | partial | Already used by E2E harness |
| Inst.4 — `install-gui --force` rebuilds even if MD5 matches | planned | |
| Inst.5 — `install-gui` detects stale build (VERSION mtime > binary mtime) | planned | Regression for v.5 fix |
| Inst.6 — MD5 mismatch detection → install fails with exit 5 | planned | |
| Inst.7 — Install kills running app instances cleanly | planned | |
| Inst.8 — Permission failure on `/Applications` write → exit 3 | planned | |
| Inst.9 — Build failure → exit 2, app/install untouched | planned | |
| Inst.10 — `deploy.sh build` produces correct artifacts | planned | new `deploy.sh` |
| Inst.11 — `deploy.sh install` installs Python CLI via pipx | planned | |
| Inst.12 — `deploy.sh install` verifies MCP server entry point | planned | `llamacpp-mcp-server` on PATH after install |
| Inst.13 — `deploy.sh verify` runs sanity checks (CLI runs, GUI app present, MCP entry exists) | planned | |
| Inst.14 — `deploy.sh` checks dependencies (python, swift, macOS version, pipx) and reports missing | planned | |
| Inst.15 — `deploy.sh deploy-local` full end-to-end (backend + frontend + verify) | planned | |
| Inst.16 — `deploy.sh` source_revision pin (matches aidevops Release Workflow contract) | planned | |
| Inst.17 — Upgrade scenario: prior version installed, new version replaces cleanly | planned | |
| Inst.18 — Idempotent: running `deploy.sh install` twice in a row is safe | planned | |

## 7. Coverage matrix (one-look)

| ID | Flow | Variants | In tree | Planned |
|---|---|---:|---:|---:|
| A | App Launch & Boot | 6 | 1 | 5 |
| B | Chat Window Lifecycle | 6 | 1 | 5 |
| C | Chat Send & Receive | 12 | 1 | 11 |
| D | Start/Stop GUI↔CLI Consistency | 10 | 0 | 10 |
| E | Model Config CRUD | 11 | 0 (partial pytest) | 11 |
| F | Model Download from Catalog | 12 | 0 | 12 |
| G | Model Comparison | 7 | 0 | 7 |
| H | Crash Detection & Auto-Restart | 10 | 0 | 10 |
| I | Autostart on Boot | 6 | 0 (partial pytest) | 6 |
| J | Docker / Colima Lifecycle | 9 | 0 | 9 |
| K | Infrastructure Components | 7 | 0 (partial pytest) | 7 |
| L | Preferences | 6 | 0 | 6 |
| M | Logs Viewer | 7 | 0 | 7 |
| N | MCP Agentic Surface | 16 | 0 (partial pytest) | 16 |
| O | status --json Schema Lock | 7 | 0 (partial pytest) | 7 |
| P | Clean Shutdown & Cleanup | 8 | 0 | 8 |
| Q | Discovery & Auto-detection | 6 | 0 (partial pytest) | 6 |
| R | Bootstrap mlx-vlm | 4 | 0 | 4 |
| S | Multi-Model Concurrency | 7 | 0 | 7 |
| T | External CLI Invocation | 6 | 0 | 6 |
| U | Logging Lifecycle | 5 | 0 (partial pytest) | 5 |
| V | Cleanup Command | 5 | 0 | 5 |
| W | Health Endpoint / Watch | 4 | 0 (partial pytest) | 4 |
| X | Lifecycle Log Schema | 4 | 0 (implicit) | 4 |
| Y | Minor UI Flows | 5 | 0 | 5 |
| Inst | Deployment & Installation | 18 | 0 (partial smoke) | 18 |
| **TOTAL** | | **202** | **3** | **199** |

Note: many "planned" variants reuse existing pytest coverage that just needs to be labeled / linked to a slice ID rather than written from scratch.

## 8. How to run

### Default (CI-safe)

```bash
cd gui-macos && swift test
```

Runs Slice A real-stack + all `default`-tier pytest. Skips `interactive` and `heavy` tiers with a clear message.

### Interactive (local dev with Accessibility-granted shell)

```bash
cd gui-macos && RUN_E2E_INTERACTIVE=1 swift test
```

Plus interactive tier (B, D, L, M, P).

### Full heavy (model load, downloads, Colima)

```bash
cd gui-macos && RUN_E2E_INTERACTIVE=1 RUN_E2E_HEAVY=1 swift test
```

Plus heavy tier (C variants, F, G, J, R, S).

### Filter a single slice

```bash
swift test --filter SliceA
swift test --filter SliceInst
```

## 9. Platform registration (aidevops)

The slice catalog is registered in aidevops via `.aidevops-stack.yml` at repo root (proposed). Each slice becomes a test suite entry. See `docs/SLICE-IMPLEMENTATION-PLAN.md` for the registration step.

## 10. Related documents

- `docs/SLICE-IMPLEMENTATION-PLAN.md` — executable plan to land all planned variants
- `docs/SWIFT-AGENT-STANDARD.md` §18 — testing philosophy
- `docs/SWIFT-CONFORMANCE-PLAN.md` §11 — manual smoke checklist
- `gui-macos/Tests/E2E/E2EHelpers.swift` — shared real-stack test infrastructure

---

Questions: libor@arionetworks.com
