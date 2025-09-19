from pathlib import Path

from llamacpp_manager.logs import rotate_file, open_log_append


def test_rotate_file_creates_backup_and_truncates(tmp_path: Path):
    log = tmp_path / "model.log"
    log.write_bytes(b"x" * (1024 * 1024))  # 1MB
    # Set threshold small to force rotation
    rotate_file(log, max_bytes=100, backups=2)
    # After rotation, current file exists but is truncated (size 0)
    assert log.exists()
    assert log.stat().st_size == 0
    # A backup .1 should exist with previous content size
    b1 = log.with_suffix(log.suffix + ".1")
    assert b1.exists()
    assert b1.stat().st_size == 1024 * 1024


def test_open_log_append_creates_file(tmp_path: Path):
    log = tmp_path / "sub" / "model.log"
    with open_log_append(log) as f:
        f.write("hello\n")
    assert log.exists()
    assert log.read_text().strip() == "hello"

