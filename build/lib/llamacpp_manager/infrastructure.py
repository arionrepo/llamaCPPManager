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
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def get_process_uptime(pid: int) -> Optional[str]:
    """
    Get human-readable uptime for a process.

    Business Purpose: Shows how long a component has been running,
    useful for monitoring stability and recent restarts.

    Args:
        pid: Process ID

    Returns:
        Uptime string like "2d 5h 30m" or None if process not found

    Example:
        uptime = get_process_uptime(12345)
        # Returns: "1h 23m"
    """
    try:
        # Get process start time using ps
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "etime="],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            # ps etime format: "[[dd-]hh:]mm:ss" or similar
            # We'll just return it as-is, it's already human-readable
            uptime = result.stdout.strip()
            return uptime if uptime else None
    except Exception:
        pass
    return None


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


def get_port_from_component(component: Dict[str, Any]) -> Optional[int]:
    """
    Extract port number from component health check configuration.

    Business Purpose: Identifies which port a component uses so we can
    detect and clear hung processes before starting.

    Args:
        component: Component configuration dictionary

    Returns:
        Port number if found, None otherwise

    Example:
        port = get_port_from_component(controller_config)
        # Returns: 8090
    """
    health_check = component.get("health_check", {})
    endpoint = health_check.get("endpoint", "")

    # Extract port from endpoint URL like "http://127.0.0.1:8090/status"
    match = re.search(r':(\d+)/', endpoint)
    if match:
        return int(match.group(1))
    return None


def find_process_using_port(port: int) -> Optional[int]:
    """
    Find PID of process listening on a specific port.

    Business Purpose: Detects hung processes that are blocking a port
    so they can be killed before starting a new instance.

    Args:
        port: Port number to check

    Returns:
        PID of process using the port, or None if port is free

    Example:
        pid = find_process_using_port(8090)
        if pid:
            print(f"Port 8090 is used by PID {pid}")
    """
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            # May return multiple PIDs, take the first one
            pids = result.stdout.strip().split('\n')
            return int(pids[0])
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        pass
    return None


def kill_process_force(pid: int, component_name: str) -> Tuple[bool, str]:
    """
    Force-kill a process that's blocking a component's port.

    Business Purpose: Clears hung processes that prevent infrastructure
    components from starting cleanly.

    Args:
        pid: Process ID to kill
        component_name: Name of component for logging

    Returns:
        Tuple of (success: bool, message: str)

    Example:
        success, msg = kill_process_force(12345, "llm_controller")
        print(f"Kill result: {msg}")
    """
    try:
        # Try graceful termination first
        os.kill(pid, signal.SIGTERM)

        # Wait briefly for process to exit
        import time
        for _ in range(10):
            try:
                os.kill(pid, 0)  # Check if still alive
                time.sleep(0.2)
            except ProcessLookupError:
                return True, f"killed hung process {pid}"

        # Force kill if still alive
        try:
            os.kill(pid, signal.SIGKILL)
            return True, f"force-killed hung process {pid}"
        except ProcessLookupError:
            return True, f"killed hung process {pid}"

    except ProcessLookupError:
        return True, f"process {pid} already gone"
    except PermissionError:
        return False, f"no permission to kill process {pid}"
    except Exception as e:
        return False, f"failed to kill {pid}: {e}"


def clear_hung_process_on_port(component: Dict[str, Any]) -> Optional[str]:
    """
    Check for and kill any hung process using a component's port.

    Business Purpose: Automatically clears port conflicts before starting
    infrastructure components, preventing "address already in use" errors.

    Args:
        component: Component configuration dictionary

    Returns:
        Warning message if process was killed, None otherwise

    Example:
        warning = clear_hung_process_on_port(controller_config)
        if warning:
            print(f"Warning: {warning}")
    """
    port = get_port_from_component(component)
    if not port:
        return None

    pid = find_process_using_port(port)
    if not pid:
        return None

    component_name = component.get("name", "component")
    success, msg = kill_process_force(pid, component_name)

    if success:
        return f"cleared hung process on port {port}: {msg}"
    else:
        return f"failed to clear port {port}: {msg}"


def start_script_managed_component(component: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Start a script-managed infrastructure component.

    Business Purpose: Starts components like LLM controller by invoking
    their management script's start command. Automatically clears any
    hung processes blocking the component's port first.

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

    # Check for and clear any hung process on the port
    warning = clear_hung_process_on_port(component)
    warning_msg = f" ({warning})" if warning else ""

    try:
        result = subprocess.run(
            [expanded, "start"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            msg = result.stdout.strip() or "started"
            return True, msg + warning_msg
        else:
            return False, result.stderr.strip() or f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "start command timed out after 30s"
    except Exception as e:
        return False, f"failed to start: {e}"


def stop_script_managed_component(component: Dict[str, Any], force: bool = False) -> Tuple[bool, str]:
    """
    Stop a script-managed infrastructure component.

    Business Purpose: Stops components like LLM controller by invoking
    their management script's stop command. If the stop command fails
    or if force=True, kills any process on the component's port.

    Args:
        component: Component configuration dictionary
        force: If True, force-kill process on port regardless of script result

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

    # If force mode, just kill the process on the port
    if force:
        warning = clear_hung_process_on_port(component)
        if warning:
            return True, warning
        else:
            return True, "no process found on port"

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
            # Stop script failed, try to force-kill process on port as fallback
            warning = clear_hung_process_on_port(component)
            if warning:
                return True, f"stop script failed, but {warning}"
            else:
                return False, result.stderr.strip() or f"exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        # Timeout, try to force-kill process on port as fallback
        warning = clear_hung_process_on_port(component)
        if warning:
            return True, f"stop timed out, but {warning}"
        else:
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

            # Parse PID from plist-style output
            # Format: '"PID" = 84184;'
            pid_match = re.search(r'"PID"\s*=\s*(\d+);', output)
            if pid_match:
                pid = int(pid_match.group(1))
                # Verify process is actually running
                try:
                    os.kill(pid, 0)  # Check if PID exists
                    return True, f"running (PID {pid})"
                except ProcessLookupError:
                    return True, "loaded but not running"

            # Check if PID is missing (means not running)
            if '"PID"' not in output:
                return True, "loaded but not running"

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
