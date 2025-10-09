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


def start_process(
    llama_server_path: str,
    spec: ModelSpec,
    log_dir: Path,
    extra_env: Optional[dict] = None,
    logging_config: Optional[dict] = None
) -> int:
    """
    Start llama-server process with optional logging.

    Args:
        llama_server_path: Path to llama-server executable
        spec: Model specification
        log_dir: Directory for log files
        extra_env: Additional environment variables
        logging_config: Logging configuration (enabled, max_bytes, backups, timestamps)

    Returns:
        Process ID of started process
    """
    # Get logging settings (model-level overrides global)
    log_config = logging_config or {}
    model_log_config = spec.logging or {}

    # Determine if logging is enabled
    enabled = model_log_config.get("enabled", log_config.get("enabled", True))
    timestamps = model_log_config.get("timestamps", log_config.get("timestamps", True))
    max_bytes = model_log_config.get("max_bytes", log_config.get("max_bytes", 10 * 1024 * 1024))
    backups = model_log_config.get("backups", log_config.get("backups", 5))

    env = os.environ.copy()
    if spec.env:
        env.update(spec.env)
    if extra_env:
        env.update(extra_env)
    argv = build_argv(llama_server_path, spec)

    # Configure logging based on settings
    if enabled:
        log_path = log_dir / f"{spec.name}.log"
        rotate_file(log_path, max_bytes=max_bytes, backups=backups)

        if timestamps:
            # For timestamp logging, we need a persistent helper process
            # since daemon threads die when the CLI exits.
            # Use a wrapper script approach instead.
            import tempfile
            import shlex

            # Create a wrapper script that adds timestamps
            wrapper_script = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False, dir='/tmp')
            wrapper_path = wrapper_script.name

            # Build the wrapper script content
            quoted_argv = ' '.join(shlex.quote(arg) for arg in argv)
            script_content = f'''#!/bin/bash
# Timestamp logger wrapper for {spec.name}
# Intelligently tag lines as INFO or ERROR based on content

exec {quoted_argv} 2>&1 | while IFS= read -r line; do
    # Detect error patterns (case-insensitive)
    if echo "$line" | grep -iE "(error|fail|fatal|exception|crash|abort)" > /dev/null; then
        printf "[%s] [ERROR] %s\\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$line"
    else
        printf "[%s] [INFO] %s\\n" "$(date '+%Y-%m-%d %H:%M:%S')" "$line"
    fi
done >> {shlex.quote(str(log_path))}
'''
            wrapper_script.write(script_content)
            wrapper_script.close()

            # Make wrapper executable
            os.chmod(wrapper_path, 0o755)

            # Start the wrapper script
            proc = Popen(['/bin/bash', wrapper_path], env=env)

            # Clean up wrapper script after a delay (it will keep running)
            import threading
            def cleanup_wrapper():
                import time
                time.sleep(5)
                try:
                    os.unlink(wrapper_path)
                except:
                    pass
            threading.Thread(target=cleanup_wrapper, daemon=True).start()
        else:
            # No timestamps - direct file logging
            stdout_log = open_log_append(log_path)
            stderr_log = stdout_log  # Share same file
            proc = Popen(argv, stdout=stdout_log, stderr=stderr_log, env=env)
    else:
        # Logging disabled - discard output
        import subprocess
        proc = Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)

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
