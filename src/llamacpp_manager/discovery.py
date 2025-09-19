from __future__ import annotations

import shlex
import subprocess
from typing import List, Dict, Any


def _ps_output() -> str:
    # macOS/BSD ps columns; fall back to generic if needed
    try:
        cp = subprocess.run(
            ["ps", "-ax", "-o", "pid=,args="], capture_output=True, text=True, check=True
        )
        return cp.stdout
    except Exception:
        return ""


def find_llama_processes() -> List[Dict[str, Any]]:
    """Parse process table to find llama-server processes.

    Returns a list of {pid:int, argv: List[str]}.
    """
    out = []
    text = _ps_output()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_str, rest = line.split(" ", 1)
            pid = int(pid_str)
        except ValueError:
            continue
        # quick filter
        if "llama-server" not in rest:
            continue
        try:
            argv = shlex.split(rest)
        except Exception:
            argv = rest.split()
        out.append({"pid": pid, "argv": argv})
    return out

