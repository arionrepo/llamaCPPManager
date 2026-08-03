# llamaCPPManager — Known Issues

**File:** /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/KNOWN-ISSUES.md
**Description:** Issues discovered while diagnosing Mistral-Small-3.2-24B tool-calling failures on port 8089 (2026-07-27). Recorded for follow-up.
**Author:** Claude (Opus 4.8)
**Created:** 2026-07-27
**Last Updated:** 2026-08-03
**Last Updated By:** Claude (Opus 4.8) — live lifecycle test findings (I10–I12)

## Context
Session traced a Mistral-Small-3.2-24B tool-call crash (`</s>` parse 500) on 8089 to an outdated llama.cpp binary (b8559). Fixed by building b10154 and pointing the manager at it. Along the way, several manager issues surfaced.

## Update 2026-07-28 — external-process visibility now surfaced in `status`
A follow-up session (commit `8ac9a5d`, v2026.07.28.1) addressed the **visibility** half of the "server runs on 8089 but the manager didn't start it" confusion that underlies several issues here (esp. I7). `status` now reports `process_source: "external"` for a live server discovered only by port scan (no manager PID file, no launchd plist), and adds `logs_available` / `logs_hint` fields plus a `⚠` note; `logs <model>` warns the log may be stale. This visibility commit did **not** by itself fix the root causes below — it just makes an unmanaged/externally-started process obvious instead of looking like a silent logging bug.

**Root-cause status as of the 2026-07-28 remediation batch (v2026.07.28.2–.4):** I1 (reclassified; README fixed), I3, I5, I6 (largely), I8, and I9 were subsequently **closed** in later commits the same day (see per-issue entries below for commit hashes). I2 is moot. Still **open** from that batch: **I4** (canonical llama.cpp build/version *policy*, low). **I7** (kill/restart lifecycle) was **CLOSED 2026-08-03** — verified live (no code change needed; the real-pid tracking + SIGTERM→SIGKILL machinery works, and I9/I10/I11/I12 stabilized the path).

**New issues from the 2026-07-29 live lifecycle test (corrected 2026-08-01):** **I10** (`start`/`restart` CLI hangs after spawning) — **CLOSED 2026-08-03 (v2026.08.03.3)**; **I11** (MLX `restart` port-release race) — **CLOSED 2026-08-03 (v2026.08.03.2)**; **I12** (`/tmp` timestamp-wrapper scripts leak) — **CLOSED 2026-08-03 (v2026.08.03.1)**. See the "Live lifecycle test results" block and per-issue entries below.

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

### I4 — Stale/crashing binary shipped as the default path  (severity: high, mitigated) — **CLOSED 2026-08-03 (policy documented)**
- GUI `llama_server_path` was `…/llama.cpp/build/bin/llama-server` (build **b8559**), which crashes on Mistral-Small-3.2 tool calls (`Failed to parse input at pos N: </s>`), fixed upstream in llama.cpp **b10154**.
- **Mitigation applied 2026-07-27:** GUI `llama_server_path` repointed to `…/llama.cpp-b10154/build/bin/llama-server`.
- **Consolidated 2026-07-28 (verified):** the canonical `…/llama.cpp/build/bin/llama-server` was itself rebuilt to **b10154** (`--version` → `10154 (0e4a03622)`, built 2026-07-27 23:37); the temporary `llama.cpp-b10154/` dir is gone and both configs point at the canonical path. The crash-binary condition is cleared for now.
- **Resolved 2026-08-03:** the canonical build/version *policy* is now documented in [`docs/LLAMA-CPP-VERSION-POLICY.md`](docs/LLAMA-CPP-VERSION-POLICY.md): version floor **b10154** (never regress below), verify-before-adopt (version check + tools-mode smoke + logged commit) on any rebuild, rebuild discipline (record old→new commit; no silent in-place rebuild), and per-model pinning via I3 for exceptions. The operator may adjust the specifics, but the anti-silent-regression process is now written down rather than tribal knowledge.

### I5 — Duplicate `--ctx-size` in launch argv  (severity: low) — **CLOSED 2026-07-28 (v2026.07.28.2)**
- mistral entry yields `--ctx-size 32768 … --ctx-size 65536` (mode default from `build_argv` + per-model `args: [--ctx-size, '65536']`). Last wins (65536), so harmless, but sloppy and confusing in logs.
- **Fixed 2026-07-28:** `build_argv` collects the `--` flags present in `spec.args` and skips the matching default (generalized to all base/mode-default flags, not just `--ctx-size`), so each flag appears exactly once with the model's value.

### I6 — Mode preset ≠ binary; mode switch can silently revert the binary  (severity: medium) — **LARGELY CLOSED 2026-07-28 (via I3)**
- Modes (basic/tools/performance/extended in `process.py:build_argv`) only control flags (`--jinja`, `--flash-attn`, `--parallel/--batch`). Switching mode restarts the server, which re-reads `llama_server_path` — so a mode change can silently swap the binary back to the configured (possibly stale) one.
- **Impact:** on 2026-07-27, switching the mistral to "tools mode" relaunched it on the old b8559 binary, re-introducing the crash until the config was repointed.
- **Status 2026-07-28:** with per-model `llama_server_path` (I3), pin a model's binary and a mode switch can no longer swap it — the binary is part of the model's config, not the mode. Also fixed a related latent bug: `monitor.py` / `model_manager.py` built `ModelSpec` without `mode`/`ctx_size`/`n_gpu_layers`, so an **auto-restart relaunched the model in basic mode with default context** regardless of config; all start paths now go through the canonical `config.spec_from_dict`. Residual (open, low): mode presets still bundle flags; a fully orthogonal "flags vs binary vs slots" config model is deferred.

### I7 — Kill/restart lifecycle reparents to launchd; TERM not always honored  (severity: low) — **CLOSED 2026-08-03 (verified live; no code change needed)**
- Server started via a generated wrapper script; child `llama-server` reparents to launchd (pid 1) when the script exits, and was reported to survive a SIGTERM (needing SIGKILL).
- **Impact:** headless stop/restart could be unreliable; manager must track the real llama-server pid and stop it directly.
- **Resolution 2026-08-03 (verified live, supervised):** the concern does not reproduce — the machinery to address it already exists and works. `start_process` returns the **real llama-server pid** (via `pgrep -P` on the wrapper), `stop_process` escalates **SIGTERM→SIGKILL** after a timeout, and `cmd_stop` also kills children first and has a kill-by-port fallback. Live verification on both a GGUF (`gemma-3-270m`) and an MLX (`gemma-270m-compliance-mlx`) model: `start`→`stop`→`restart`→`stop` left the port **freed every time with no reparented orphan** (checked by both `lsof` on the port and `pgrep` on the model file), and restart produced a fresh pid. Combined with the I10 fix (`start` returns promptly) and I11 fix (restart waits for / force-frees the port), headless stop/restart is now reliable. No code change was required for I7 itself; the earlier "models die ~30s after start" fragility relates to the wrapper/detach path, which the I12 (deterministic wrapper + self-delete) and I10 (DEVNULL stdio) fixes have since stabilized.

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
- **Live-verified 2026-08-03:** installed a real launchd agent for `smollm3` (`launchd install`). The rendered plist `ProgramArguments` **and** the live launchd-spawned process argv were **byte-identical** to the direct `start` argv (`llama-server -m … --n-gpu-layers 999 --ctx-size 32768 --parallel 1 --host 127.0.0.1 --port 8082`). Agent cleanly uninstalled (`launchd uninstall` → bootout + plist removed, process gone, port freed). The remaining supervised launchd check for I9 is now done; the reparent/TERM concerns in I7 are separate.

## Live lifecycle test results (2026-07-29, corrected 2026-08-01)
Ran start → stop → restart → stop, one model at a time, via the **live pipx CLI** (`~/.local/bin/llamacpp-manager`), each model on its own registered port, capacity-reserved per model.
- **GGUF (`llama-server`): gemma-3-270m, qwen3-0.6b, mistral-05b-compliance — all PASS.** start/stop/restart reliable; restart produced a fresh pid each time; stops clean (no SIGKILL escalation needed). Gives **live** confidence for the direct start/stop/restart path — partially closes I7's "needs live testing" gap for GGUF. Launchd install/reload + reparent edge still pending (see I7/I9).
- **MLX (`mlx_lm.server`): gemma-270m-compliance-mlx, mistral-05b-compliance-mlx — start/stop PASS; restart FLAKY (see I11).**
- **Methodology note:** an earlier run used the repo dev `.venv` (missing `psutil`/`mlx_lm`) and wrongly reported MLX as broken. MLX works via the pipx CLI, which launches MLX through the configured `mlx_python_path` = `~/mlx_env` (mlx_lm 0.31.3). Lesson: test against the shipped (pipx) environment, not the dev venv.

### I10 — `start`/`restart` CLI does not return (hangs) after spawning  (severity: medium) — **CLOSED 2026-08-03 (v2026.08.03.3)**
- `llamacpp-manager start <model>` spawned the server (correctly detached, `start_new_session=True`) and printed `started <name> pid=… port=…`, but the CLI **hung instead of exiting** for output-capturing callers. Root cause (refined): the timestamp-logging wrapper `Popen` did not redirect its stdio, so the detached child **inherited and held open the CLI's stdout/stderr pipe** — a caller capturing the CLI's output blocks for EOF until the long-lived server exits. (The CLI process itself returns; the *reader* hangs.) Verified live — the test harness force-killed each `start`/`restart` after 90s while the server stayed healthy.
- **Fixed 2026-08-03:** the wrapper `Popen` now passes `stdin=DEVNULL, stdout=DEVNULL, stderr=DEVNULL` so the detached child holds no copy of the CLI's pipe. The wrapper writes its own log to the logfile internally, so nothing is lost. Verified live: `start` with captured output returned in ~0.2s (was blocking to the 90s timeout); model came up healthy. Test asserts the DEVNULL redirection (`test_start_process_wrapper_uses_deterministic_path_and_self_deletes`). The spawn-detach + `pgrep` child-tracking logic was left untouched.

### I11 — MLX `restart` race: port not released before re-start  (severity: medium) — **CLOSED 2026-08-03 (v2026.08.03.2)**
- `cmd_restart` = `cmd_stop` + `cmd_start` with **no wait for port release between them**. `mlx_lm.server` frees its port more slowly than `llama-server`, so a back-to-back restart intermittently hit `cmd_start`'s port-in-use pre-check → `rc=2`, and the model did not come up. Reproduced live: both MLX models failed restart in the automated back-to-back run; a slower manual restart-from-stopped succeeded.
- **Cosmetic sub-bug:** `cmd_restart`'s internal `cmd_stop` returned `1` ("not running") when the model was already stopped, so `restart` could report a non-zero exit (`max(r1,r2)`) even when the model then started fine.
- **Fixed 2026-08-03:** `cmd_restart` now waits (up to 10s) for each target's port to be released after stop; if still held, it force-kills whatever holds the model's own registered port (`lsof -ti tcp:<port>` → `SIGKILL`) and re-waits (up to 6s) before the start phase. It now returns the start result (`r2`) rather than `max(r1, r2)`, so a stop that found nothing running does not inflate the exit code. Verified live: 5/5 back-to-back MLX restarts succeeded (was flaky at 2/3). Validated via live smoke; `pytest` remains green (the fix is in the `stop`+`start` orchestration, exercised end-to-end rather than by a new unit test).

### I12 — timestamp-logger `/tmp` wrapper scripts leak  (severity: low) — **CLOSED 2026-08-03 (v2026.08.03.1)**
- `process.py:start_process` wrote a per-start bash wrapper via `NamedTemporaryFile(delete=False, dir='/tmp')` and attempted cleanup in a **daemon thread**, which dies when the short-lived CLI exits — the exact failure mode the surrounding code comment warns about. Result: `/tmp/tmp*.sh` files accumulated indefinitely (8 observed from a single session).
- **Fixed 2026-08-03:** the wrapper is now written to a deterministic per-model path `<log_dir>/wrappers/<model>.sh` (created via `mkdir(parents=True, exist_ok=True)`, **overwritten each start** → at most one file per model, out of `/tmp`) and **self-deletes on exit** via `trap 'rm -f "$0"' EXIT`. The non-functional daemon-thread cleanup was removed. Test: `test_process.py::test_start_process_wrapper_uses_deterministic_path_and_self_deletes`. The spawn/detach and `pgrep -P` child-tracking logic was intentionally left untouched (fragile I7 territory).
- **Residual (low):** on `SIGKILL` the `EXIT` trap does not fire, so one stale wrapper can remain until the next start overwrites it (still bounded to one per model). An optional sweep in the `cleanup` command (remove wrappers whose owning process is dead) would close even that edge — deferred.

## Mode reference (from `src/llamacpp_manager/process.py:build_argv`)
| Mode | Extra flags (beyond `--ctx-size <n>` default 32768, `--n-gpu-layers 999`) |
|------|---------------------------------------------------------------------------|
| basic | *(none)* — no `--jinja`, so **no tool calling** |
| tools | `--jinja` |
| performance | `--jinja --parallel 4 --batch-size 512 --ubatch-size 512` |
| extended | `--jinja --flash-attn on` |
