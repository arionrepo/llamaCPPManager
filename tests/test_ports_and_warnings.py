import socket
import threading

import pytest

from llamacpp_manager.cli import main


def occupy_port(port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", port))
    s.listen(1)
    return s


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    monkeypatch.setenv("LLAMACPP_MANAGER_SKIP_BIN_CHECK", "1")
    return cfgdir, logdir, piddir


def test_config_add_warns_when_port_busy(tmp_path, capsys):
    s = occupy_port(9751)
    try:
        assert main(["init"]) == 0
        model = tmp_path / "m.gguf"; model.write_text("x")
        assert main(["config", "add", "m1", str(model), "--port", "9751"]) == 0
        err = capsys.readouterr().err
        assert "port 9751" in err
    finally:
        s.close()


def test_start_refuses_when_port_busy(tmp_path, monkeypatch, capsys):
    s = occupy_port(9752)
    try:
        assert main(["init"]) == 0
        model = tmp_path / "m.gguf"; model.write_text("x")
        assert main(["config", "add", "m1", str(model), "--port", "9752"]) == 0
        rc = main(["start", "m1"])  # should refuse due to busy port
        assert rc != 0
        err = capsys.readouterr().err
        assert "already in use" in err
    finally:
        s.close()

