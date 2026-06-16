# File: src/llamacpp_manager/lifecycle_log.py
# Description: Centralized lifecycle event log for models (start, stop, kill, crash)
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-06-16

"""
Structured lifecycle event logger for llamaCPPManager.

Writes JSON lines to ~/Library/Logs/llamaCPPManager/lifecycle.jsonl so we can
trace exactly what happened to any model: who started it, who stopped it, with
what PID, exit code, signal, stderr, etc.

Each event is a single JSON object on one line — easy to grep, easy to tail.

Usage:
    from .lifecycle_log import log_event
    log_event("start.begin", model="phi3", caller="cli.cmd_start", args={...})
    log_event("start.spawn.success", model="phi3", pid=12345, argv=[...])
    log_event("stop.begin", model="phi3", caller="cli.cmd_stop")
    log_event("stop.kill.sigterm", model="phi3", pid=12345)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional


_LOG_PATH = Path.home() / "Library" / "Logs" / "llamaCPPManager" / "lifecycle.jsonl"


def _ensure_dir():
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def log_event(
    event: str,
    model: Optional[str] = None,
    caller: Optional[str] = None,
    pid: Optional[int] = None,
    **fields: Any,
) -> None:
    """
    Append a structured lifecycle event.

    Args:
        event: dot-namespaced event name (e.g. "start.begin", "stop.kill.sigterm")
        model: model name (if applicable)
        caller: source location (e.g. "cli.cmd_start", "monitor._restart_model")
        pid: associated process ID
        **fields: additional context (argv, exit_code, stderr, etc.)
    """
    _ensure_dir()

    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "pid_self": os.getpid(),
        "ppid": os.getppid(),
        "event": event,
    }
    if model is not None:
        entry["model"] = model
    if caller is not None:
        entry["caller"] = caller
    if pid is not None:
        entry["pid"] = pid
    entry.update(fields)

    try:
        with open(_LOG_PATH, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
    except Exception as e:
        # Never crash on logging
        try:
            sys.stderr.write(f"[lifecycle_log] failed to write event {event}: {e}\n")
        except Exception:
            pass


def log_path() -> Path:
    return _LOG_PATH
