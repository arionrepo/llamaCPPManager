import pytest

from llamacpp_manager import discovery as disc


def test_find_llama_processes_parsing(monkeypatch):
    sample = """
1234 /opt/homebrew/bin/llama-server -m /path/model.gguf --host 127.0.0.1 --port 9999
5678 /usr/bin/python script.py
    """.strip()
    monkeypatch.setattr(disc, "_ps_output", lambda: sample)
    procs = disc.find_llama_processes()
    assert len(procs) == 1
    assert procs[0]["pid"] == 1234
    assert "llama-server" in procs[0]["argv"][0]

