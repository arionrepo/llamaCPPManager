import pytest

from llamacpp_manager.cli import main


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    return cfgdir, logdir, piddir


def test_start_stop_with_launchd_flags(tmp_path, monkeypatch, capsys):
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m1", str(model), "--port", "9601"]) == 0

    import llamacpp_manager.cli as cli
    # Stub launchctl helpers
    monkeypatch.setattr(cli, "launchctl_bootstrap", lambda p: type("CP", (), {"returncode": 0, "stderr": ""})())
    monkeypatch.setattr(cli, "launchctl_kickstart", lambda name: type("CP", (), {"returncode": 0, "stderr": ""})())
    monkeypatch.setattr(cli, "launchctl_bootout", lambda name: type("CP", (), {"returncode": 0, "stderr": ""})())

    assert main(["start", "m1", "--launchd"]) == 0
    out = capsys.readouterr().out
    assert "launchd started m1" in out

    assert main(["stop", "m1", "--launchd"]) == 0
    out = capsys.readouterr().out
    assert "launchd stopped m1" in out

