import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_deploy(args, env):
    return subprocess.run(
        ["bash", "deploy.sh", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def test_deploy_verify_with_fake_cli_and_mcp(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    status_output = tmp_path / "status.json"
    gui_app = tmp_path / "Applications" / "llamaCPP Manager.app"
    gui_app.mkdir(parents=True)

    _write_executable(
        bin_dir / "llamacpp-manager",
        """#!/bin/bash
set -euo pipefail
if [[ "$1" == "status" && "$2" == "--json" ]]; then
  printf '%s\n' '{"models":[],"infrastructure":[],"logging":{"enabled":true,"max_bytes":1,"backups":1,"timestamps":true}}'
  exit 0
fi
exit 2
""",
    )
    _write_executable(
        bin_dir / "llamacpp-mcp-server",
        "#!/bin/bash\nexit 0\n",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DEPLOY_GUI_APP"] = str(gui_app)
    env["DEPLOY_STATUS_OUTPUT_PATH"] = str(status_output)

    result = _run_deploy(["verify"], env)

    assert result.returncode == 0, result.stderr
    assert "verify complete" in result.stdout
    assert status_output.exists()


def test_deploy_install_is_idempotent_with_fake_pipx_and_gui_installer(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "pipx.log"
    gui_app = tmp_path / "Applications" / "llamaCPP Manager.app"
    fake_pipx = tmp_path / "fake-pipx.sh"
    fake_gui = tmp_path / "fake-install-gui.sh"

    _write_executable(
        fake_pipx,
        f"""#!/bin/bash
set -euo pipefail
printf '%s\\n' "$*" >> "{log_file}"
cat > "{bin_dir / 'llamacpp-manager'}" <<'EOF'
#!/bin/bash
if [[ "${{1:-}}" == "status" && "${{2:-}}" == "--json" ]]; then
  printf '%s\\n' '{{"models":[],"infrastructure":[],"logging":{{"enabled":true,"max_bytes":1,"backups":1,"timestamps":true}}}}'
  exit 0
fi
exit 0
EOF
chmod +x "{bin_dir / 'llamacpp-manager'}"
cat > "{bin_dir / 'llamacpp-mcp-server'}" <<'EOF'
#!/bin/bash
exit 0
EOF
chmod +x "{bin_dir / 'llamacpp-mcp-server'}"
""",
    )
    _write_executable(
        fake_gui,
        f"""#!/bin/bash
set -euo pipefail
mkdir -p "{gui_app}"
exit 0
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    env["DEPLOY_PIPX_BIN"] = str(fake_pipx)
    env["DEPLOY_GUI_INSTALLER"] = str(fake_gui)
    env["DEPLOY_GUI_APP"] = str(gui_app)

    first = _run_deploy(["install"], env)
    second = _run_deploy(["install"], env)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert log_file.read_text().count("install --force .") == 2
    assert (bin_dir / "llamacpp-manager").exists()
    assert (bin_dir / "llamacpp-mcp-server").exists()


def test_deploy_source_revision_mismatch_exits_6(tmp_path):
    env = os.environ.copy()
    env["DEPLOY_GUI_APP"] = str(tmp_path / "missing.app")

    result = _run_deploy(["verify", "--source-revision", "deadbeef"], env)

    assert result.returncode == 6
    assert "source revision mismatch" in result.stderr


def test_deploy_check_deps_passes_on_dev_machine():
    result = subprocess.run(
        ["bash", "deploy.sh", "check-deps"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    assert result.returncode == 0, result.stderr
