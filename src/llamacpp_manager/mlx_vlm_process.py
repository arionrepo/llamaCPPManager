# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/mlx_vlm_process.py
# Description: MLX-VLM process management for diffusion / vision-language Apple Silicon models
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-06-16

"""
MLX-VLM model process management.

Business Purpose:
    Manages mlx_vlm.server processes for Apple Silicon models that require the
    vision-language MLX stack — currently the only path to serve diffusion-class
    text models like Google's DiffusionGemma on macOS (since upstream llama-server
    and stock mlx_lm.server do not yet support diffusion sampling).

Architecture mirror of mlx_process.py:
    Same interface (build_*_argv + start_*_process) so the cli.cmd_start router
    can dispatch to this module without modifying existing code paths.

Safety:
    Uses start_new_session=True so the child mlx_vlm.server survives the parent
    CLI exiting (same fix that was applied to process.py / mlx_process.py).
    Emits structured lifecycle events so every step is traceable.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import List, Optional

from .config import ModelSpec
from .logs import open_log_append, open_timestamped_log
from .lifecycle_log import log_event


def build_mlx_vlm_argv(python_path: str, spec: ModelSpec) -> List[str]:
    """
    Build command arguments for `python -m mlx_vlm.server`.

    Args:
        python_path: Path to Python with mlx-vlm installed (typically a dedicated venv)
        spec: Model specification

    Returns:
        Command list for subprocess.

    Example:
        argv = build_mlx_vlm_argv("~/mlx_vlm_env/bin/python", spec)
        # ['~/mlx_vlm_env/bin/python', '-m', 'mlx_vlm.server',
        #  '--model', 'mlx-community/diffusiongemma-26B-A4B-it-4bit',
        #  '--host', '127.0.0.1', '--port', '8104']
    """
    argv = [
        python_path, "-m", "mlx_vlm.server",
        "--model", spec.model_path,
        "--host", spec.host,
        "--port", str(spec.port),
    ]
    # Extra config args (e.g., --max-tokens, --temperature) pass through verbatim
    if spec.args:
        argv.extend(spec.args)
    return argv


def _verify_mlx_vlm_available(python_path: str, model_name: str) -> tuple[bool, str]:
    """
    Pre-flight check: verify that the Python interpreter has mlx_vlm.server
    available. Runs `python -c "import mlx_vlm.server"` and reports the result.

    Returns (ok, message). On failure, message is suitable for showing to the user.
    """
    if not Path(python_path).expanduser().exists():
        return False, (
            f"mlx_vlm_python_path does not exist: {python_path}. "
            f"Run: llamacpp-manager bootstrap mlx-vlm"
        )
    try:
        result = subprocess.run(
            [python_path, "-c", "import mlx_vlm.server"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "ok"
        stderr_excerpt = (result.stderr or "").strip().splitlines()[-1:] if result.stderr else []
        return False, (
            f"mlx-vlm not importable from {python_path}: "
            f"{(stderr_excerpt[0] if stderr_excerpt else 'unknown error')}. "
            f"Run: llamacpp-manager bootstrap mlx-vlm"
        )
    except subprocess.TimeoutExpired:
        return False, f"Timeout verifying mlx-vlm at {python_path}"
    except Exception as e:
        return False, f"Pre-flight check failed: {type(e).__name__}: {e}"


def start_mlx_vlm_process(
    python_path: str,
    spec: ModelSpec,
    log_dir: Path,
    extra_env: Optional[dict] = None,
    logging_config: Optional[dict] = None,
) -> int:
    """
    Start `python -m mlx_vlm.server` as a detached child process.

    Args:
        python_path: Path to Python with mlx-vlm installed
        spec: Model specification (deployment_type should be "mlx-vlm")
        log_dir: Directory for log files
        extra_env: Additional environment variables
        logging_config: Optional logging settings (parallel to other start_* funcs)

    Returns:
        PID of the spawned process

    Raises:
        RuntimeError if mlx-vlm is not available (with clear bootstrap instructions)
    """
    # Pre-flight check
    ok, msg = _verify_mlx_vlm_available(python_path, spec.name)
    if not ok:
        log_event(
            "process.start.preflight_failed",
            model=spec.name,
            caller="mlx_vlm_process.start_mlx_vlm_process",
            reason=msg,
        )
        raise RuntimeError(msg)

    env = os.environ.copy()
    if spec.env:
        env.update(spec.env)
    if extra_env:
        env.update(extra_env)

    argv = build_mlx_vlm_argv(python_path, spec)
    log_event(
        "process.start.begin",
        model=spec.name,
        caller="mlx_vlm_process.start_mlx_vlm_process",
        argv=argv,
        port=spec.port,
        deployment="mlx-vlm",
    )

    # Log file path mirrors what other backends use
    log_path = log_dir / f"{spec.name}.log"
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # Open log file for stdout/stderr capture
    try:
        log_file = open_log_append(log_path)
        stdout_file = log_file
        stderr_file = log_file
    except Exception:
        stdout_file = subprocess.DEVNULL
        stderr_file = subprocess.DEVNULL

    # Spawn with start_new_session=True so the child survives parent CLI exiting
    # (same critical detachment fix used in process.py and mlx_process.py).
    try:
        proc = subprocess.Popen(
            argv,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
        )
    except FileNotFoundError as e:
        log_event(
            "process.start.spawn_failed",
            model=spec.name,
            caller="mlx_vlm_process.start_mlx_vlm_process",
            error_type="FileNotFoundError",
            error=str(e),
        )
        raise RuntimeError(
            f"MLX-VLM Python not found at {python_path}. "
            f"Run: llamacpp-manager bootstrap mlx-vlm"
        ) from e
    except Exception as e:
        log_event(
            "process.start.spawn_failed",
            model=spec.name,
            caller="mlx_vlm_process.start_mlx_vlm_process",
            error_type=type(e).__name__,
            error=str(e),
        )
        raise

    log_event(
        "process.start.direct_spawned",
        model=spec.name,
        pid=proc.pid,
        mode="mlx_vlm.server",
    )
    return proc.pid
