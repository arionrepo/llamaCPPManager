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

    def fake_popen(args, stdout=None, stderr=None, env=None):
        recorded["args"] = args
        recorded["stdout"] = stdout
        recorded["stderr"] = stderr
        recorded["env"] = env
        return DummyPopen(args, stdout=stdout, stderr=stderr, env=env)

    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setattr(proc, "Popen", fake_popen)

    spec = ModelSpec(name="m1", model_path=str(tmp_path / "m.gguf"), port=8081, host="127.0.0.1", args=["-c", "8192"]) 
    # create a dummy model file to satisfy validation elsewhere if added later
    Path(spec.model_path).write_text("x")

    pid = proc.start_process("/opt/homebrew/bin/llama-server", spec, Path(tmp_path / "logs"))
    assert pid == 12345
    argv = recorded["args"]
    # Contains binary, -m, model path, --host, --port, and extra args order preserved
    assert argv[0].endswith("llama-server")
    assert "-m" in argv and spec.model_path in argv
    assert "--host" in argv and "127.0.0.1" in argv
    assert "--port" in argv and "8081" in argv
    # Log file opened
    assert (tmp_path / "logs" / "m1.log").exists()


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
