# llamaCPPManager — Known Issues

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/KNOWN-ISSUES.md
**Description:** Issues discovered while diagnosing Mistral-Small-3.2-24B tool-calling failures on port 8089 (2026-07-27). Recorded for follow-up.
**Author:** Claude (Opus 4.8)
**Created:** 2026-07-27
**Last Updated:** 2026-07-29
**Last Updated By:** Claude (Opus 4.8) — verify-reconcile pass

## Context
Session traced a Mistral-Small-3.2-24B tool-call crash (`</s>` parse 500) on 8089 to an outdated llama.cpp binary (b8559). Fixed by building b10154 and pointing the manager at it. Along the way, several manager issues surfaced.

## Update 2026-07-28 — external-process visibility now surfaced in `status`
A follow-up session (commit `8ac9a5d`, v2026.07.28.1) addressed the **visibility** half of the "server runs on 8089 but the manager didn't start it" confusion that underlies several issues here (esp. I7). `status` now reports `process_source: "external"` for a live server discovered only by port scan (no manager PID file, no launchd plist), and adds `logs_available` / `logs_hint` fields plus a `⚠` note; `logs <model>` warns the log may be stale. This visibility commit did **not** by itself fix the root causes below — it just makes an unmanaged/externally-started process obvious instead of looking like a silent logging bug.

**Root-cause status as of the 2026-07-28 remediation batch (v2026.07.28.2–.4):** I1 (reclassified; README fixed), I3, I5, I6 (largely), I8, and I9 were subsequently **closed** in later commits the same day (see per-issue entries below for commit hashes). I2 is moot. The only items still **open** are **I4** (canonical llama.cpp build/version *policy*, low) and **I7** (kill/restart lifecycle, deferred — needs supervised live testing, bundles with the I9 live-launchd check).

## Issues

### I1 — Two divergent configs; unclear which is authoritative  (severity: high) — **RECLASSIFIED 2026-07-28: original premise FALSE; root cause was a stale README. Doc fixed.**
- **Original claim (2026-07-27):** "pipx CLI reads `~/.config/llamacpp-manager/models.yaml`; GUI reads `~/Library/Application Support/llamaCPPManager/config.yaml`; they diverge."
- **Verified false (2026-07-28):** `config.py:load_config()` → `utils.py:config_path()` reads **only** `~/Library/Application Support/llamaCPPManager/config.yaml`. There is **no code path** that reads `~/.config/llamacpp-manager/models.yaml`. The CLI and GUI already share one source of truth (confirmed: `llamacpp-manager config list --json` returns the 36-model Application Support config, not the 15-model `~/.config` file).
- **Actual root cause:** `README.md` (→ packaged `PKG-INFO`) documented the config location as `~/.config/llamacpp-manager/models.yaml` **and** used a legacy dict schema (`path`/`context_size`/`auto_start`). An operator/tool following that doc creates a `~/.config/.../models.yaml` that nothing reads — producing the exact "edit does nothing" symptom, but from a dead orphan file, not a competing live config.
- **Fix applied 2026-07-28:** README Model Configuration section corrected — right path (`~/Library/Application Support/llamaCPPManager/config.yaml`), correct list schema, note that `~/.config/llamacpp-manager/` is catalog-cache-only, and guidance to prefer `config add/update` over hand-editing.
- **Residual (open, low):** an orphan `~/.config/llamacpp-manager/models.yaml` (15 models, includes a **duplicate port 8089** for `mistral-small-3.2-24b` + `qwen-32b`) exists on this host, birth-time 2026-07-28 17:08 — provenance unconfirmed (possibly written by hermes or a personal script; **not** the manager). It is inert. Operator decision: delete it or leave it. The manager will never read it.

### I2 — pipx CLI `llama_server_path` points at a non-existent binary  (severity: high) — **CLOSED / MOOT 2026-07-28**
- **Original claim (2026-07-27):** `~/.config/llamacpp-manager/models.yaml` → `llama_server_path: /opt/homebrew/bin/llama-server` (does not exist).
- **Status 2026-07-28:** Moot — that file is not read by the manager (see I1). Independently, the orphan file's `llama_server_path` has since been updated to the valid local build path, and the **live** config's `llama_server_path` = `/Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llama.cpp/build/bin/llama-server`. No CLI-cannot-start-native-models condition exists from this cause.
- **Confirmed 2026-07-28:** live `llama.cpp/build/bin/llama-server` reports `version: 10154 (0e4a03622)` (built 2026-07-27 23:37). The 2026-07-27 mitigation has been consolidated — the canonical `llama.cpp/build` was rebuilt to b10154 and the temporary `llama.cpp-b10154/` dir no longer exists. No regression to b8559. Both live config and orphan file point at this valid b10154 binary.

### I3 — Single global `llama_server_path`; no per-model binary override  (severity: medium) — **CLOSED 2026-07-28 (v2026.07.28.3)**
- `build_argv` / config use one global binary for all models. Can't run one model on a fixed/newer llama.cpp build while leaving others on another.
- **Impact:** forced the 2026-07-27 fix to repoint the global path (acceptable only because other models were deprioritized). A per-model `llama_server_path` / build override would be the correct design.
- **Fixed 2026-07-28:** added optional `llama_server_path` to `ModelSpec`; `build_argv` and `launchd.build_program_arguments` resolve `spec.llama_server_path or <global>`. Surfaced via `config add/update --llama-server-path` (empty string clears). `start`'s binary pre-check and `start_process`'s fail-loud check both resolve per-model. Persisted only when set (omitted from YAML otherwise). Tests in `test_process.py` / `test_config.py`.

### I4 — Stale/crashing binary shipped as the default path  (severity: high, mitigated)
- GUI `llama_server_path` was `…/llama.cpp/build/bin/llama-server` (build **b8559**), which crashes on Mistral-Small-3.2 tool calls (`Failed to parse input at pos N: </s>`), fixed upstream in llama.cpp **b10154**.
- **Mitigation applied 2026-07-27:** GUI `llama_server_path` repointed to `…/llama.cpp-b10154/build/bin/llama-server`.
- **Consolidated 2026-07-28 (verified):** the canonical `…/llama.cpp/build/bin/llama-server` was itself rebuilt to **b10154** (`--version` → `10154 (0e4a03622)`, built 2026-07-27 23:37); the temporary `llama.cpp-b10154/` dir is gone and both configs point at the canonical path. The crash-binary condition is cleared for now.
- **Follow-up (still open):** decide the canonical llama.cpp build/version *policy* so the canonical `build/` can't silently regress to an old commit on the next rebuild. A per-model `llama_server_path` / build override (see I3) is the durable fix.

### I5 — Duplicate `--ctx-size` in launch argv  (severity: low) — **CLOSED 2026-07-28 (v2026.07.28.2)**
- mistral entry yields `--ctx-size 32768 … --ctx-size 65536` (mode default from `build_argv` + per-model `args: [--ctx-size, '65536']`). Last wins (65536), so harmless, but sloppy and confusing in logs.
- **Fixed 2026-07-28:** `build_argv` collects the `--` flags present in `spec.args` and skips the matching default (generalized to all base/mode-default flags, not just `--ctx-size`), so each flag appears exactly once with the model's value.

### I6 — Mode preset ≠ binary; mode switch can silently revert the binary  (severity: medium) — **LARGELY CLOSED 2026-07-28 (via I3)**
- Modes (basic/tools/performance/extended in `process.py:build_argv`) only control flags (`--jinja`, `--flash-attn`, `--parallel/--batch`). Switching mode restarts the server, which re-reads `llama_server_path` — so a mode change can silently swap the binary back to the configured (possibly stale) one.
- **Impact:** on 2026-07-27, switching the mistral to "tools mode" relaunched it on the old b8559 binary, re-introducing the crash until the config was repointed.
- **Status 2026-07-28:** with per-model `llama_server_path` (I3), pin a model's binary and a mode switch can no longer swap it — the binary is part of the model's config, not the mode. Also fixed a related latent bug: `monitor.py` / `model_manager.py` built `ModelSpec` without `mode`/`ctx_size`/`n_gpu_layers`, so an **auto-restart relaunched the model in basic mode with default context** regardless of config; all start paths now go through the canonical `config.spec_from_dict`. Residual (open, low): mode presets still bundle flags; a fully orthogonal "flags vs binary vs slots" config model is deferred.

### I7 — Kill/restart lifecycle reparents to launchd; TERM not always honored  (severity: low) — **OPEN (deferred 2026-07-28; supervised fix required)**
- Server started via a generated `/tmp/tmp*.sh` script; child `llama-server` reparents to launchd (pid 1) when the script exits, and survived a SIGTERM (needed SIGKILL).
- **Impact:** headless stop/restart is unreliable; manager should track the real llama-server pid and stop it directly.
- **Deferred 2026-07-28:** the timestamped-log path's wrapper + `pgrep -P` + `start_new_session` machinery has a documented history of subtle breakage ("models die ~30s after start"). `stop_process` already escalates SIGTERM→SIGKILL, so severity is low. A fix needs live start/stop/restart verification on the actual machine, not just unit tests — explicitly excluded from the autonomous batch.

### I8 — b10154 defaults to 4 parallel slots; tools/basic modes don't set `--parallel`, so context is silently split 4×  (severity: high, mitigated) — **CLOSED 2026-07-28 (v2026.07.28.2)**
- llama.cpp **b10154** defaults to **4 slots** (`total_slots: 4`), dividing `--ctx-size` across them (e.g. 65536 → 16384 per request).
- `build_argv` only sets `--parallel` in **performance** mode (=4). tools/basic/extended modes leave it at the server default, which on b10154 is 4 — so a single-user request gets only ctx/4.
- Combined with hermes v0.19's large system prompt (37+ synced skills + tool schemas ~16k tokens), the per-request budget was nearly exhausted → `Context length exceeded (44 tokens). Cannot compress further.` on every tool call.
- **Mitigation applied 2026-07-27:** added `--parallel 1` (and `--flash-attn on`) to the mistral-small-24b per-model `args` in the GUI config, giving one request the full 65536 context. Verified: hermes `read_file` tool call succeeds.
- **Fix for the manager:** for single-user/agentic models, default `--parallel 1` (or make it a per-model/per-mode setting); don't let mode presets silently inherit a 4-slot server default.
- **Fixed 2026-07-28:** `build_argv` now emits `--parallel 1` for basic/tools/extended; `performance` keeps 4. Per-model `--parallel` in `args` overrides. Tests in `test_process.py`.

### I9 — launchd argv builder diverges from `build_argv`  (severity: medium) — **CLOSED 2026-07-28 (v2026.07.28.4)**
- `launchd.build_program_arguments` is a second, simpler argv builder: `[binary, -m, model_path] + spec.args + [--host, --port]`. It does **not** apply `--n-gpu-layers`, `--ctx-size`, mode flags, or the new `--parallel 1` default. So a model started via a launchd agent gets a materially different (and worse) launch command than the same model started via `llamacpp-manager start`.
- **Impact:** autostart/launchd models silently miss GPU offload, context sizing, jinja/tool support, and single-slot pinning. The 2026-07-28 I3 fix made it honor the per-model binary, but the flag divergence remains.
- **Fixed 2026-07-28:** `build_program_arguments` now delegates to `process.build_argv`, so launchd `ProgramArguments` are byte-identical to what `start` runs (GPU offload, ctx sizing, mode flags, `--parallel 1`, dedup, per-model binary). `test_launchd.py::test_render_plist_matches_start_argv` asserts equality. **Behavior change:** like `start`, launchd render now validates the model file exists (raises if missing) — installing an agent for a missing model now fails loud instead of writing a plist that would fail at load.
- **Not yet verified against a live launchd agent** — asserted equal to the verified `start` argv via unit test; a real `launchd install` + reload on the machine is the remaining supervised check (bundles naturally with I7).

## Mode reference (from `src/llamacpp_manager/process.py:build_argv`)
| Mode | Extra flags (beyond `--ctx-size <n>` default 32768, `--n-gpu-layers 999`) |
|------|---------------------------------------------------------------------------|
| basic | *(none)* — no `--jinja`, so **no tool calling** |
| tools | `--jinja` |
| performance | `--jinja --parallel 4 --batch-size 512 --ubatch-size 512` |
| extended | `--jinja --flash-attn on` |
