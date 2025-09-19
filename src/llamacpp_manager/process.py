import os
import signal
from pathlib import Path
from subprocess import Popen
from typing import List, Optional

from .config import ModelSpec
from .logs import rotate_file, open_log_append


def build_argv(llama_server_path: str, spec: ModelSpec) -> List[str]:
    argv: List[str] = [llama_server_path, "-m", spec.model_path]
    if spec.args:
        argv.extend(spec.args)
    argv.extend(["--host", spec.host, "--port", str(spec.port)])
    return argv


def start_process(llama_server_path: str, spec: ModelSpec, log_dir: Path, extra_env: Optional[dict] = None) -> int:
    log_path = log_dir / f"{spec.name}.log"
    rotate_file(log_path)
    env = os.environ.copy()
    if spec.env:
        env.update(spec.env)
    if extra_env:
        env.update(extra_env)
    argv = build_argv(llama_server_path, spec)
    f = open_log_append(log_path)
    # use the same file for stdout and stderr (append, line-buffered)
    proc = Popen(argv, stdout=f, stderr=f, env=env)
    return proc.pid


def stop_process(pid: int) -> None:
    os.kill(pid, signal.SIGTERM)

