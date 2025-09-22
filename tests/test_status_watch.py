import json
import threading
import time
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


def test_status_watch_mode_with_interrupt(tmp_path, monkeypatch, capsys):
    """Test that status --watch mode can be interrupted with KeyboardInterrupt"""
    # Init and add model
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    assert main(["config", "add", "m1", str(model), "--port", "9400"]) == 0
    _ = capsys.readouterr()

    # Mock health check
    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": False, "latency_ms": None})

    # Use threading to simulate KeyboardInterrupt after a short delay
    def interrupt_after_delay():
        time.sleep(0.1)  # Let watch mode start
        import os
        import signal
        os.kill(os.getpid(), signal.SIGINT)

    interrupt_thread = threading.Thread(target=interrupt_after_delay)
    interrupt_thread.daemon = True
    interrupt_thread.start()

    # This should exit gracefully on KeyboardInterrupt
    result = main(["status", "--watch", "--interval", "0.05"])
    assert result == 0

    # Should have printed at least one status update
    out = capsys.readouterr().out
    assert "name" in out and "mode" in out  # Header should be present


def test_status_table_format(tmp_path, monkeypatch, capsys):
    """Test that status outputs a properly formatted table"""
    # Init and add model
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    assert main(["config", "add", "test-model", str(model), "--port", "9401"]) == 0
    _ = capsys.readouterr()

    # Mock health and process discovery
    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": True, "latency_ms": 42, "http_status": 200})
    from llamacpp_manager.utils import write_pid
    write_pid("test-model", 1234)
    monkeypatch.setattr(cli, "process_alive", lambda pid: True)

    assert main(["status"]) == 0
    out = capsys.readouterr().out
    lines = out.strip().split('\n')

    # Should have header and data row
    assert len(lines) >= 2

    # Header should contain expected columns
    header = lines[0]
    assert "name" in header
    assert "mode" in header
    assert "pid" in header
    assert "host" in header
    assert "port" in header
    assert "up" in header
    assert "latency_ms" in header

    # Data row should contain our test model
    data_row = lines[1]
    assert "test-model" in data_row
    assert "1234" in data_row
    assert "9401" in data_row
    assert "True" in data_row
    assert "42" in data_row


def test_status_json_vs_table_consistency(tmp_path, monkeypatch, capsys):
    """Test that JSON and table output contain the same data"""
    # Init and add model
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    assert main(["config", "add", "consistency-test", str(model), "--port", "9402"]) == 0
    _ = capsys.readouterr()

    # Mock health and process discovery
    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "check_endpoint", lambda host, port, timeout_ms=2000: {"up": True, "latency_ms": 123})
    from llamacpp_manager.utils import write_pid
    write_pid("consistency-test", 5678)
    monkeypatch.setattr(cli, "process_alive", lambda pid: True)

    # Get JSON output
    assert main(["status", "--json"]) == 0
    json_out = capsys.readouterr().out
    json_data = json.loads(json_out)

    # Get table output
    assert main(["status"]) == 0
    table_out = capsys.readouterr().out

    # Verify JSON data appears in table
    model_data = json_data[0]
    assert model_data["name"] == "consistency-test"
    assert str(model_data["pid"]) in table_out
    assert str(model_data["port"]) in table_out
    assert str(model_data["latency_ms"]) in table_out