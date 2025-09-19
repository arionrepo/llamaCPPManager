import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict

import yaml


APP_NAME = "llamaCPPManager"


def expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


def app_support_dir() -> Path:
    # Allow override for testing or custom setups
    override = os.environ.get("LLAMACPP_MANAGER_CONFIG_DIR")
    if override:
        return expand(override)
    # macOS Application Support path
    base = expand("~/Library/Application Support")
    return base / APP_NAME


def logs_dir() -> Path:
    override = os.environ.get("LLAMACPP_MANAGER_LOG_DIR")
    if override:
        return expand(override)
    return expand(f"~/Library/Logs/{APP_NAME}")


def is_inside_git_repo(path: Path) -> bool:
    p = path.resolve()
    root = Path(p.root)
    while True:
        if (p / ".git").exists():
            return True
        if p == p.parent or p == root:
            return False
        p = p.parent


def config_path() -> Path:
    return app_support_dir() / "config.yaml"


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def atomic_write_text(path: Path, data: str) -> None:
    ensure_dir(path.parent)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name, dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def read_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("Config root must be a YAML mapping")
    return data


def write_yaml(path: Path, data: Dict[str, Any]) -> None:
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    atomic_write_text(path, text)


def to_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)
