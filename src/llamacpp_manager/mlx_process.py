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

    # Start process
    proc = subprocess.Popen(
        argv,
        env=env,
        stdout=stdout_file,
        stderr=stderr_file,
        start_new_session=True
    )

    return proc.pid
