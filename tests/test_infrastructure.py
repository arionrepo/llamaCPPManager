# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/tests/test_infrastructure.py
# Description: Unit tests for infrastructure component management
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-01

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from llamacpp_manager import infrastructure
from llamacpp_manager.config import load_config, list_infrastructure_components, get_infrastructure_component


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    """Isolate test environment for config and logs."""
    cfgdir = tmp_path / "cfg"
    logdir = tmp_path / "logs"
    monkeypatch.setenv("LLAMACPP_MANAGER_CONFIG_DIR", str(cfgdir))
    monkeypatch.setenv("LLAMACPP_MANAGER_LOG_DIR", str(logdir))
    return cfgdir, logdir


def test_expand_path():
    """Test path expansion with ~ and environment variables."""
    home = str(Path.home())
    expanded = infrastructure.expand_path("~/test/path")
    assert expanded == f"{home}/test/path"
    assert "~" not in expanded


def test_validate_script_path_missing_file(tmp_path):
    """Test validation fails for non-existent script."""
    non_existent = str(tmp_path / "missing.sh")
    errors = infrastructure.validate_script_path(non_existent, "test_component")
    assert len(errors) > 0
    assert "not found" in errors[0].lower()


def test_validate_script_path_not_executable(tmp_path):
    """Test validation fails for non-executable script."""
    script = tmp_path / "test.sh"
    script.write_text("#!/bin/bash\necho test")
    # Don't make it executable
    errors = infrastructure.validate_script_path(str(script), "test_component")
    assert len(errors) > 0
    assert "not executable" in errors[0].lower()


def test_validate_script_path_valid(tmp_path):
    """Test validation passes for valid executable script."""
    script = tmp_path / "test.sh"
    script.write_text("#!/bin/bash\necho test")
    os.chmod(script, 0o755)
    errors = infrastructure.validate_script_path(str(script), "test_component")
    assert len(errors) == 0


def test_list_infrastructure_components():
    """Test loading infrastructure components from config."""
    cfg = load_config()
    components = list_infrastructure_components(cfg)

    assert "cloudflared" in components
    assert "llm_controller" in components

    cloudflared = components["cloudflared"]
    assert cloudflared["type"] == "launchd_managed"
    assert cloudflared["enabled"] == True

    controller = components["llm_controller"]
    assert controller["type"] == "script_managed"
    assert controller["enabled"] == True


def test_get_infrastructure_component():
    """Test retrieving specific infrastructure component."""
    cfg = load_config()

    cloudflared = get_infrastructure_component(cfg, "cloudflared")
    assert cloudflared is not None
    assert cloudflared["type"] == "launchd_managed"

    controller = get_infrastructure_component(cfg, "llm_controller")
    assert controller is not None
    assert controller["type"] == "script_managed"

    # Non-existent component
    missing = get_infrastructure_component(cfg, "nonexistent")
    assert missing is None


@patch('subprocess.run')
def test_start_script_managed_component_success(mock_run, tmp_path):
    """Test starting script-managed component succeeds."""
    script = tmp_path / "controller.sh"
    script.write_text("#!/bin/bash\necho started")
    os.chmod(script, 0o755)

    component = {
        "name": "test_controller",
        "management_script": str(script)
    }

    mock_run.return_value = MagicMock(returncode=0, stdout="started", stderr="")

    success, msg = infrastructure.start_script_managed_component(component)
    assert success
    assert "started" in msg
    mock_run.assert_called_once()


@patch('subprocess.run')
def test_start_script_managed_component_failure(mock_run, tmp_path):
    """Test starting script-managed component handles failure."""
    script = tmp_path / "controller.sh"
    script.write_text("#!/bin/bash\nexit 1")
    os.chmod(script, 0o755)

    component = {
        "name": "test_controller",
        "management_script": str(script)
    }

    mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="failed to start")

    success, msg = infrastructure.start_script_managed_component(component)
    assert not success
    assert "failed" in msg.lower()


@patch('subprocess.run')
def test_stop_script_managed_component_success(mock_run, tmp_path):
    """Test stopping script-managed component succeeds."""
    script = tmp_path / "controller.sh"
    script.write_text("#!/bin/bash\necho stopped")
    os.chmod(script, 0o755)

    component = {
        "name": "test_controller",
        "management_script": str(script)
    }

    mock_run.return_value = MagicMock(returncode=0, stdout="stopped", stderr="")

    success, msg = infrastructure.stop_script_managed_component(component)
    assert success
    assert "stopped" in msg


@patch('subprocess.run')
def test_status_script_managed_component_running(mock_run, tmp_path):
    """Test status check for running script-managed component."""
    script = tmp_path / "controller.sh"
    script.write_text("#!/bin/bash\necho running")
    os.chmod(script, 0o755)

    component = {
        "name": "test_controller",
        "management_script": str(script)
    }

    mock_run.return_value = MagicMock(returncode=0, stdout="running: PID 12345", stderr="")

    running, status = infrastructure.status_script_managed_component(component)
    assert running
    assert "running" in status.lower()


@patch('subprocess.run')
def test_status_script_managed_component_not_running(mock_run, tmp_path):
    """Test status check for stopped script-managed component."""
    script = tmp_path / "controller.sh"
    script.write_text("#!/bin/bash\necho stopped")
    os.chmod(script, 0o755)

    component = {
        "name": "test_controller",
        "management_script": str(script)
    }

    mock_run.return_value = MagicMock(returncode=0, stdout="not running", stderr="")

    running, status = infrastructure.status_script_managed_component(component)
    assert not running
    assert "not running" in status.lower()


@patch('subprocess.run')
def test_start_launchd_managed_component_success(mock_run, tmp_path):
    """Test starting launchd-managed component succeeds."""
    installer = tmp_path / "install_cloudflared.sh"
    installer.write_text("#!/bin/bash\necho installed")
    os.chmod(installer, 0o755)

    component = {
        "name": "cloudflared",
        "installer_script": str(installer)
    }

    mock_run.return_value = MagicMock(returncode=0, stdout="cloudflared LaunchAgent installed and started.", stderr="")

    success, msg = infrastructure.start_launchd_managed_component(component)
    assert success
    assert "started" in msg.lower() or "installed" in msg.lower()


@patch('subprocess.run')
def test_stop_launchd_managed_component_success(mock_run):
    """Test stopping launchd-managed component succeeds."""
    component = {
        "name": "cloudflared",
        "launchd_label": "llms.tunnel"
    }

    mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

    success, msg = infrastructure.stop_launchd_managed_component(component)
    assert success
    assert msg == "stopped"


@patch('subprocess.run')
def test_status_launchd_managed_component_running(mock_run):
    """Test status check for running launchd-managed component."""
    component = {
        "name": "cloudflared",
        "launchd_label": "llms.tunnel"
    }

    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="12345\tllms.tunnel\n",
        stderr=""
    )

    running, status = infrastructure.status_launchd_managed_component(component)
    assert running
    assert "12345" in status or "running" in status.lower()


@patch('subprocess.run')
def test_status_launchd_managed_component_not_running(mock_run):
    """Test status check for stopped launchd-managed component."""
    component = {
        "name": "cloudflared",
        "launchd_label": "llms.tunnel"
    }

    mock_run.return_value = MagicMock(
        returncode=1,
        stdout="",
        stderr="Could not find service \"llms.tunnel\" in domain for port"
    )

    running, status = infrastructure.status_launchd_managed_component(component)
    assert not running
    assert "not loaded" in status.lower()


def test_get_log_path_cloudflared():
    """Test log path generation for cloudflared."""
    component = {
        "name": "cloudflared",
        "type": "launchd_managed",
        "log_dir": "~/llms/logs"
    }

    out_log = infrastructure.get_log_path(component, "out")
    err_log = infrastructure.get_log_path(component, "err")

    assert out_log is not None
    assert "cloudflared.out.log" in out_log
    assert err_log is not None
    assert "cloudflared.err.log" in err_log


def test_get_log_path_controller():
    """Test log path generation for controller."""
    component = {
        "name": "llm_controller",
        "type": "script_managed",
        "log_dir": "~/llms/logs"
    }

    out_log = infrastructure.get_log_path(component, "out")
    err_log = infrastructure.get_log_path(component, "err")

    assert out_log is not None
    assert "controller.out.log" in out_log
    assert err_log is not None
    assert "controller.err.log" in err_log


def test_get_log_path_no_log_dir():
    """Test log path returns None when no log directory configured."""
    component = {
        "name": "test",
        "type": "script_managed"
    }

    log_path = infrastructure.get_log_path(component)
    assert log_path is None


@patch('llamacpp_manager.infrastructure.start_script_managed_component')
def test_start_infrastructure_component_script_managed(mock_start):
    """Test unified start delegates to script-managed handler."""
    component = {
        "enabled": True,
        "type": "script_managed",
        "name": "controller"
    }

    mock_start.return_value = (True, "started")

    success, msg = infrastructure.start_infrastructure_component(component)
    assert success
    mock_start.assert_called_once_with(component)


@patch('llamacpp_manager.infrastructure.start_launchd_managed_component')
def test_start_infrastructure_component_launchd_managed(mock_start):
    """Test unified start delegates to launchd-managed handler."""
    component = {
        "enabled": True,
        "type": "launchd_managed",
        "name": "cloudflared"
    }

    mock_start.return_value = (True, "started")

    success, msg = infrastructure.start_infrastructure_component(component)
    assert success
    mock_start.assert_called_once_with(component)


def test_start_infrastructure_component_disabled():
    """Test starting disabled component returns error."""
    component = {
        "enabled": False,
        "type": "script_managed",
        "name": "disabled_component"
    }

    success, msg = infrastructure.start_infrastructure_component(component)
    assert not success
    assert "disabled" in msg.lower()


def test_start_infrastructure_component_unknown_type():
    """Test starting component with unknown type returns error."""
    component = {
        "enabled": True,
        "type": "unknown_type",
        "name": "invalid_component"
    }

    success, msg = infrastructure.start_infrastructure_component(component)
    assert not success
    assert "unknown" in msg.lower()
