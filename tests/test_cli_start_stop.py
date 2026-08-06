from pathlib import Path

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


def test_start_stop_dry_run_and_pidfile(tmp_path, monkeypatch, capsys):
    # Prepare model
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m1", str(model), "--port", "9200"]) == 0

    # Dry run prints command and does not create pid
    assert main(["start", "m1", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "DRY-RUN:" in out
    p = tmp_path / "pids" / "m1.pid"
    assert not p.exists()

    # Monkeypatch start/stop
    import llamacpp_manager.cli as cli
    called = {}

    def fake_start(llama, spec, logdir, logging_config=None):
        called["start"] = (llama, spec.name)
        return 55555

    def fake_stop(pid):
        called["stop"] = pid

    monkeypatch.setattr(cli, "start_process", fake_start)
    monkeypatch.setattr(cli, "stop_process", fake_stop)

    # Start (writes pid)
    assert main(["start", "m1"]) == 0
    assert p.exists() and p.read_text().strip() == "55555"
    # Stop (reads pid and removes file)
    assert main(["stop", "m1"]) == 0
    assert not p.exists()


def test_start_port_override_is_ephemeral(tmp_path, capsys):
    """`start --port` overrides the configured port for this run only, without
    changing the persisted config."""
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m1", str(model), "--port", "9200"]) == 0

    # Dry-run with an override port should show the override, not the config port.
    assert main(["start", "m1", "--port", "8199", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "--port 8199" in out
    assert "--port 9200" not in out

    # The persisted config is unchanged.
    assert main(["config", "show", "m1"]) == 0
    show = capsys.readouterr().out
    assert "9200" in show and "8199" not in show
