import json
from pathlib import Path

from llamacpp_manager.cli import main
from llamacpp_manager.lifecycle_log import log_event, log_path


COMMON_REQUIRED_FIELDS = {
    "ts": str,
    "event": str,
    "pid_self": int,
}

EVENT_REQUIRED_FIELDS = {
    "cli.start.begin": {
        "caller": str,
        "dry_run": bool,
        "launchd": bool,
        "target": str,
    },
    "cli.stop.begin": {
        "caller": str,
        "launchd": bool,
        "target": str,
    },
    "cli.chat.reply_received": {
        "model": str,
        "reply_length": int,
        "caller": str,
        "source": str,
    },
    "cli.status.fetched": {
        "model_count": int,
        "infrastructure_count": int,
        "caller": str,
        "source": str,
    },
    "process.stop.sigterm": {
        "caller": str,
        "pid": int,
        "timeout": (int, float),
    },
    "process.stop.exited_after_sigterm": {
        "pid": int,
    },
}


def _assert_entry_shape(entry):
    for field, expected_type in COMMON_REQUIRED_FIELDS.items():
        assert field in entry, f"missing common field {field}: {entry}"
        assert isinstance(entry[field], expected_type), f"{field} has wrong type in {entry}"

    required = EVENT_REQUIRED_FIELDS.get(entry["event"], {})
    for field, expected_type in required.items():
        assert field in entry, f"{entry['event']} missing {field}: {entry}"
        assert isinstance(entry[field], expected_type), f"{entry['event']}.{field} has wrong type in {entry}"


def _read_entries_from_offset(path, offset):
    with path.open() as handle:
        handle.seek(offset)
        return [json.loads(line) for line in handle if line.strip()]


def test_lifecycle_log_live_appends_match_schema(tmp_path, monkeypatch, capsys):
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    monkeypatch.setenv("LLAMACPP_MANAGER_SKIP_BIN_CHECK", "1")

    path = log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    offset = path.stat().st_size if path.exists() else 0

    model = tmp_path / "schema-log.gguf"
    model.write_text("x")
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    assert main(["config", "add", "schema-log", str(model), "--port", "9390"]) == 0
    _ = capsys.readouterr()

    assert main(["start", "schema-log", "--dry-run"]) == 0
    _ = capsys.readouterr()
    _ = main(["stop", "schema-log"])
    _ = capsys.readouterr()

    log_event(
        "cli.chat.reply_received",
        model="schema-log",
        caller="gui.ChatViewModel.sendMessage()",
        source="gui",
        reply_length=2,
    )
    log_event(
        "cli.status.fetched",
        caller="gui.StatusViewModel.refresh()",
        source="gui",
        model_count=1,
        infrastructure_count=3,
    )

    entries = _read_entries_from_offset(path, offset)
    assert entries, "expected new lifecycle entries to be appended"
    for entry in entries:
        _assert_entry_shape(entry)

    events = {entry["event"] for entry in entries}
    assert "cli.start.begin" in events
    assert "cli.stop.begin" in events
    assert "cli.chat.reply_received" in events
    assert "cli.status.fetched" in events


def test_lifecycle_log_rotation_preserves_json_lines(tmp_path, monkeypatch):
    import llamacpp_manager.lifecycle_log as lifecycle_log

    active = tmp_path / "lifecycle.jsonl"
    rotated = tmp_path / "lifecycle.jsonl.1"
    monkeypatch.setattr(lifecycle_log, "_LOG_PATH", active)

    log_event("process.stop.sigterm", caller="test.lifecycle", pid=123, timeout=1.5)
    active.rename(rotated)
    log_event("process.stop.exited_after_sigterm", pid=123)

    for candidate in (rotated, active):
        lines = [json.loads(line) for line in candidate.read_text().splitlines() if line.strip()]
        assert lines, f"expected JSON lines in {candidate}"
        for entry in lines:
            _assert_entry_shape(entry)
