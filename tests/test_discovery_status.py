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
    # A process found only by port scan (no PID file, no launchd plist) was NOT
    # started by the manager, so its output is not captured -> "external".
    assert data["models"][0]["process_source"] == "external"
    assert data["models"][0]["logs_available"] is False
    assert data["models"][0]["logs_hint"]


def test_status_discovered_with_launchd_plist_is_managed(tmp_path, monkeypatch, capsys):
    """A discovered process (no PID file) that has a launchd plist installed is
    manager-managed: launchd captures its output, so process_source == 'launchd'
    and logs are considered available."""
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    assert main(["config", "add", "m1", str(model), "--port", "9502"]) == 0
    _ = capsys.readouterr()

    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "find_llama_processes", lambda: [{"pid": 4321, "argv": ["llama-server", "-m", str(model), "--port", "9502"]}])
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": True, "latency_ms": 1})

    # Pretend a launchd plist exists for this model (fake object with .exists()
    # so we don't disturb Path.exists used elsewhere in status gathering).
    class _FakePlist:
        def exists(self):
            return True
    monkeypatch.setattr(cli, "plist_path", lambda name: _FakePlist())

    assert main(["status", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["models"][0]["process_source"] == "launchd"
    assert data["models"][0]["logs_available"] is True
    assert data["models"][0]["logs_hint"] is None

