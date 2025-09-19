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


def test_launchd_install_uninstall_cli(tmp_path, monkeypatch, capsys):
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m1", str(model), "--port", "9801"]) == 0

    import llamacpp_manager.cli as cli
    # Stub launchctl to succeed
    monkeypatch.setattr(cli, "launchctl_bootstrap", lambda p: type("CP", (), {"returncode": 0, "stderr": ""})())
    monkeypatch.setattr(cli, "launchctl_kickstart", lambda name: type("CP", (), {"returncode": 0, "stderr": ""})())
    monkeypatch.setattr(cli, "launchctl_bootout", lambda name: type("CP", (), {"returncode": 0, "stderr": ""})())

    assert main(["launchd", "install", "m1"]) == 0
    out = capsys.readouterr().out
    assert "installed launchd agent for m1" in out

    assert main(["launchd", "uninstall", "m1"]) == 0
    out = capsys.readouterr().out
    assert "uninstalled launchd agent for m1" in out

