import json
from pathlib import Path

import pytest

from llamacpp_manager.cli import main


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    return cfgdir, logdir, piddir


def test_status_json_with_health_and_pid(tmp_path, monkeypatch, capsys):
    # Init and add model
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    assert main(["config", "add", "m1", str(model), "--port", "9300"]) == 0
    _ = capsys.readouterr()

    # Fake health and pid
    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": True, "latency_ms": 5, "http_status": 200, "version": "llama.cpp"})
    # Write a pid file and make process_alive return True
    from llamacpp_manager.utils import write_pid
    write_pid("m1", 4242)
    monkeypatch.setattr(cli, "process_alive", lambda pid: True)

    assert main(["status", "--json"]) == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, list) and data and data[0]["name"] == "m1"
    assert data[0]["up"] is True
    assert data[0]["pid"] == 4242
    assert data[0]["mode"] == "direct"
