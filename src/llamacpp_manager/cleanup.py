# File: src/llamacpp_manager/cleanup.py
# Description: Zombie / stale subprocess detection and cleanup for the llamaCPPManager
#              CLI and GUI. Targets two failure modes seen in the wild:
#                1. `llamacpp-manager models download <name>` processes that hung and
#                   never exited (sometimes multiple copies of the same model running
#                   for days).
#                2. Duplicate model-server processes (mlx_lm.server / mlx_vlm.server /
#                   llama-server) for the same model — left behind when a previous
#                   start did not properly stop the prior instance.
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-06-22

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional


@dataclass
class ProcMatch:
    pid: int
    age_seconds: int
    cmdline: str
    reason: str  # human-readable why we matched this process

    def to_dict(self) -> dict:
        return {
            "pid": self.pid,
            "age_seconds": self.age_seconds,
            "cmdline": self.cmdline,
            "reason": self.reason,
        }


# ---- process inventory ----------------------------------------------------

def _running_processes() -> List[tuple]:
    """
    Return [(pid, etime_seconds, cmdline), ...] for every process visible to the
    current user. Uses /bin/ps because (a) it's always present on macOS and
    (b) we don't want to take a hard dependency on psutil for cleanup (the
    pipx venv has it, but the dev .venv may not).

    `etime` is elapsed-time-since-start in `[[DD-]HH:]MM:SS` format.
    """
    try:
        out = subprocess.check_output(
            ["/bin/ps", "-eo", "pid=,etime=,command="],
            text=True,
            timeout=5.0,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    result: List[tuple] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        # Split into pid, etime, command-with-spaces
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        age = _parse_etime(parts[1])
        cmd = parts[2]
        result.append((pid, age, cmd))
    return result


def _parse_etime(s: str) -> int:
    """
    Parse ps elapsed-time `[[DD-]HH:]MM:SS` into seconds. Returns 0 on parse
    failure (which conservatively means "treat as just-started, don't kill").
    """
    try:
        days = 0
        if "-" in s:
            d_part, s = s.split("-", 1)
            days = int(d_part)
        parts = s.split(":")
        if len(parts) == 2:
            h = 0
            m, sec = parts
        elif len(parts) == 3:
            h, m, sec = parts
        else:
            return 0
        return days * 86400 + int(h) * 3600 + int(m) * 60 + int(sec)
    except Exception:
        return 0


# ---- matchers -------------------------------------------------------------

def find_stale_downloads(
    max_age_seconds: int = 3600,
    model_name: Optional[str] = None,
) -> List[ProcMatch]:
    """
    Find `llamacpp-manager models download` processes older than max_age_seconds.

    Args:
        max_age_seconds: only return processes older than this. 3600 = 1 hour
            default. A download that's been running for an hour is almost
            certainly hung (real downloads of even multi-GB models complete in
            tens of minutes on a normal connection).
        model_name: if set, only match downloads for this specific model name.
            If None, match all.

    Returns: list of ProcMatch sorted oldest-first.
    """
    matches: List[ProcMatch] = []
    target = f"models download {model_name}" if model_name else "models download"
    for pid, age, cmd in _running_processes():
        # Match the exact pipx CLI invocation. Avoid catching `models list` /
        # `models info` etc by requiring "models download".
        if "llamacpp-manager" not in cmd:
            continue
        if target not in cmd:
            continue
        if age < max_age_seconds:
            continue
        matches.append(ProcMatch(
            pid=pid,
            age_seconds=age,
            cmdline=cmd,
            reason=f"models-download running for {_fmt_age(age)} (threshold {_fmt_age(max_age_seconds)})",
        ))
    matches.sort(key=lambda m: m.age_seconds, reverse=True)
    return matches


def find_server_processes_for_model(
    model_name: str,
    model_path: Optional[str] = None,
) -> List[ProcMatch]:
    """
    Find mlx_lm.server / mlx_vlm.server / llama-server processes that match the
    given model.

    Matching strategy:
      - For MLX/MLX-VLM: match `--model <repo-id-or-path>` argument against
        model_path (which is the HF repo ID or local dir for these deployments).
      - For llama-server: match `-m <gguf-path>` argument against model_path
        (the absolute file path).
      - As a last resort, match by model_name substring in the cmdline.

    Args:
        model_name: the configured model name (used for fallback substring match).
        model_path: the configured `model_path` field from config.yaml. May be a
            local path, a directory, or an HF repo ID.

    Returns: list of ProcMatch.
    """
    matches: List[ProcMatch] = []
    for pid, age, cmd in _running_processes():
        is_mlx = "mlx_lm.server" in cmd or "mlx_lm/server.py" in cmd
        is_mlx_vlm = "mlx_vlm.server" in cmd or "mlx_vlm/server.py" in cmd
        is_llama = "llama-server" in cmd
        if not (is_mlx or is_mlx_vlm or is_llama):
            continue

        matched_by = None
        if model_path:
            # Exact-substring match on the model path / HF repo
            if model_path in cmd:
                matched_by = "model_path"
        if not matched_by:
            # Fallback: model name appears in the cmdline (covers cases where the
            # config has a friendly name but the path doesn't echo it)
            if model_name and f" {model_name}" in cmd:
                matched_by = "model_name (fallback)"
        if not matched_by:
            continue

        kind = "mlx_lm" if is_mlx else "mlx_vlm" if is_mlx_vlm else "llama-server"
        matches.append(ProcMatch(
            pid=pid,
            age_seconds=age,
            cmdline=cmd,
            reason=f"{kind} for {model_name!r} matched by {matched_by} (age {_fmt_age(age)})",
        ))
    matches.sort(key=lambda m: m.age_seconds)  # oldest last -> we typically want newest preserved if dedup
    return matches


# ---- actions --------------------------------------------------------------

def kill_processes(matches: Iterable[ProcMatch], dry_run: bool = False) -> List[int]:
    """
    SIGTERM (then SIGKILL if still alive after 2s) the given matches.

    Returns the list of PIDs we successfully terminated (or would terminate if
    dry_run).
    """
    killed: List[int] = []
    pending: List[int] = []
    for m in matches:
        if dry_run:
            killed.append(m.pid)
            continue
        try:
            os.kill(m.pid, signal.SIGTERM)
            pending.append(m.pid)
        except ProcessLookupError:
            # Already gone — count as success
            killed.append(m.pid)
        except PermissionError:
            # Can't kill someone else's process — skip
            pass

    if pending and not dry_run:
        time.sleep(2.0)
        for pid in pending:
            try:
                os.kill(pid, 0)  # check if still alive
                # Still alive — escalate
                try:
                    os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
            except ProcessLookupError:
                pass
            killed.append(pid)

    return killed


# ---- top-level wrappers ---------------------------------------------------

def cleanup_stale_downloads(
    max_age_seconds: int = 3600,
    dry_run: bool = False,
) -> dict:
    """
    Convenience entry point for app-launch cleanup. Returns a report dict so
    the CLI command can emit JSON if asked.
    """
    matches = find_stale_downloads(max_age_seconds=max_age_seconds)
    killed = kill_processes(matches, dry_run=dry_run)
    return {
        "scanned": "stale_downloads",
        "max_age_seconds": max_age_seconds,
        "dry_run": dry_run,
        "matches": [m.to_dict() for m in matches],
        "killed_pids": killed,
    }


def cleanup_for_model(
    model_name: str,
    model_path: Optional[str] = None,
    dry_run: bool = False,
    include_stale_downloads_only: bool = False,
) -> dict:
    """
    Convenience entry point for per-model pre-start cleanup. Targets BOTH any
    stale download processes for this model name AND any orphaned server
    processes for this model. Servers are matched without an age threshold —
    if the user is about to start a fresh instance, any existing instance is
    treated as a zombie regardless of age.

    Args:
        model_name: configured model name
        model_path: configured `model_path` field; used to match server procs
        dry_run: report only
        include_stale_downloads_only: if True, only target downloads (no
            server kills). Used as a defensive option for callers that don't
            want to risk killing a healthy server.
    """
    matches: List[ProcMatch] = []
    matches.extend(find_stale_downloads(max_age_seconds=60, model_name=model_name))
    if not include_stale_downloads_only:
        matches.extend(find_server_processes_for_model(
            model_name=model_name,
            model_path=model_path,
        ))
    killed = kill_processes(matches, dry_run=dry_run)
    return {
        "scanned": "model",
        "model_name": model_name,
        "dry_run": dry_run,
        "matches": [m.to_dict() for m in matches],
        "killed_pids": killed,
    }


def _fmt_age(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    if seconds < 86400:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h{m:02d}m"
    d = seconds // 86400
    h = (seconds % 86400) // 3600
    return f"{d}d{h:02d}h"
