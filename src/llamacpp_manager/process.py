import os
import signal
from pathlib import Path
from subprocess import Popen
import time
from typing import List, Optional

from .config import ModelSpec
from .logs import rotate_file, open_log_append, open_timestamped_log


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

    # Open timestamped logs for stdout and stderr
    # Note: We can't use 'with' statement because we need the process to continue after return
    stdout_log = open_timestamped_log(log_path, "stdout")
    stderr_log = open_timestamped_log(log_path, "stderr")

    proc = Popen(argv, stdout=stdout_log, stderr=stderr_log, env=env)
    return proc.pid


def stop_process(pid: int, timeout: float = 5.0) -> None:
    os.kill(pid, signal.SIGTERM)
    # wait up to timeout for process to exit; if still alive, SIGKILL
    deadline = time.time() + max(0.1, float(timeout))
    while time.time() < deadline:
        try:
            # signal 0 checks existence
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            # assume still alive
            pass
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
