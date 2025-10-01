# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/infrastructure.py
# Description: Infrastructure component lifecycle management for cloudflared and controller
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-01

"""
Infrastructure component lifecycle management.

Business Purpose: Manages critical infrastructure components (cloudflared tunnel
and LLM controller) by wrapping existing management scripts and providing unified
status, control, and monitoring capabilities.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def expand_path(path: str) -> str:
    """
    Expand ~ and environment variables in path.

    Business Purpose: Converts user-friendly paths with ~ notation
    to absolute paths for reliable script execution.

    Args:
        path: Path potentially containing ~ or environment variables

    Returns:
        Expanded absolute path string

    Example:
        expanded = expand_path("~/llms/controller.sh")
        # Returns: "/Users/username/llms/controller.sh"
    """
    return os.path.expanduser(os.path.expandvars(path))


def validate_script_path(path: str, component_name: str) -> List[str]:
    """
    Validate that a management script exists and is executable.

    Business Purpose: Prevents runtime errors by validating script
    paths during configuration or startup.

    Args:
        path: Path to script file
        component_name: Name of component for error messages

    Returns:
        List of error messages (empty if valid)

    Example:
        errors = validate_script_path("~/llms/controller.sh", "llm_controller")
        if errors:
            print(f"Configuration error: {'; '.join(errors)}")
    """
    errors: List[str] = []
    expanded = expand_path(path)
    script_path = Path(expanded)

    if not script_path.exists():
        errors.append(f"{component_name}: script not found at {expanded}")
    elif not os.access(script_path, os.X_OK):
        errors.append(f"{component_name}: script not executable: {expanded}")

    return errors


def start_script_managed_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Start a script-managed infrastructure component.

    Business Purpose: Starts components like LLM controller by invoking
    their management script's start command.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = start_script_managed_component(controller_config)
        if success:
            print(f"Started: {msg}")
        else:
            print(f"Failed: {msg}", file=sys.stderr)
    """
    script = component.get("management_script")
    if not script:
        return False, "no management_script configured"

    expanded = expand_path(script)
    errors = validate_script_path(script, component.get("name", "component"))
    if errors:
        return False, "; ".join(errors)

    try:
        result = subprocess.run(
            [expanded, "start"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "started"
        else:
            return False, result.stderr.strip() or f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "start command timed out after 30s"
    except Exception as e:
        return False, f"failed to start: {e}"


def stop_script_managed_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Stop a script-managed infrastructure component.

    Business Purpose: Stops components like LLM controller by invoking
    their management script's stop command.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = stop_script_managed_component(controller_config)
        if success:
            print(f"Stopped: {msg}")
    """
    script = component.get("management_script")
    if not script:
        return False, "no management_script configured"

    expanded = expand_path(script)
    errors = validate_script_path(script, component.get("name", "component"))
    if errors:
        return False, "; ".join(errors)

    try:
        result = subprocess.run(
            [expanded, "stop"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "stopped"
        else:
            return False, result.stderr.strip() or f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "stop command timed out after 30s"
    except Exception as e:
        return False, f"failed to stop: {e}"


def status_script_managed_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Get status of a script-managed infrastructure component.

    Business Purpose: Checks component status by invoking management
    script's status command.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (running: bool, status_message: str)

    Example:
        running, status = status_script_managed_component(controller_config)
        print(f"Controller: {status}")
    """
    script = component.get("management_script")
    if not script:
        return False, "no management_script configured"

    expanded = expand_path(script)
    if not Path(expanded).exists():
        return False, f"script not found: {expanded}"

    try:
        result = subprocess.run(
            [expanded, "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        output = result.stdout.strip()
        # Parse status output to determine if running
        running = "running" in output.lower() and "not running" not in output.lower()
        return running, output or "status unknown"
    except subprocess.TimeoutExpired:
        return False, "status check timed out"
    except Exception as e:
        return False, f"failed to check status: {e}"


def start_launchd_managed_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Start a launchd-managed infrastructure component.

    Business Purpose: Starts components like cloudflared by running their
    installer script which creates and loads the launchd agent.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = start_launchd_managed_component(cloudflared_config)
        if success:
            print(f"Cloudflared tunnel started via launchd: {msg}")
    """
    installer = component.get("installer_script")
    if not installer:
        return False, "no installer_script configured"

    expanded = expand_path(installer)
    errors = validate_script_path(installer, component.get("name", "component"))
    if errors:
        return False, "; ".join(errors)

    try:
        result = subprocess.run(
            [expanded],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return True, result.stdout.strip() or "started via launchd"
        else:
            return False, result.stderr.strip() or f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "installer script timed out after 60s"
    except Exception as e:
        return False, f"failed to run installer: {e}"


def stop_launchd_managed_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Stop a launchd-managed infrastructure component.

    Business Purpose: Stops components like cloudflared by unloading
    their launchd agent.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = stop_launchd_managed_component(cloudflared_config)
        if success:
            print(f"Cloudflared tunnel stopped: {msg}")
    """
    label = component.get("launchd_label")
    if not label:
        return False, "no launchd_label configured"

    uid = os.getuid()
    domain = f"gui/{uid}/{label}"

    try:
        result = subprocess.run(
            ["launchctl", "bootout", domain],
            capture_output=True,
            text=True,
            timeout=30
        )
        # bootout returns 0 even if agent wasn't loaded, which is fine
        return True, "stopped"
    except subprocess.TimeoutExpired:
        return False, "launchctl bootout timed out"
    except Exception as e:
        return False, f"failed to stop: {e}"


def status_launchd_managed_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Get status of a launchd-managed infrastructure component.

    Business Purpose: Checks if launchd agent is loaded and running.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (running: bool, status_message: str)

    Example:
        running, status = status_launchd_managed_component(cloudflared_config)
        print(f"Cloudflared: {status}")
    """
    label = component.get("launchd_label")
    if not label:
        return False, "no launchd_label configured"

    try:
        result = subprocess.run(
            ["launchctl", "list", label],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            # Agent is loaded
            output = result.stdout.strip()
            # Parse PID from output - launchctl list shows PID in first column
            # Format: "PID    Status    Label"
            # Or:     "12345  0         llms.tunnel"
            lines = output.split("\n")
            for line in lines:
                parts = line.split()
                if len(parts) >= 1:
                    # First token should be PID or "-" if not running
                    pid_str = parts[0].strip()
                    if pid_str != "-" and pid_str.isdigit():
                        try:
                            pid = int(pid_str)
                            return True, f"running (PID {pid})"
                        except ValueError:
                            pass
            return True, "loaded (status unknown)"
        else:
            return False, "not loaded"
    except subprocess.TimeoutExpired:
        return False, "launchctl list timed out"
    except Exception as e:
        return False, f"failed to check status: {e}"


def start_infrastructure_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Start an infrastructure component (delegates to appropriate method).

    Business Purpose: Provides unified start interface that automatically
    selects the correct start method based on component type.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = start_infrastructure_component(component)
        if not success:
            print(f"Error: {msg}", file=sys.stderr)
    """
    if not component.get("enabled", True):
        return False, "component is disabled in config"

    component_type = component.get("type", "")
    if component_type == "script_managed":
        return start_script_managed_component(component)
    elif component_type == "launchd_managed":
        return start_launchd_managed_component(component)
    else:
        return False, f"unknown component type: {component_type}"


def stop_infrastructure_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Stop an infrastructure component (delegates to appropriate method).

    Business Purpose: Provides unified stop interface that automatically
    selects the correct stop method based on component type.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = stop_infrastructure_component(component)
    """
    component_type = component.get("type", "")
    if component_type == "script_managed":
        return stop_script_managed_component(component)
    elif component_type == "launchd_managed":
        return stop_launchd_managed_component(component)
    else:
        return False, f"unknown component type: {component_type}"


def get_infrastructure_status(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Get status of an infrastructure component (delegates to appropriate method).

    Business Purpose: Provides unified status interface that automatically
    selects the correct status check method based on component type.

    Args:
        component: Component configuration dictionary

    Returns:
        Tuple of (running: bool, status_message: str)

    Example:
        running, status = get_infrastructure_status(component)
        print(f"{component['name']}: {status}")
    """
    component_type = component.get("type", "")
    if component_type == "script_managed":
        return status_script_managed_component(component)
    elif component_type == "launchd_managed":
        return status_launchd_managed_component(component)
    else:
        return False, f"unknown component type: {component_type}"


def get_log_path(component: Dict[str, Any], log_type: str = "out") -> Optional[str]:
    """
    Get log file path for an infrastructure component.

    Business Purpose: Provides log file paths so users can view component
    logs for troubleshooting.

    Args:
        component: Component configuration dictionary
        log_type: "out" for stdout, "err" for stderr

    Returns:
        Absolute path to log file or None if not configured

    Example:
        log_path = get_log_path(cloudflared_config, "err")
        if log_path:
            subprocess.run(["tail", "-f", log_path])
    """
    log_dir = component.get("log_dir")
    if not log_dir:
        return None

    name = component.get("name", "component")
    component_type = component.get("type", "")

    expanded_dir = expand_path(log_dir)

    # Determine log filename based on component
    if component_type == "launchd_managed" and name == "cloudflared":
        filename = f"cloudflared.{log_type}.log"
    elif component_type == "script_managed" and "controller" in name.lower():
        filename = f"controller.{log_type}.log"
    else:
        filename = f"{name}.{log_type}.log"

    return os.path.join(expanded_dir, filename)
