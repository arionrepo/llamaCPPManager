import pytest

from llamacpp_manager.cli import main


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    monkeypatch.setenv("LLAMACPP_MANAGER_SKIP_BIN_CHECK", "1")
    return cfgdir, logdir, piddir


def test_ensure_running_starts_missing_autostart_direct(tmp_path, monkeypatch, capsys):
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m1", str(model), "--port", "9401"]) == 0

    # Mark autostart
    assert main(["config", "update", "m1", "--autostart"]) == 0

    import llamacpp_manager.cli as cli
    # Health says down
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": False})
    # Start process stub
    called = {}
    def fake_start(llama, spec, logdir):
        called["start"] = (spec.name, spec.port)
        return 77777
    monkeypatch.setattr(cli, "start_process", fake_start)

    assert main(["ensure-running"]) == 0
    out = capsys.readouterr().out
    assert "ensure-running: started 1 model" in out
    assert called.get("start") == ("m1", 9401)


def test_ensure_running_skips_when_up(tmp_path, monkeypatch, capsys):
    model = tmp_path / "m2.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m2", str(model), "--port", "9402"]) == 0
    assert main(["config", "update", "m2", "--autostart"]) == 0
    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": True})
    assert main(["ensure-running"]) == 0
    out = capsys.readouterr().out
    assert "ensure-running: started 0 model" in out
