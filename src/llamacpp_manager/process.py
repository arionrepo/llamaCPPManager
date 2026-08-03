import os
import signal
from pathlib import Path
from subprocess import Popen
import time
from typing import List, Optional

from .config import ModelSpec
from .logs import rotate_file, open_log_append, open_timestamped_log


def build_argv(llama_server_path: str, spec: ModelSpec) -> List[str]:
    # Discover actual .gguf file if model_path is a directory
    model_path = spec.model_path
    expanded_path = Path(model_path).expanduser()

    if expanded_path.is_dir():
        # Auto-discover .gguf file in directory
        gguf_files = list(expanded_path.glob("*.gguf"))
        if not gguf_files:
            raise RuntimeError(f"No .gguf files found in directory: {expanded_path}")
        # Use the largest .gguf file (main model)
        discovered_file = max(gguf_files, key=lambda p: p.stat().st_size)
        model_path = str(discovered_file)
        print(f"Auto-discovered model file: {discovered_file.name}")
    elif not expanded_path.exists():
        raise RuntimeError(f"Model file not found: {expanded_path}")

    # Per-model binary override (KNOWN-ISSUES I3): a model may pin its own
    # llama-server build (e.g. a newer/fixed commit) without changing the global
    # default. Falls back to the global path when unset.
    server_path = getattr(spec, "llama_server_path", None) or llama_server_path

    argv: List[str] = [server_path, "-m", model_path]

    # Per-model args take precedence over our base/mode defaults. Collect the
    # flag tokens the user set explicitly so we never emit a duplicate default
    # for the same flag (llama-server tolerates duplicates via last-wins, but it
    # is confusing in logs — see KNOWN-ISSUES I5). Anything in spec.args wins.
    user_args = list(spec.args or [])
    user_flags = {a for a in user_args if isinstance(a, str) and a.startswith("--")}

    def add_default(flag: str, *values: object) -> None:
        """Append a default flag (+optional value) unless the model overrode it."""
        if flag in user_flags:
            return
        argv.append(flag)
        argv.extend(str(v) for v in values)

    # GPU offload — default to "all layers to Metal" on Apple Silicon. The
    # bash launcher restart-llm-interactive.sh always passed `--n-gpu-layers 999`
    # for the same reason. Per-model override available via spec.n_gpu_layers.
    n_gpu_layers = spec.n_gpu_layers if spec.n_gpu_layers is not None else 999
    add_default("--n-gpu-layers", n_gpu_layers)

    # Context size — default 32768 (matches the bash launcher's general-case
    # default). Per-model override via spec.ctx_size (e.g. phi3 needs 8192
    # because Phi-3-mini-4k natively supports 4k and only RoPE-extends to 8k).
    ctx_size = spec.ctx_size if spec.ctx_size is not None else 32768
    add_default("--ctx-size", ctx_size)

    # Slot count + mode flags.
    #
    # llama-server (b10154+) defaults to 4 slots and divides --ctx-size across
    # them, so a single request silently gets only ctx/4 (KNOWN-ISSUES I8). This
    # is a single-user local manager, so every mode except `performance` pins
    # `--parallel 1` to give one request the full context window. `performance`
    # intentionally runs 4 slots for throughput. A per-model `--parallel` in
    # spec.args overrides either default.
    mode = getattr(spec, 'mode', 'basic')
    if mode == "performance":
        add_default("--parallel", 4)
        add_default("--jinja")
        add_default("--batch-size", 512)
        add_default("--ubatch-size", 512)
    else:
        add_default("--parallel", 1)
        if mode == "tools":
            add_default("--jinja")
        elif mode == "extended":
            add_default("--jinja")
            add_default("--flash-attn", "on")
        # basic mode: no --jinja (no tool calling), just the single slot.

    # Explicit per-model args last — defaults for these flags were skipped above,
    # so this both applies the override and guarantees no duplicate flag.
    argv.extend(user_args)

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

    from .lifecycle_log import log_event

    env = os.environ.copy()
    if spec.env:
        env.update(spec.env)
    if extra_env:
        env.update(extra_env)
    argv = build_argv(llama_server_path, spec)

    # Fail loud on a missing binary rather than letting Popen raise a bare
    # FileNotFoundError with no context (KNOWN-ISSUES I2/I3). argv[0] is the
    # resolved server path (per-model override or global). Only enforce for
    # absolute paths — a bare name is resolved via PATH by the OS.
    server_path = argv[0]
    if os.path.sep in server_path and not Path(server_path).expanduser().exists():
        from .lifecycle_log import log_event as _log_event
        _log_event("process.start.binary_missing", model=spec.name, server_path=server_path)
        raise RuntimeError(
            f"llama-server binary not found for model '{spec.name}': {server_path}. "
            f"Set a valid global 'llama_server_path' or a per-model override."
        )

    log_event("process.start.begin", model=spec.name, caller="process.start_process",
              argv=argv, port=spec.port, deployment="native",
              logging_enabled=enabled, timestamps=timestamps)

    # Configure logging based on settings
    if enabled:
        log_path = log_dir / f"{spec.name}.log"
        rotate_file(log_path, max_bytes=max_bytes, backups=backups)

        if timestamps:
            # For timestamp logging, we need a persistent helper process
            # since daemon threads die when the CLI exits.
            # Use a wrapper script approach instead.
            import shlex

            # Timestamp-logger wrapper. Use a DETERMINISTIC per-model path (not a
            # random /tmp file) so wrappers cannot accumulate: each start overwrites
            # the model's single wrapper, and the wrapper self-deletes on exit via a
            # trap. The previous approach (tempfile.NamedTemporaryFile in /tmp +
            # daemon-thread unlink) leaked because the daemon thread dies when the
            # short-lived CLI process exits — see KNOWN-ISSUES I12.
            wrappers_dir = log_dir / "wrappers"
            wrappers_dir.mkdir(parents=True, exist_ok=True)
            wrapper_path = str(wrappers_dir / f"{spec.name}.sh")

            # Build the wrapper script content
            quoted_argv = ' '.join(shlex.quote(arg) for arg in argv)
            script_content = f'''#!/bin/bash
# Timestamp logger wrapper for {spec.name}
# Self-deletes on exit; overwritten on each start (KNOWN-ISSUES I12).
trap 'rm -f "$0"' EXIT
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
            with open(wrapper_path, "w") as wrapper_script:
                wrapper_script.write(script_content)

            # Make wrapper executable
            os.chmod(wrapper_path, 0o755)

            # Start the wrapper script
            # start_new_session=True detaches the child into its own process group / session
            # so it survives the parent CLI exiting (was causing models to die ~30s after start)
            proc = Popen(['/bin/bash', wrapper_path], env=env, start_new_session=True)
            wrapper_pid = proc.pid
            log_event("process.start.wrapper_spawned", model=spec.name,
                      pid=wrapper_pid, wrapper_path=wrapper_path)

            # Wrapper cleanup is handled by the wrapper's own `trap ... EXIT`
            # (self-delete on server exit) plus the deterministic path being
            # overwritten on each start. No daemon-thread unlink — that died with
            # the CLI and leaked /tmp scripts (KNOWN-ISSUES I12).

            # CRITICAL FIX: Track actual llama-server child PID, not bash wrapper
            # The wrapper is just a logging helper; we need to track the real server process
            import subprocess
            llama_server_pid = None
            # Wait up to 5 seconds for llama-server child to spawn
            for attempt in range(50):  # 50 attempts * 0.1s = 5 seconds max
                time.sleep(0.1)
                try:
                    # Find child processes of bash wrapper
                    result = subprocess.run(
                        ['pgrep', '-P', str(wrapper_pid)],
                        capture_output=True,
                        text=True,
                        timeout=1
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        # Get first child PID (should be llama-server)
                        llama_server_pid = int(result.stdout.strip().split()[0])
                        break
                except:
                    pass

            log_event("process.start.child_resolved", model=spec.name,
                      wrapper_pid=wrapper_pid, llama_server_pid=llama_server_pid,
                      returned_pid=llama_server_pid if llama_server_pid else wrapper_pid)
            return llama_server_pid if llama_server_pid else wrapper_pid
        else:
            # No timestamps - direct file logging
            stdout_log = open_log_append(log_path)
            stderr_log = stdout_log  # Share same file
            proc = Popen(argv, stdout=stdout_log, stderr=stderr_log, env=env, start_new_session=True)
            log_event("process.start.direct_spawned", model=spec.name, pid=proc.pid,
                      mode="direct_no_timestamps")
    else:
        # Logging disabled - discard output
        import subprocess
        proc = Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, start_new_session=True)
        log_event("process.start.direct_spawned", model=spec.name, pid=proc.pid,
                  mode="direct_no_logging")

    return proc.pid


def stop_process(pid: int, timeout: float = 5.0) -> None:
    from .lifecycle_log import log_event
    log_event("process.stop.sigterm", pid=pid, caller="process.stop_process", timeout=timeout)
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError as e:
        log_event("process.stop.no_such_process", pid=pid, error=str(e))
        raise
    except Exception as e:
        log_event("process.stop.error", pid=pid, error=str(e), error_type=type(e).__name__)
        raise

    # wait up to timeout for process to exit; if still alive, SIGKILL
    deadline = time.time() + max(0.1, float(timeout))
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            log_event("process.stop.exited_after_sigterm", pid=pid)
            return
        except PermissionError:
            pass
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
        log_event("process.stop.sigkill", pid=pid, reason="sigterm_timeout")
    except ProcessLookupError:
        log_event("process.stop.exited_before_sigkill", pid=pid)
