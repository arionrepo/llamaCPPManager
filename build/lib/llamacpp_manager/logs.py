from __future__ import annotations

import os
import shutil
from pathlib import Path

from .utils import ensure_dir


def rotate_file(path: Path, max_bytes: int = 10 * 1024 * 1024, backups: int = 5) -> None:
    """Basic size-based rotation for a single file.

    If file exceeds max_bytes, shift backups and truncate current.
    """
    try:
        if not path.exists():
            ensure_dir(path.parent)
            return
        if path.stat().st_size < max_bytes:
            return
        # rotate: file -> .1, .1 -> .2, ...
        for i in range(backups, 0, -1):
            src = path.with_suffix(path.suffix + f".{i}")
            dst = path.with_suffix(path.suffix + f".{i+1}")
            if src.exists():
                if i == backups and dst.exists():
                    try:
                        dst.unlink()
                    except Exception:
                        pass
                src.rename(dst)
        # move current to .1
        first = path.with_suffix(path.suffix + ".1")
        shutil.copy2(path, first)
        # truncate current
        with path.open("w") as f:
            f.truncate(0)
    except Exception:
        # best-effort; avoid crashing caller on rotation failure
        pass


def open_log_append(path: Path):
    ensure_dir(path.parent)
    return path.open("a", buffering=1)

