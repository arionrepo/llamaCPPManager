# Implementation Plan — KNOWN-ISSUES I11, I10, I7, I4

**File:** docs/plans/plan-known-issues-i11-i10-i7-i4.md
**Description:** Autonomous-execution plan to resolve four open KNOWN-ISSUES in dependency order.
**Author:** Libor Ballaty <libor@arionetworks.com> (operator), Claude (Opus 4.8, drafter)
**Created:** 2026-08-03
**Last Updated:** 2026-08-03

## Goal
Resolve I11 (MLX restart race), I10 (start/restart CLI hang), I7 (kill/restart reparenting/TERM),
and I4 (llama.cpp build/version policy) with verification gates and incremental commits.

## Constraints & safety
- **Shared device:** another agent's `mistral-small-24b` runs on 8089 (~44 GB). NEVER touch it. Stay within `absmax=2`.
- **Ports:** smoke tests use registered models on their OWN registered ports (≠8089); capacity-reserved; cleaned up.
- **Live testing uses the pipx CLI** (`~/.local/bin/llamacpp-manager`); `pipx reinstall` after each src edit.
- **Fragile code:** I10/I7 touch `start_process` detach machinery ("models die ~30s after start" history). High-risk; validate live before commit.
- **Verification gate (every code step):** `.venv/bin/pytest` green + a live smoke test.

## Steps

### step-1  (I11 — MLX restart port-release race)  [fatal: false]
- **command:** In `cli.py:cmd_restart` (and/or the MLX stop path), wait for the port to be released after stop before the start phase; treat "already stopped" as success so a clean restart does not return non-zero.
- **validation:** pytest green; live: start `gemma-270m-compliance-mlx` (8097), restart back-to-back 3×, each comes up (port bound, rc==0); stop; port free.
- **depends_on:** []

### step-2  (I10 — start/restart CLI hangs after spawning)  [fatal: false]
- **command:** In `process.py:start_process`, detach the timestamp-logging wrapper so the CLI returns promptly (redirect wrapper stdin/stdout/stderr to DEVNULL / logfile at `Popen` so the parent holds no pipe). Preserve detached-survival + real-pid tracking.
- **validation:** pytest green; live: `llamacpp-manager start <gguf>` returns in <15s (not hanging), model up; stop clean.
- **depends_on:** [step-1]

### step-3  (I7 — kill/restart reparenting/TERM)  [fatal: false]
- **command:** Verify (and minimally harden if needed) that stop targets the real server pid and no orphan survives, given step-2. Likely verification + doc-close; code only if an orphan/TERM gap is observed.
- **validation:** live: start→stop (TERM honored, pid gone, port free, no orphan llama-server)→restart (new pid)→stop, on 1 GGUF + 1 MLX.
- **depends_on:** [step-2]

### step-4  (I4 — llama.cpp build/version policy)  [fatal: false]  [doc-only]
- **command:** Document the canonical llama.cpp build/version policy and how to prevent silent regression (supersedes/complements per-model binary override I3). Update KNOWN-ISSUES I4.
- **validation:** policy doc exists; KNOWN-ISSUES I4 updated to reflect the decision.
- **depends_on:** []

## goal_validation
- `.venv/bin/pytest` fully green.
- KNOWN-ISSUES I11/I10/I7/I4 statuses updated to match outcomes.
- Live smoke clean on ≥1 GGUF + ≥1 MLX (start/stop/restart), no orphans, all test models stopped, capacity released.
- All step commits present; VERSION bumped once; pushed to origin.
