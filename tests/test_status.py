import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from llamacpp_manager.cli import main


SCHEMA_PATH = Path(__file__).parent / "fixtures" / "status_schema.json"


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    cfgdir = tmp_path / "cfg"; logdir = tmp_path / "logs"; piddir = tmp_path / "pids"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_PID_DIR", str(piddir))
    return cfgdir, logdir, piddir


def _status_schema():
    return json.loads(SCHEMA_PATH.read_text())


def _assert_status_schema(payload):
    schema = _status_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)


def _read_status_payload(capsys):
    payload = json.loads(capsys.readouterr().out)
    _assert_status_schema(payload)
    return payload


def _fake_health(monkeypatch, *, up_ports=None):
    up_ports = up_ports or set()
    import llamacpp_manager.cli as cli

    def fake_check_endpoint(host, port, timeout_ms=2000):
        if port in up_ports:
            return {
                "up": True,
                "latency_ms": 5,
                "http_status": 200,
                "version": "llama.cpp",
                "health_state": "healthy",
            }
        return {
            "up": False,
            "latency_ms": 0,
            "http_status": None,
            "version": None,
            "health_state": "down",
        }

    monkeypatch.setattr(cli, "check_endpoint", fake_check_endpoint)


def _add_model(tmp_path, capsys, name, port, *, deployment_type="native", host="127.0.0.1"):
    if deployment_type == "mlx":
        model_path = "mlx-community/gemma-3-1b-it-4bit"
    elif deployment_type == "mlx-vlm":
        model_path = "mlx-community/diffusiongemma-26B-A4B-it-4bit"
    else:
        model_path = tmp_path / f"{name}.gguf"
        model_path.write_text("x")

    args = [
        "config", "add", name, str(model_path),
        "--host", host,
        "--port", str(port),
        "--deployment-type", deployment_type,
    ]
    assert main(args) == 0
    _ = capsys.readouterr()


def test_status_schema_is_versioned():
    schema = _status_schema()
    assert schema["schema_version"] == 1
    assert schema["$id"].endswith("/status/v1")


def test_status_json_empty_config_matches_schema(capsys):
    assert main(["init"]) == 0
    _ = capsys.readouterr()

    assert main(["status", "--json"]) == 0
    payload = _read_status_payload(capsys)

    assert payload["models"] == []
    assert payload["infrastructure"]
    assert payload["logging"]["enabled"] is True


@pytest.mark.parametrize(
    ("deployment_type", "port"),
    [
        ("native", 9301),
        ("container", 9302),
        ("mlx", 9303),
        ("mlx-vlm", 9304),
    ],
)
def test_status_json_covers_all_deployment_types(tmp_path, monkeypatch, capsys, deployment_type, port):
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    _fake_health(monkeypatch)
    _add_model(tmp_path, capsys, f"{deployment_type}-model", port, deployment_type=deployment_type)

    assert main(["status", "--json"]) == 0
    payload = _read_status_payload(capsys)

    row = payload["models"][0]
    assert row["deployment_type"] == deployment_type
    assert row["up"] is False
    assert row["host"] == "127.0.0.1"
    assert row["process_source"] == "stopped"
    if deployment_type in {"mlx", "mlx-vlm"}:
        assert row["model_filename"] is None
        assert row["quantization"] is None
    else:
        assert row["model_filename"] == f"{deployment_type}-model.gguf"
        assert row["file_size_gb"] is not None


def test_status_json_covers_mixed_running_and_stopped_models(tmp_path, monkeypatch, capsys):
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    _add_model(tmp_path, capsys, "running-model", 9310)
    _add_model(tmp_path, capsys, "stopped-model", 9311)

    _fake_health(monkeypatch, up_ports={9310})
    from llamacpp_manager.utils import write_pid
    write_pid("running-model", 4242)

    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "process_alive", lambda pid: pid == 4242)

    assert main(["status", "--json"]) == 0
    payload = _read_status_payload(capsys)

    rows = {row["name"]: row for row in payload["models"]}
    assert rows["running-model"]["up"] is True
    assert rows["running-model"]["pid"] == 4242
    assert rows["running-model"]["process_source"] == "direct"
    assert rows["stopped-model"]["up"] is False
    assert rows["stopped-model"]["pid"] is None
    assert rows["stopped-model"]["process_source"] == "stopped"


def test_status_json_includes_infrastructure_and_optional_fields(tmp_path, monkeypatch, capsys):
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    _fake_health(monkeypatch)
    _add_model(tmp_path, capsys, "optional-fields", 9320, deployment_type="mlx")

    assert main(["status", "--json"]) == 0
    payload = _read_status_payload(capsys)

    assert payload["infrastructure"]
    row = payload["models"][0]
    assert row["model_filename"] is None
    assert row["file_size_gb"] is None
    assert row["quantization"] is None
    assert row["ram_mb"] is None
    assert row["cpu_percent"] is None
    assert row["description"] is None


def test_status_json_and_table_outputs_stay_consistent(tmp_path, monkeypatch, capsys):
    assert main(["init"]) == 0
    _ = capsys.readouterr()
    _add_model(tmp_path, capsys, "m1", 9330)

    _fake_health(monkeypatch, up_ports={9330})
    from llamacpp_manager.utils import write_pid
    write_pid("m1", 4242)

    import llamacpp_manager.cli as cli
    monkeypatch.setattr(cli, "process_alive", lambda pid: pid == 4242)

    assert main(["status", "--json"]) == 0
    payload = _read_status_payload(capsys)

    assert main(["status"]) == 0
    table = capsys.readouterr().out

    row = payload["models"][0]
    assert "Infrastructure Components:" in table
    assert row["name"] in table
    assert str(row["pid"]) in table
    assert str(row["port"]) in table
    assert str(row["latency_ms"]) in table
