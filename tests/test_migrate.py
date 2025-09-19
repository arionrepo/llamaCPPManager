import os
from pathlib import Path

import pytest

from llamacpp_manager.cli import main


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"
    logdir = tmp_path / "logs"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    return cfgdir, logdir


def test_migrate_config_and_logs(tmp_path):
    # Arrange current dirs and files
    assert main(["init"]) == 0
    (tmp_path / "cfg" / "config.yaml").write_text("llama_server_path: /opt/homebrew/bin/llama-server\nmodels: []\n")
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "logs" / "m1.log").write_text("log")

    new_cfg = tmp_path / "newcfg"
    new_logs = tmp_path / "newlogs"
    rc = main(["config", "migrate", "--to-config-dir", str(new_cfg), "--to-log-dir", str(new_logs), "--move", "--force"])
    assert rc == 0
    assert (new_cfg / "config.yaml").exists()
    assert (new_logs / "m1.log").exists()

