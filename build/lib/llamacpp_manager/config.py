import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import app_support_dir, config_path, logs_dir, ensure_dir, read_yaml, write_yaml


DEFAULT_LLAMA_SERVER_PATH = "/opt/homebrew/bin/llama-server"


@dataclass
class ModelSpec:
    name: str
    model_path: str
    host: str = "127.0.0.1"
    port: int = 0
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    autostart: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Normalize None lists/maps to empty for YAML clarity
        if d.get("args") is None:
            d["args"] = []
        if d.get("env") is None:
            d["env"] = {}
        return d


def default_config() -> Dict[str, Any]:
    return {
        "llama_server_path": DEFAULT_LLAMA_SERVER_PATH,
        "log_dir": str(logs_dir()),
        "timeout_ms": 2000,
        "models": [],
    }


def load_config() -> Dict[str, Any]:
    path = config_path()
    if not path.exists():
        return default_config()
    cfg = read_yaml(path)
    # Backfill defaults
    for k, v in default_config().items():
        cfg.setdefault(k, v)
    cfg.setdefault("models", [])
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    ensure_dir(app_support_dir())
    write_yaml(config_path(), cfg)


def validate_port_unique(cfg: Dict[str, Any], port: int, *, ignore_name: Optional[str] = None) -> Optional[str]:
    for m in cfg.get("models", []):
        if ignore_name and m.get("name") == ignore_name:
            continue
        try:
            if int(m.get("port")) == int(port):
                return m.get("name") or "<unknown>"
        except Exception:
            continue
    return None


def validate_model(cfg: Dict[str, Any], model: ModelSpec, *, updating: bool = False) -> List[str]:
    errors: List[str] = []
    if not model.name:
        errors.append("name is required")
    if not model.model_path:
        errors.append("model_path is required")
    else:
        p = Path(os.path.expanduser(model.model_path))
        if not p.exists():
            errors.append(f"model_path not found: {p}")
    if not (1 <= int(model.port) <= 65535):
        errors.append("port must be in 1..65535")
    # Unique port check
    conflict = validate_port_unique(cfg, model.port, ignore_name=model.name if updating else None)
    if conflict:
        errors.append(f"port {model.port} already used by model '{conflict}'")
    return errors


def list_models(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(cfg.get("models", []))


def get_model(cfg: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for m in cfg.get("models", []):
        if m.get("name") == name:
            return m
    return None


def add_model(cfg: Dict[str, Any], model: ModelSpec) -> None:
    if get_model(cfg, model.name):
        raise ValueError(f"model '{model.name}' already exists")
    errs = validate_model(cfg, model)
    if errs:
        raise ValueError("; ".join(errs))
    cfg.setdefault("models", []).append(model.to_dict())


def update_model(cfg: Dict[str, Any], name: str, updates: Dict[str, Any]) -> None:
    m = get_model(cfg, name)
    if not m:
        raise ValueError(f"model '{name}' not found")
    merged = {**m, **{k: v for k, v in updates.items() if v is not None}}
    spec = ModelSpec(
        name=merged.get("name", name),
        model_path=merged["model_path"],
        host=merged.get("host", "127.0.0.1"),
        port=int(merged["port"]),
        args=list(merged.get("args", []) or []),
        env=dict(merged.get("env", {}) or {}),
        autostart=bool(merged.get("autostart", False)),
    )
    errs = validate_model(cfg, spec, updating=True)
    if errs:
        raise ValueError("; ".join(errs))
    # apply updates back to original dict
    m.clear()
    m.update(spec.to_dict())


def remove_model(cfg: Dict[str, Any], name: str) -> bool:
    models = cfg.get("models", [])
    for i, m in enumerate(models):
        if m.get("name") == name:
            del models[i]
            return True
    return False
