# Tests for the `history` CLI (KNOWN-ISSUES README-drift reconciliation) and the
# I11 `cmd_restart` port-release wait + return-start-result behavior.
from pathlib import Path

import pytest

from llamacpp_manager.cli import main
import llamacpp_manager.cli as cli


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(tmp_path / "pids"))
    monkeypatch.setenv("LLAMACPP_MANAGER_SKIP_BIN_CHECK", "1")


def test_restart_waits_for_port_release_and_returns_start_result(tmp_path, monkeypatch):
    """KNOWN-ISSUES I11: restart must wait for the port to free after stop before
    starting, and its exit code must reflect the start result (not max(stop,start)),
    so a 'nothing to stop' (rc=1) does not fail an otherwise-successful restart."""
    model = tmp_path / "m.gguf"; model.write_text("x")
    assert main(["init"]) == 0
    assert main(["config", "add", "m1", str(model), "--port", "9200"]) == 0

    calls = {"stop": 0, "start": 0, "port_checks": 0}
    # Internal stop "found nothing running" -> returns 1 (the inflation case).
    monkeypatch.setattr(cli, "cmd_stop", lambda a: calls.__setitem__("stop", calls["stop"] + 1) or 1)
    monkeypatch.setattr(cli, "cmd_start", lambda a: calls.__setitem__("start", calls["start"] + 1) or 0)

    # Port reports "in use" for the first 3 polls, then frees (slow release).
    seq = [True, True, True, False]

    def fake_port_in_use(host, port):
        calls["port_checks"] += 1
        return seq.pop(0) if seq else False

    monkeypatch.setattr(cli, "port_in_use", fake_port_in_use)

    rc = main(["restart", "m1"])
    assert rc == 0                       # returns start result (0), not max(1, 0)
    assert calls["stop"] == 1 and calls["start"] == 1
    assert calls["port_checks"] >= 3     # actually waited for the port to free


class _FakeStore:
    def __init__(self, *a, **k):
        pass

    def list_conversations(self, limit=50, offset=0):
        return [{"id": 1, "title": "Test conv", "message_count": 2, "updated_at": "2026-01-01"}]

    def search_messages(self, query, limit=50):
        return [{"conversation_id": 1, "conversation_title": "Test conv", "content": f"match:{query}"}]

    def get_conversation(self, conversation_id):
        return {"id": conversation_id, "title": "Test conv", "messages": []}


def test_history_list_search_export(monkeypatch, capsys):
    """history list/search/export wire to the ChatStorage query API. cmd_history
    imports ChatStorage locally, so patch it at the source module."""
    monkeypatch.setattr("llamacpp_manager.chat_storage.ChatStorage", _FakeStore)

    assert main(["history", "list"]) == 0
    out = capsys.readouterr().out
    assert "Test conv" in out and "[1]" in out

    assert main(["history", "search", "quantum"]) == 0
    out = capsys.readouterr().out
    assert "match:quantum" in out

    assert main(["history", "export", "--conversation", "1"]) == 0
    out = capsys.readouterr().out
    assert '"title"' in out and "Test conv" in out
