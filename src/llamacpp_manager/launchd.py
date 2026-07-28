from __future__ import annotations

import os
import plistlib
import getpass
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

from .config import ModelSpec


def agent_label(name: str) -> str:
    return f"ai.llamacpp.{name}"


def agents_dir() -> Path:
    return Path.home() / "Library" / "LaunchAgents"


def plist_path(name: str) -> Path:
    return agents_dir() / f"{agent_label(name)}.plist"


def build_program_arguments(llama_server_path: str, spec: ModelSpec) -> List[str]:
    # Per-model binary override (KNOWN-ISSUES I3), consistent with process.build_argv.
    # NOTE: unlike process.build_argv this does NOT apply mode/ctx/parallel defaults
    # — the launchd path has a known argv divergence tracked as I9.
    server_path = getattr(spec, "llama_server_path", None) or llama_server_path
    argv: List[str] = [server_path, "-m", spec.model_path]
    if spec.args:
        argv.extend(spec.args)
    argv.extend(["--host", spec.host, "--port", str(spec.port)])
    return argv


def render_plist(llama_server_path: str, spec: ModelSpec, *, log_dir: Path) -> Dict[str, Any]:
    out_log = str((log_dir / f"{spec.name}.out.log").expanduser())
    err_log = str((log_dir / f"{spec.name}.err.log").expanduser())
    env = dict(spec.env or {})
    return {
        "Label": agent_label(spec.name),
        "ProgramArguments": build_program_arguments(llama_server_path, spec),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": out_log,
        "StandardErrorPath": err_log,
        "EnvironmentVariables": env,
        # Ensure it runs in the user's context
        "ProcessType": "Interactive",
    }


def write_plist(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        plistlib.dump(data, f)


def launchctl_bootstrap(plist: Path) -> subprocess.CompletedProcess:
    uid = os.getuid()
    return subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)], capture_output=True, text=True)


def launchctl_kickstart(name: str) -> subprocess.CompletedProcess:
    uid = os.getuid()
    return subprocess.run(["launchctl", "kickstart", f"gui/{uid}/{agent_label(name)}"], capture_output=True, text=True)


def launchctl_bootout(name: str) -> subprocess.CompletedProcess:
    uid = os.getuid()
    return subprocess.run(["launchctl", "bootout", f"gui/{uid}/{agent_label(name)}"], capture_output=True, text=True)

