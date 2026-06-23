import json
import pytest

from llamacpp_manager.cli import main


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    return cfgdir, logdir, piddir


def test_status_uses_process_discovery_when_no_pid(tmp_path, monkeypatch, capsys):
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    assert main(["config", "add", "m1", str(model), "--port", "9501"]) == 0
    _ = capsys.readouterr()

    # Monkeypatch discovery to return a running llama-server with --port 9501
    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "find_llama_processes", lambda: [{"pid": 1234, "argv": ["/opt/homebrew/bin/llama-server", "-m", str(model), "--host", "127.0.0.1", "--port", "9501"]}])
    # Health up so status shows up=True
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": True, "latency_ms": 1})

    assert main(["status", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["models"][0]["pid"] == 1234
    # Field semantics changed: `mode` is now performance mode (basic/tools/
    # performance/extended). The direct/launchd distinction moved to
    # `process_source`. Process-discovery semantics are tested via process_source.
    assert data["models"][0]["mode"] == "basic"
    assert data["models"][0]["process_source"] == "direct"

