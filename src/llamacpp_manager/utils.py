import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict
from datetime import datetime
import signal

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


def pid_dir() -> Path:
    override = os.environ.get("LLAMACPP_MANAGER_PID_DIR")
    if override:
        return expand(override)
    return app_support_dir() / "pids"


def pid_path(name: str) -> Path:
    return pid_dir() / f"{name}.pid"


def write_pid(name: str, pid: int) -> None:
    p = pid_path(name)
    ensure_dir(p.parent)
    atomic_write_text(p, str(pid))


def read_pid(name: str) -> int:
    p = pid_path(name)
    if not p.exists():
        raise FileNotFoundError(f"pid file not found for {name}: {p}")
    return int(p.read_text().strip())


def remove_pid(name: str) -> None:
    p = pid_path(name)
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass


def process_alive(pid: int) -> bool:
    try:
        # On POSIX, signal 0 checks existence/permission
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return False


def dir_empty_or_missing(p: Path) -> bool:
    if not p.exists():
        return True
    if not p.is_dir():
        return False
    return not any(p.iterdir())


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup_existing(dst: Path) -> Path:
    """If dst exists, move it aside to a timestamped backup directory."""
    if not dst.exists():
        return dst
    bak = dst.parent / f"{dst.name}.bak-{timestamp()}"
    shutil.move(str(dst), str(bak))
    return bak


def migrate_directory(src: Path, dst: Path, *, move: bool = False, force: bool = False) -> str:
    """Copy or move a directory to a new location safely.

    - If dst exists and not force, raise.
    - If dst exists and force, move it to a timestamped backup first.
    - If src is missing or empty, create dst if needed and no-op copy.
    """
    src = src.resolve()
    dst = dst.resolve()
    ensure_dir(dst.parent)

    if dst.exists():
        if not force and not dir_empty_or_missing(dst):
            raise ValueError(f"destination exists and not empty: {dst}; use --force to backup and overwrite")
        if force:
            backup_existing(dst)

    if not src.exists() or dir_empty_or_missing(src):
        ensure_dir(dst)
        return f"created destination (source empty or missing): {dst}"

    if move:
        shutil.move(str(src), str(dst))
        return f"moved {src} -> {dst}"
    else:
        # Python 3.9+: dirs_exist_ok
        shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
        return f"copied {src} -> {dst}"


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
