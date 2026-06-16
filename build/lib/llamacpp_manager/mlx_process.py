# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/mlx_process.py
# Description: MLX model process management for Apple Silicon
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2026-03-27

"""
MLX model process management.

Business Purpose: Manages MLX-LM server processes for Apple Silicon optimized models.
Provides same interface as process.py but for MLX runtime instead of llama.cpp.
"""

import os
import subprocess
import signal
from pathlib import Path
from typing import Optional

from .config import ModelSpec
from .logs import open_log_append, open_timestamped_log


def build_mlx_argv(python_path: str, spec: ModelSpec) -> list:
    """
    Build command arguments for mlx_lm.server.

    Args:
        python_path: Path to Python with mlx-lm installed (can be venv)
        spec: Model specification

    Returns:
        Command list for subprocess

    Example:
        argv = build_mlx_argv("~/.venv/bin/python3", spec)
        # ['~/.venv/bin/python3', '-m', 'mlx_lm.server', '--model', 'mlx-community/gemma-3-1b-it-4bit', '--port', '8081']
    """
    # MLX uses model repo ID directly from Hugging Face
    # spec.model_path should be the HF repo ID for MLX models
    argv = [
        python_path, "-m", "mlx_lm.server",
        "--model", spec.model_path,
        "--host", spec.host,
        "--port", str(spec.port)
    ]

    # Add any extra args from config
    if spec.args:
        argv.extend(spec.args)

    return argv


def start_mlx_process(
    python_path: str,
    spec: ModelSpec,
    log_dir: Path,
    extra_env: Optional[dict] = None,
    logging_config: Optional[dict] = None
) -> int:
    """
    Start mlx_lm.server process with logging.

    Args:
        python_path: Path to Python with mlx-lm installed
        spec: Model specification (model_path should be HF repo ID)
        log_dir: Directory for log files
        extra_env: Additional environment variables
        logging_config: Logging configuration

    Returns:
        Process ID of started process

    Example:
        spec = ModelSpec(
            name="gemma-3-1b",
            model_path="mlx-community/gemma-3-1b-it-4bit",
            port=8081
        )
        pid = start_mlx_process("~/mlx_env/bin/python3", spec, Path("~/logs"))
    """
    # Get logging settings
    log_config = logging_config or {}
    model_log_config = spec.logging or {}

    enabled = model_log_config.get("enabled", log_config.get("enabled", True))

    env = os.environ.copy()

    # CRITICAL: Set MLX memory limits to prevent GPU exhaustion
    # Leave sufficient RAM for macOS WindowServer to prevent screen flashing
    # These can be overridden in spec.env if needed
    if "MLX_METAL_MEMORY_LIMIT" not in env:
        # Default: Conservative limit (adjust based on total RAM)
        # For 32GB Mac: use ~20GB max, leave 12GB for system
        # For 64GB Mac: use ~52GB max, leave 12GB for system
        import psutil
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
        safe_limit_gb = max(8, total_ram_gb - 12)  # Leave 12GB for system
        env["MLX_METAL_MEMORY_LIMIT"] = str(int(safe_limit_gb * 1024**3))

    if "MLX_METAL_CACHE_LIMIT" not in env:
        # Cache limit = 60% of memory limit (conservative to prevent exhaustion)
        memory_limit = int(env["MLX_METAL_MEMORY_LIMIT"])
        env["MLX_METAL_CACHE_LIMIT"] = str(int(memory_limit * 0.6))

    if spec.env:
        env.update(spec.env)
    if extra_env:
        env.update(extra_env)

    argv = build_mlx_argv(python_path, spec)

    # Configure logging
    if enabled:
        log_path = log_dir / f"{spec.name}.log"
        from .logs import rotate_file
        max_bytes = model_log_config.get("max_bytes", log_config.get("max_bytes", 10 * 1024 * 1024))
        backups = model_log_config.get("backups", log_config.get("backups", 5))
        rotate_file(log_path, max_bytes=max_bytes, backups=backups)

        # Simple approach - write to same log file for both stdout and stderr
        log_file = open_log_append(log_path)
        stdout_file = log_file
        stderr_file = log_file
    else:
        stdout_file = subprocess.DEVNULL
        stderr_file = subprocess.DEVNULL

    # Start process with error handling
    from .lifecycle_log import log_event
    log_event("process.start.begin", model=spec.name, caller="mlx_process.start_mlx_process",
              argv=argv, port=spec.port, deployment="mlx")
    try:
        proc = subprocess.Popen(
            argv,
            env=env,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True
        )
        log_event("process.start.direct_spawned", model=spec.name, pid=proc.pid,
                  mode="mlx_lm.server")
        return proc.pid
    except FileNotFoundError as e:
        raise RuntimeError(
            f"MLX Python not found at {python_path}. "
            f"Install mlx-lm in a venv and set mlx_python_path in config. "
            f"Example: python3 -m venv ~/mlx_env && ~/mlx_env/bin/pip install mlx-lm"
        ) from e
    except Exception as e:
        raise RuntimeError(f"Failed to start MLX process: {e}") from e
