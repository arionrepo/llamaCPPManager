import os
from pathlib import Path

import pytest

from llamacpp_manager.config import ModelSpec, add_model, update_model, remove_model, load_config, save_config
from llamacpp_manager.utils import app_support_dir, logs_dir, config_path


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"
    logdir = tmp_path / "logs"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    return cfgdir, logdir


def test_add_update_remove_model(tmp_path):
    # Prepare fake model file
    model_file = tmp_path / "model.gguf"
    model_file.write_text("dummy")

    cfg = load_config()
    spec = ModelSpec(name="m1", model_path=str(model_file), port=8081)
    add_model(cfg, spec)
    save_config(cfg)

    cfg2 = load_config()
    assert any(m["name"] == "m1" for m in cfg2["models"]) 

    update_model(cfg2, "m1", {"port": 8082})
    save_config(cfg2)
    cfg3 = load_config()
    m = [m for m in cfg3["models"] if m["name"] == "m1"][0]
    assert m["port"] == 8082

    assert remove_model(cfg3, "m1")
    save_config(cfg3)
    cfg4 = load_config()
    assert not any(m["name"] == "m1" for m in cfg4.get("models", []))


def test_port_conflict(tmp_path):
    f1 = tmp_path / "a.gguf"; f1.write_text("a")
    f2 = tmp_path / "b.gguf"; f2.write_text("b")
    cfg = load_config()
    add_model(cfg, ModelSpec(name="a", model_path=str(f1), port=9000))
    save_config(cfg)
    with pytest.raises(Exception):
        add_model(cfg, ModelSpec(name="b", model_path=str(f2), port=9000))

