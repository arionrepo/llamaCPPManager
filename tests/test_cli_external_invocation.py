import fcntl
import hashlib
import json
import os
import shlex
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml


def _cli_base_cmd():
    return [sys.executable, "-m", "llamacpp_manager.cli"]


def _base_env(tmp_path):
    cfgdir = tmp_path / "cfg"
    logdir = tmp_path / "logs"
    piddir = tmp_path / "pids"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path.cwd() / "src")
    env["LLAMACPP_MANAGER_CONFIG_DIR"] = str(cfgdir)
    env["LLAMACPP_MANAGER_LOG_DIR"] = str(logdir)
    env["LLAMACPP_MANAGER_PID_DIR"] = str(piddir)
    env["LLAMACPP_MANAGER_SKIP_BIN_CHECK"] = "1"
    return env


def _run_cli(args, env, *, check=False):
    return subprocess.run(
        _cli_base_cmd() + args,
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=check,
    )


def _run_cli_shell(command, env):
    return subprocess.run(
        ["/bin/zsh", "-lc", command],
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
    )


def _occupy_port():
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    sock.listen(1)
    return sock, sock.getsockname()[1]


def test_status_json_remains_parseable_when_piped(tmp_path):
    env = _base_env(tmp_path)
    model = tmp_path / "pipe.gguf"
    model.write_text("x")

    assert _run_cli(["init"], env).returncode == 0
    assert _run_cli(["config", "add", "pipe-model", str(model), "--port", "9410"], env).returncode == 0

    command = f"{shlex.join(_cli_base_cmd())} status --json | cat"
    result = _run_cli_shell(command, env)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["models"][0]["name"] == "pipe-model"
    assert result.stderr == ""


def test_status_json_preserves_utf8_model_names(tmp_path):
    env = _base_env(tmp_path)
    model = tmp_path / "utf8.gguf"
    model.write_text("x")
    model_name = "mødel-čaj"

    assert _run_cli(["init"], env).returncode == 0
    assert _run_cli(["config", "add", model_name, str(model), "--port", "9411"], env).returncode == 0

    result = _run_cli(["status", "--json"], env)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["models"][0]["name"] == model_name


def test_missing_pgrep_emits_typed_warning_but_stop_succeeds(tmp_path):
    env = _base_env(tmp_path)
    env["PATH"] = "/bin"
    model = tmp_path / "stop.gguf"
    model.write_text("x")

    assert _run_cli(["init"], env).returncode == 0
    assert _run_cli(["config", "add", "stop-model", str(model), "--port", "9412"], env).returncode == 0

    sleeper = subprocess.Popen(["/bin/sleep", "30"])
    try:
        pid_path = tmp_path / "pids" / "stop-model.pid"
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(sleeper.pid))

        result = _run_cli(["stop", "stop-model"], env)

        assert result.returncode == 0
        assert "warning: pgrep not found; skipping child-process cleanup for stop-model" in result.stderr
        assert "stopped stop-model" in result.stdout

        deadline = time.time() + 5
        while time.time() < deadline and sleeper.poll() is None:
            time.sleep(0.1)
        assert sleeper.poll() is not None
    finally:
        if sleeper.poll() is None:
            sleeper.terminate()
            sleeper.wait(timeout=5)


def test_concurrent_read_only_invocations_do_not_corrupt_config(tmp_path):
    env = _base_env(tmp_path)
    model = tmp_path / "concurrent.gguf"
    model.write_text("x")

    assert _run_cli(["init"], env).returncode == 0
    assert _run_cli(["config", "add", "concurrent-model", str(model), "--port", "9413"], env).returncode == 0

    cfg_path = tmp_path / "cfg" / "config.yaml"
    before = cfg_path.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()

    def invoke_status():
        result = _run_cli(["status", "--json"], env)
        assert result.returncode == 0
        json.loads(result.stdout)
        return result

    def invoke_list():
        result = _run_cli(["config", "list", "--json"], env)
        assert result.returncode == 0
        json.loads(result.stdout)
        return result

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(invoke_status if i % 2 == 0 else invoke_list) for i in range(12)]
        for future in futures:
            future.result()

    after = cfg_path.read_bytes()
    assert hashlib.sha256(after).hexdigest() == before_hash
    parsed = yaml.safe_load(after)
    assert parsed["models"][0]["name"] == "concurrent-model"

    with cfg_path.open() as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def test_external_cli_exit_codes_are_stable(tmp_path):
    env = _base_env(tmp_path)
    model = tmp_path / "exitcodes.gguf"
    model.write_text("x")

    ok = _run_cli(["init"], env)
    assert ok.returncode == 0

    missing_target = _run_cli(["config", "show", "missing-model"], env)
    assert missing_target.returncode == 1

    invalid_query = _run_cli(["query", "chat", "missing-model", "--message", "badrole:hello"], env)
    assert invalid_query.returncode == 2

    assert _run_cli(["config", "add", "exit-model", str(model), "--port", "9414"], env).returncode == 0
    dry_run = _run_cli(["start", "exit-model", "--dry-run"], env)
    assert dry_run.returncode == 0


def test_json_stdout_stays_clean_when_warnings_go_to_stderr(tmp_path):
    env = _base_env(tmp_path)
    model = tmp_path / "busy.gguf"
    model.write_text("x")
    sock, port = _occupy_port()
    try:
        assert _run_cli(["init"], env).returncode == 0

        add_result = _run_cli(["config", "add", "busy-model", str(model), "--port", str(port)], env)
        assert add_result.returncode == 0
        assert "Added model 'busy-model'" in add_result.stdout
        assert f"warning: port {port} on 127.0.0.1 appears in use right now" in add_result.stderr

        status_result = _run_cli(["status", "--json"], env)
        assert status_result.returncode == 0
        payload = json.loads(status_result.stdout)
        assert payload["models"][0]["name"] == "busy-model"
        assert status_result.stderr == ""
    finally:
        sock.close()
