import pytest

from pathlib import Path
from llamacpp_manager.cli import main


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    # Do NOT set SKIP_BIN_CHECK in this file; we test the check
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    return cfgdir, logdir, piddir


def test_binary_check_fails_when_missing(tmp_path, capsys):
    # init and set a non-existent llama_server_path
    assert main(["init"]) == 0
    # Edit config via update path: not implemented for llama_server_path; mimic by writing config file
    cfg_file = tmp_path / "cfg" / "config.yaml"
    text = cfg_file.read_text()
    text = text.replace("llama_server_path: /opt/homebrew/bin/llama-server", "llama_server_path: /nonexistent/llama-server")
    cfg_file.write_text(text)

    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["config", "add", "m1", str(model), "--port", "9701"]) == 0
    rc = main(["start", "m1"])  # should fail binary check
    assert rc != 0
    err = capsys.readouterr().err
    assert "llama-server not found" in err


def test_refuse_remote_bind_without_flag(tmp_path, monkeypatch, capsys):
    # Skip binary check to focus on host guard
    monkeypatch.setenv("LLAMACPP_MANAGER_SKIP_BIN_CHECK", "1")
    assert main(["init"]) == 0
    model = tmp_path / "m2.gguf"; model.write_text("x")
    # add with host 0.0.0.0
    assert main(["config", "add", "m2", str(model), "--host", "0.0.0.0", "--port", "9702"]) == 0
    rc = main(["start", "m2"])  # should refuse
    assert rc != 0
    err = capsys.readouterr().err
    assert "refusing to bind non-local host" in err
    # but allow with flag (mock start)
    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "start_process", lambda lp, spec, ld: 123)
    rc2 = main(["start", "m2", "--allow-remote"])  # ok
    assert rc2 == 0

