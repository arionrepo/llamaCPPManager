import os
import signal
from pathlib import Path

import pytest

from llamacpp_manager.config import ModelSpec


class DummyPopen:
    def __init__(self, args, stdout=None, stderr=None, env=None):
        # Record inputs for assertions
        self.args = args
        self.stdout = stdout
        self.stderr = stderr
        self.env = env or {}
        self.pid = 12345
        self._terminated = False

    def poll(self):
        return None if not self._terminated else 0

    def send_signal(self, sig):
        if sig == signal.SIGTERM:
            self._terminated = True

    def wait(self, timeout=None):
        if self._terminated:
            return 0
        raise TimeoutError("not terminated")


def test_start_process_builds_correct_args_and_logs(tmp_path, monkeypatch):
    # Late import to allow monkeypatch
    from llamacpp_manager import process as proc

    recorded = {}

    def fake_popen(args, stdout=None, stderr=None, env=None, start_new_session=False):
        recorded["args"] = args
        recorded["stdout"] = stdout
        recorded["stderr"] = stderr
        recorded["env"] = env
        recorded["start_new_session"] = start_new_session
        return DummyPopen(args, stdout=stdout, stderr=stderr, env=env)

    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setattr(proc, "Popen", fake_popen)

    spec = ModelSpec(name="m1", model_path=str(tmp_path / "m.gguf"), port=8081, host="127.0.0.1", args=["-c", "8192"])
    # create a dummy model file to satisfy validation elsewhere if added later
    Path(spec.model_path).write_text("x")
    # create a dummy binary so start_process's existence check passes
    binary = tmp_path / "llama-server"; binary.write_text("#!/bin/sh\n")

    # Test with timestamps disabled to get direct binary execution
    logging_config = {"enabled": True, "timestamps": False}
    pid = proc.start_process(str(binary), spec, Path(tmp_path / "logs"), logging_config=logging_config)
    assert pid == 12345
    argv = recorded["args"]
    # Contains binary, -m, model path, --host, --port, and extra args order preserved
    assert argv[0].endswith("llama-server")
    assert "-m" in argv and spec.model_path in argv
    assert "--host" in argv and "127.0.0.1" in argv
    assert "--port" in argv and "8081" in argv
    # Log file opened
    assert (tmp_path / "logs" / "m1.log").exists()


def test_start_process_wrapper_uses_deterministic_path_and_self_deletes(tmp_path, monkeypatch):
    """KNOWN-ISSUES I12: the timestamp-logger wrapper must be written to a
    deterministic per-model path (log_dir/wrappers/<name>.sh), NOT a random /tmp
    file, and must self-delete via a `trap ... EXIT` — no daemon-thread unlink.
    KNOWN-ISSUES I10: the wrapper Popen must redirect its stdio to DEVNULL so the
    detached child does not inherit (and hold open) the CLI's stdout/stderr,
    which otherwise makes `start`/`restart` appear to hang for output-capturing
    callers."""
    import subprocess
    from llamacpp_manager import process as proc

    recorded = {}

    def fake_popen(args, stdin=None, stdout=None, stderr=None, env=None, start_new_session=False):
        recorded["args"] = args
        recorded["stdin"] = stdin
        recorded["stdout"] = stdout
        recorded["stderr"] = stderr
        return DummyPopen(args, env=env)

    monkeypatch.setattr(proc, "Popen", fake_popen)

    log_dir = tmp_path / "logs"
    spec = ModelSpec(name="m1", model_path=str(tmp_path / "m.gguf"), port=8081, host="127.0.0.1")
    Path(spec.model_path).write_text("x")
    binary = tmp_path / "llama-server"; binary.write_text("#!/bin/sh\n")

    # timestamps=True selects the wrapper-script logging path
    logging_config = {"enabled": True, "timestamps": True}
    proc.start_process(str(binary), spec, log_dir, logging_config=logging_config)

    wrapper = log_dir / "wrappers" / "m1.sh"
    # Popen must launch the wrapper from the deterministic path, not /tmp
    assert recorded["args"][0] == "/bin/bash"
    assert recorded["args"][1] == str(wrapper)
    assert not recorded["args"][1].startswith("/tmp/")
    # Wrapper file was written there with a self-delete trap (I12)
    assert wrapper.exists()
    content = wrapper.read_text()
    assert 'trap \'rm -f "$0"\' EXIT' in content
    # Wrapper stdio detached to DEVNULL so the CLI does not hang (I10)
    assert recorded["stdin"] == subprocess.DEVNULL
    assert recorded["stdout"] == subprocess.DEVNULL
    assert recorded["stderr"] == subprocess.DEVNULL


def _count(argv, flag):
    return argv.count(flag)


def _value_after(argv, flag):
    return argv[argv.index(flag) + 1]


def test_build_argv_non_performance_modes_pin_single_slot(tmp_path):
    """I8: basic/tools/extended must pin --parallel 1 (llama-server defaults to 4
    slots, which silently quarters the context window for a single request)."""
    from llamacpp_manager.process import build_argv
    model = tmp_path / "m.gguf"; model.write_text("x")
    for mode in ("basic", "tools", "extended"):
        spec = ModelSpec(name="m", model_path=str(model), port=8081, mode=mode)
        argv = build_argv("/bin/llama-server", spec)
        assert _count(argv, "--parallel") == 1, f"{mode}: exactly one --parallel"
        assert _value_after(argv, "--parallel") == "1", f"{mode}: single slot"
    # tools/extended enable jinja; basic does not
    assert "--jinja" in build_argv("/bin/llama-server", ModelSpec(name="m", model_path=str(model), port=8081, mode="tools"))
    assert "--jinja" not in build_argv("/bin/llama-server", ModelSpec(name="m", model_path=str(model), port=8081, mode="basic"))


def test_build_argv_performance_mode_uses_four_slots(tmp_path):
    from llamacpp_manager.process import build_argv
    model = tmp_path / "m.gguf"; model.write_text("x")
    spec = ModelSpec(name="m", model_path=str(model), port=8081, mode="performance")
    argv = build_argv("/bin/llama-server", spec)
    assert _count(argv, "--parallel") == 1
    assert _value_after(argv, "--parallel") == "4"
    assert "--jinja" in argv and "--batch-size" in argv


def test_build_argv_dedups_user_overridden_flags(tmp_path):
    """I5: a per-model arg must override the default WITHOUT producing a
    duplicate flag in the launch command."""
    from llamacpp_manager.process import build_argv
    model = tmp_path / "m.gguf"; model.write_text("x")
    spec = ModelSpec(
        name="m", model_path=str(model), port=8081, mode="tools",
        args=["--ctx-size", "131072", "--parallel", "1", "--flash-attn", "on"],
    )
    argv = build_argv("/bin/llama-server", spec)
    # Each overridden flag appears exactly once, with the user's value.
    assert _count(argv, "--ctx-size") == 1 and _value_after(argv, "--ctx-size") == "131072"
    assert _count(argv, "--parallel") == 1 and _value_after(argv, "--parallel") == "1"
    assert _count(argv, "--flash-attn") == 1 and _value_after(argv, "--flash-attn") == "on"
    # Non-overridden default still present exactly once.
    assert _count(argv, "--n-gpu-layers") == 1


def test_build_argv_per_model_binary_override(tmp_path):
    """I3: a per-model llama_server_path overrides the global binary; when unset
    the global is used."""
    from llamacpp_manager.process import build_argv
    model = tmp_path / "m.gguf"; model.write_text("x")
    # override set
    spec = ModelSpec(name="m", model_path=str(model), port=8081,
                     llama_server_path="/custom/llama.cpp-b10154/llama-server")
    assert build_argv("/global/llama-server", spec)[0] == "/custom/llama.cpp-b10154/llama-server"
    # override unset -> global
    spec2 = ModelSpec(name="m", model_path=str(model), port=8081)
    assert build_argv("/global/llama-server", spec2)[0] == "/global/llama-server"


def test_start_process_missing_binary_fails_loud(tmp_path):
    """I2/I3: a non-existent absolute binary path raises a clear RuntimeError
    rather than a bare Popen FileNotFoundError."""
    from llamacpp_manager import process as proc
    model = tmp_path / "m.gguf"; model.write_text("x")
    spec = ModelSpec(name="m", model_path=str(model), port=8081)
    with pytest.raises(RuntimeError, match="binary not found"):
        proc.start_process("/nonexistent/path/llama-server", spec, tmp_path / "logs",
                            logging_config={"enabled": False})


def test_stop_process_sends_sigterm(monkeypatch):
    from llamacpp_manager import process as proc

    dummy = DummyPopen(["bin"])  # not used directly by stop, we simulate OS APIs

    # Patch os.kill to simulate successful signal
    sent_calls = []

    def fake_kill(pid, sig):
        sent_calls.append((pid, sig))

    # Simulate process disappears after first check
    state = {"alive_checks": 0}

    def fake_os_kill(pid, sig):
        if sig == 0:
            # first existence check says alive, second raises not found
            state["alive_checks"] += 1
            if state["alive_checks"] >= 2:
                raise ProcessLookupError
            return
        return fake_kill(pid, sig)

    monkeypatch.setattr(proc, "os", type("_O", (), {"kill": fake_os_kill, "getpgid": lambda x: 0}))

    # stop should call os.kill with SIGTERM
    proc.stop_process(dummy.pid)
    assert sent_calls[0] == (dummy.pid, signal.SIGTERM)
