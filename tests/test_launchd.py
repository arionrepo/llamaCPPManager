from pathlib import Path

from llamacpp_manager.launchd import render_plist, build_program_arguments, plist_path, agent_label
from llamacpp_manager.config import ModelSpec


def test_render_plist_and_program_arguments(tmp_path):
    model = tmp_path / "m.gguf"; model.write_text("x")  # launchd argv now validates existence (I9)
    spec = ModelSpec(name="m1", model_path=str(model), host="127.0.0.1", port=9400, args=["-c","4096"], env={"A":"B"})
    llama = "/opt/homebrew/bin/llama-server"
    data = render_plist(llama, spec, log_dir=tmp_path)
    assert data["Label"] == agent_label("m1")
    assert data["ProgramArguments"][0] == llama
    assert data["ProgramArguments"][1:3] == ["-m", str(model)]
    assert "--host" in data["ProgramArguments"] and "--port" in data["ProgramArguments"]
    # I9: launchd argv now matches build_argv — full flag set, not just -m/--host/--port
    assert "--n-gpu-layers" in data["ProgramArguments"]
    assert "--ctx-size" in data["ProgramArguments"]
    assert data["EnvironmentVariables"]["A"] == "B"
    assert str(tmp_path/"m1.out.log") in data["StandardOutPath"]
    assert str(tmp_path/"m1.err.log") in data["StandardErrorPath"]


def test_render_plist_matches_start_argv(tmp_path):
    """I9: the launchd ProgramArguments must be identical to what process.build_argv
    produces for `start`, so a model launches the same either way."""
    from llamacpp_manager.process import build_argv
    model = tmp_path / "m.gguf"; model.write_text("x")
    spec = ModelSpec(name="m1", model_path=str(model), port=9401, mode="tools",
                     llama_server_path="/custom/llama-server")
    data = render_plist("/global/llama-server", spec, log_dir=tmp_path)
    assert data["ProgramArguments"] == build_argv("/global/llama-server", spec)
    # per-model binary override honored, single-slot default applied
    assert data["ProgramArguments"][0] == "/custom/llama-server"
    assert "--parallel" in data["ProgramArguments"]

