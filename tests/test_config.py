import os
from pathlib import Path

import pytest

from llamacpp_manager.config import ModelSpec, spec_from_dict, add_model, update_model, remove_model, load_config, save_config
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


def test_spec_from_dict_round_trips_all_fields(tmp_path):
    """I3 + regression: the canonical mapping preserves mode/ctx_size/
    n_gpu_layers/llama_server_path (inline constructors used to drop them)."""
    f = tmp_path / "m.gguf"; f.write_text("x")
    m = {
        "name": "m1", "model_path": str(f), "port": 8081, "mode": "performance",
        "ctx_size": 65536, "n_gpu_layers": 50,
        "llama_server_path": "/custom/llama-server",
    }
    spec = spec_from_dict(m)
    assert spec.mode == "performance"
    assert spec.ctx_size == 65536
    assert spec.n_gpu_layers == 50
    assert spec.llama_server_path == "/custom/llama-server"


def test_spec_from_dict_normalizes_empty_binary_override(tmp_path):
    f = tmp_path / "m.gguf"; f.write_text("x")
    spec = spec_from_dict({"name": "m", "model_path": str(f), "port": 8081, "llama_server_path": ""})
    assert spec.llama_server_path is None
    # and to_dict omits the unset override entirely
    assert "llama_server_path" not in spec.to_dict()


def test_update_model_preserves_mode_and_binary_override(tmp_path):
    """Previously update_model rebuilt the spec without ctx_size/mode, wiping
    them on any update. Now an unrelated update must keep them."""
    f = tmp_path / "m.gguf"; f.write_text("x")
    cfg = load_config()
    add_model(cfg, ModelSpec(name="m1", model_path=str(f), port=8081, mode="tools",
                             ctx_size=131072, llama_server_path="/custom/llama-server"))
    save_config(cfg)
    cfg2 = load_config()
    update_model(cfg2, "m1", {"port": 8090})  # unrelated field
    save_config(cfg2)
    m = [x for x in load_config()["models"] if x["name"] == "m1"][0]
    assert m["port"] == 8090
    assert m["mode"] == "tools"
    assert m["ctx_size"] == 131072
    assert m["llama_server_path"] == "/custom/llama-server"


def test_port_conflict(tmp_path):
    f1 = tmp_path / "a.gguf"; f1.write_text("a")
    f2 = tmp_path / "b.gguf"; f2.write_text("b")
    cfg = load_config()
    add_model(cfg, ModelSpec(name="a", model_path=str(f1), port=9000))
    save_config(cfg)
    with pytest.raises(Exception):
        add_model(cfg, ModelSpec(name="b", model_path=str(f2), port=9000))

