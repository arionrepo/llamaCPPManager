from __future__ import annotations

import os
import shutil
import sys
import datetime
from pathlib import Path
from typing import TextIO

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


class TimestampedLogWriter:
    """
    Wrapper that adds timestamps to each line written to a log file.

    Business Purpose: Provides clear chronological ordering of log entries
    for debugging and troubleshooting model behavior.
    """

    def __init__(self, file_handle: TextIO, name: str = "stdout"):
        """
        Initialize timestamped log writer.

        Args:
            file_handle: Underlying file handle to write to
            name: Stream name for identification (stdout/stderr)
        """
        self.file = file_handle
        self.name = name
        self.buffer = ""

    def write(self, data: str) -> int:
        """
        Write data with timestamps prepended to each line.

        Args:
            data: String data to write

        Returns:
            Number of bytes written
        """
        if not data:
            return 0

        # Add data to buffer
        self.buffer += data

        # Process complete lines
        lines = self.buffer.split('\n')

        # Keep incomplete line in buffer
        self.buffer = lines[-1]

        # Write complete lines with timestamps
        for line in lines[:-1]:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            tagged_line = f"[{timestamp}] [{self.name}] {line}\n"
            self.file.write(tagged_line)

        return len(data)

    def flush(self):
        """Flush any remaining buffer and underlying file."""
        if self.buffer:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            tagged_line = f"[{timestamp}] [{self.name}] {self.buffer}\n"
            self.file.write(tagged_line)
            self.buffer = ""
        self.file.flush()

    def fileno(self):
        """Return file descriptor for compatibility."""
        return self.file.fileno()

    def close(self):
        """Close the underlying file."""
        self.flush()
        self.file.close()


def open_timestamped_log(path: Path, stream_name: str = "stdout") -> TimestampedLogWriter:
    """
    Open a log file with automatic timestamping.

    Args:
        path: Path to log file
        stream_name: Name of stream (stdout/stderr) for tagging

    Returns:
        TimestampedLogWriter instance

    Example:
        with open_timestamped_log(Path("model.log"), "stdout") as log:
            log.write("Model started\n")
        # Writes: [2025-10-07 14:30:45.123] [stdout] Model started
    """
    ensure_dir(path.parent)
    file_handle = path.open("a", buffering=1)
    return TimestampedLogWriter(file_handle, stream_name)

