import os
from pathlib import Path

import pytest

from llamacpp_manager.cli import main
from llamacpp_manager.utils import config_path


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"
    logdir = tmp_path / "logs"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    return cfgdir, logdir


def test_init_and_list(tmp_path, capsys):
    assert main(["init"]) == 0
    out = capsys.readouterr().out
    assert str(config_path()) in out
    assert main(["config", "list"]) == 0


def test_add_list_update_remove(tmp_path, capsys):
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m1", str(model), "--port", "9100"]) == 0
    assert main(["config", "list"]) == 0
    assert main(["config", "update", "m1", "--port", "9101"]) == 0
    assert main(["config", "remove", "m1"]) == 0

