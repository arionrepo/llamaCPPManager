# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/bootstrap.py
# Description: Bootstrap helpers for optional backends (mlx-vlm).
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-06-16

"""
Bootstrap commands for optional model runtimes.

Currently supports:
- mlx-vlm: creates a dedicated venv at ~/mlx_vlm_env and installs mlx-vlm,
  then writes mlx_vlm_python_path into config so cmd_start can find it.

Safety:
- Pure additive. No modifications to other backends.
- Idempotent. Re-running is safe; venv reuse + pip --upgrade handles state.
- All failures return a (False, message) tuple so callers can report cleanly.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from .lifecycle_log import log_event


DEFAULT_MLX_VLM_VENV = Path("~/mlx_vlm_env").expanduser()


def _is_apple_silicon() -> bool:
    """Return True only on Apple Silicon Macs (M1/M2/M3/M4...)."""
    return platform.system() == "Darwin" and platform.machine() in ("arm64", "aarch64")


def bootstrap_mlx_vlm(
    venv_path: Path = DEFAULT_MLX_VLM_VENV,
    pip_spec: str = "mlx-vlm",
    upgrade: bool = True,
) -> Tuple[bool, str, dict]:
    """
    Create (or reuse) a Python venv and install mlx-vlm into it.

    Args:
        venv_path: Where to create the venv (default ~/mlx_vlm_env)
        pip_spec: PEP-508 spec for pip install (default 'mlx-vlm'; can pin)
        upgrade: Pass --upgrade to pip

    Returns:
        (success, message, details) where details has 'venv_path', 'python_path',
        and 'mlx_vlm_version' when successful.
    """
    details: dict = {"venv_path": str(venv_path)}
    log_event("bootstrap.mlx_vlm.begin", caller="bootstrap.bootstrap_mlx_vlm",
              venv_path=str(venv_path), pip_spec=pip_spec)

    if not _is_apple_silicon():
        msg = ("mlx-vlm requires Apple Silicon. "
               f"Detected: {platform.system()} / {platform.machine()}")
        log_event("bootstrap.mlx_vlm.failure", reason="not_apple_silicon",
                  platform=platform.system(), arch=platform.machine())
        return False, msg, details

    venv_path = Path(venv_path).expanduser()
    python_bin = venv_path / "bin" / "python"
    details["python_path"] = str(python_bin)

    # 1. Create venv if missing
    if not python_bin.exists():
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(venv_path)],
                check=True, capture_output=True, text=True,
            )
        except subprocess.CalledProcessError as e:
            msg = f"Failed to create venv at {venv_path}: {e.stderr or e}"
            log_event("bootstrap.mlx_vlm.failure", reason="venv_create_failed",
                      stderr=(e.stderr or str(e))[:500])
            return False, msg, details

    # 2. Upgrade pip
    try:
        subprocess.run(
            [str(python_bin), "-m", "pip", "install", "--upgrade", "pip"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        log_event("bootstrap.mlx_vlm.warning", reason="pip_upgrade_failed",
                  stderr=(e.stderr or str(e))[:300])
        # non-fatal; continue

    # 3. Install mlx-vlm
    pip_cmd = [str(python_bin), "-m", "pip", "install"]
    if upgrade:
        pip_cmd.append("--upgrade")
    pip_cmd.append(pip_spec)
    try:
        result = subprocess.run(pip_cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        msg = f"pip install {pip_spec} failed: {(e.stderr or str(e))[:500]}"
        log_event("bootstrap.mlx_vlm.failure", reason="pip_install_failed",
                  stderr=(e.stderr or str(e))[:500])
        return False, msg, details

    # 4. Verify import
    try:
        result = subprocess.run(
            [str(python_bin), "-c",
             "import mlx_vlm, mlx_vlm.server; "
             "import importlib.metadata as m; "
             "print(m.version('mlx-vlm'))"],
            check=True, capture_output=True, text=True, timeout=15,
        )
        version = (result.stdout or "").strip()
        details["mlx_vlm_version"] = version
    except subprocess.CalledProcessError as e:
        msg = f"mlx-vlm installed but import failed: {(e.stderr or str(e))[:500]}"
        log_event("bootstrap.mlx_vlm.failure", reason="import_failed",
                  stderr=(e.stderr or str(e))[:500])
        return False, msg, details

    log_event("bootstrap.mlx_vlm.success", venv_path=str(venv_path),
              python_path=str(python_bin), mlx_vlm_version=version)
    return True, f"mlx-vlm {version} installed in {venv_path}", details
