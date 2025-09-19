from pathlib import Path

from llamacpp_manager.launchd import render_plist, build_program_arguments, plist_path, agent_label
from llamacpp_manager.config import ModelSpec


def test_render_plist_and_program_arguments(tmp_path):
    spec = ModelSpec(name="m1", model_path=str(tmp_path/"m.gguf"), host="127.0.0.1", port=9400, args=["-c","4096"], env={"A":"B"})
    llama = "/opt/homebrew/bin/llama-server"
    data = render_plist(llama, spec, log_dir=tmp_path)
    assert data["Label"] == agent_label("m1")
    assert data["ProgramArguments"][0] == llama
    assert data["ProgramArguments"][1:3] == ["-m", str(tmp_path/"m.gguf")]
    assert "--host" in data["ProgramArguments"] and "--port" in data["ProgramArguments"]
    assert data["EnvironmentVariables"]["A"] == "B"
    assert str(tmp_path/"m1.out.log") in data["StandardOutPath"]
    assert str(tmp_path/"m1.err.log") in data["StandardErrorPath"]

