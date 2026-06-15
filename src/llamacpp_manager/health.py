from __future__ import annotations

import http.client
import socket
import subprocess
import time
from typing import Any, Dict, Optional


def _http_get(host: str, port: int, path: str, timeout: float, headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """
    Perform HTTP GET request with optional custom headers.

    Business Purpose: Enables health checking of services that require
    authentication headers (like the LLM controller's X-API-Key).

    Args:
        host: Host to connect to
        port: Port to connect to
        path: URL path to request
        timeout: Timeout in seconds
        headers: Optional dict of headers to send

    Returns:
        Dict with status and body, or None on failure

    Example:
        result = _http_get("localhost", 8090, "/status", 2.0, {"X-API-Key": "secret"})
    """
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        if headers:
            conn.request("GET", path, headers=headers)
        else:
            conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read()
        return {"status": resp.status, "body": body}
    except Exception:
        return None
    finally:
        try:
            conn.close()  # type: ignore[name-defined]
        except Exception:
            pass


def check_endpoint(host: str, port: int, timeout_ms: int = 2000) -> Dict[str, Any]:
    """Return status dict: { up, latency_ms, http_status?, version?, health_state }.

    Enhanced health checking with detailed states like your old system:
    - 'ok': Server responding with 200 status
    - 'starting': Server loading or responding with 503/loading message
    - 'down': Server not reachable or not responding
    """
    timeout_s = max(0.1, timeout_ms / 1000.0)
    start = time.perf_counter()
    up = False
    http_status: Optional[int] = None
    version: Optional[str] = None
    health_state = "down"

    # TCP connect
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            up = True
    except Exception:
        up = False

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if up:
        # Check /health first (llama.cpp standard), then fallback paths
        for path in ("/health", "/v1/models", "/"):
            r = _http_get(host, port, path, timeout_s)
            if not r:
                continue

            http_status = r["status"]

            try:
                body = r["body"].decode("utf-8", errors="ignore").lower()

                # Determine health state based on response
                # Normalize body by removing whitespace for status check
                # (MLX server returns {"status": "ok"}, llama.cpp returns {"status":"ok"})
                normalized = body.replace(" ", "").replace("\n", "").replace("\t", "")
                if http_status == 200:
                    if '"status":"ok"' in normalized or "models" in body:
                        health_state = "ok"
                    elif "loading" in body or "initializing" in body:
                        health_state = "starting"
                elif http_status == 503 or "loading" in body or "initializing" in body:
                    health_state = "starting"
                else:
                    health_state = "down"

                # Version detection
                if "llama" in body and ("version" in body or "cpp" in body):
                    version = "llama.cpp"

            except Exception:
                # If we got a response but can't parse it, assume starting
                if http_status == 200:
                    health_state = "ok"
                elif http_status == 503:
                    health_state = "starting"

            break
    else:
        health_state = "down"

    return {
        "up": health_state in ["ok", "starting"],
        "latency_ms": elapsed_ms,
        "http_status": http_status,
        "version": version,
        "health_state": health_state,
    }


def check_infrastructure_component_health(component: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check health of an infrastructure component based on its configuration.

    Business Purpose: Provides unified health checking for infrastructure
    components with support for HTTP checks (with custom headers) and
    launchd process checks.

    Args:
        component: Infrastructure component configuration dictionary

    Returns:
        Dict with health status including:
        - healthy: bool indicating if component is healthy
        - status: str status message
        - latency_ms: int response time (for HTTP checks)
        - details: dict with additional health information

    Example:
        health = check_infrastructure_component_health(controller_config)
        if not health["healthy"]:
            print(f"Component unhealthy: {health['status']}")
    """
    health_check = component.get("health_check", {})
    check_type = health_check.get("type", "")

    if check_type == "http":
        # HTTP health check with optional custom headers
        endpoint = health_check.get("endpoint", "")
        if not endpoint:
            return {"healthy": False, "status": "no health check endpoint configured", "latency_ms": 0, "details": {}}

        # Parse endpoint URL
        try:
            # Simple parsing for http://host:port/path
            if endpoint.startswith("http://"):
                endpoint = endpoint[7:]
            elif endpoint.startswith("https://"):
                return {"healthy": False, "status": "https not supported for health checks", "latency_ms": 0, "details": {}}

            if "/" in endpoint:
                host_port, path = endpoint.split("/", 1)
                path = "/" + path
            else:
                host_port = endpoint
                path = "/"

            if ":" in host_port:
                host, port_str = host_port.rsplit(":", 1)
                port = int(port_str)
            else:
                host = host_port
                port = 80

        except Exception as e:
            return {"healthy": False, "status": f"invalid endpoint URL: {e}", "latency_ms": 0, "details": {}}

        # Perform HTTP check
        timeout_ms = health_check.get("timeout_ms", 5000)
        timeout_s = timeout_ms / 1000.0
        headers = health_check.get("headers", {})

        start = time.perf_counter()
        result = _http_get(host, port, path, timeout_s, headers=headers if headers else None)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if not result:
            return {"healthy": False, "status": "connection failed", "latency_ms": elapsed_ms, "details": {}}

        http_status = result["status"]
        expected_status = health_check.get("expected_status", 200)

        if http_status == expected_status:
            return {
                "healthy": True,
                "status": "ok",
                "latency_ms": elapsed_ms,
                "details": {"http_status": http_status}
            }
        else:
            return {
                "healthy": False,
                "status": f"unexpected status {http_status}",
                "latency_ms": elapsed_ms,
                "details": {"http_status": http_status, "expected": expected_status}
            }

    elif check_type == "launchd_process":
        # Check if launchd service is running
        label = component.get("launchd_label")
        if not label:
            return {"healthy": False, "status": "no launchd_label configured", "latency_ms": 0, "details": {}}

        try:
            import re
            import os
            result = subprocess.run(
                ["launchctl", "list", label],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse PID from plist-style output
                # Format: '"PID" = 84184;'
                output = result.stdout.strip()
                pid_match = re.search(r'"PID"\s*=\s*(\d+);', output)
                if pid_match:
                    pid = int(pid_match.group(1))
                    # Verify process is actually running
                    try:
                        os.kill(pid, 0)  # Check if PID exists
                        return {
                            "healthy": True,
                            "status": "running",
                            "latency_ms": 0,
                            "details": {"pid": pid, "launchd_label": label}
                        }
                    except ProcessLookupError:
                        return {
                            "healthy": False,
                            "status": "loaded but not running",
                            "latency_ms": 0,
                            "details": {"launchd_label": label}
                        }

                # No PID means not running
                return {
                    "healthy": False,
                    "status": "loaded but not running",
                    "latency_ms": 0,
                    "details": {"launchd_label": label}
                }
            else:
                return {
                    "healthy": False,
                    "status": "not loaded",
                    "latency_ms": 0,
                    "details": {"launchd_label": label}
                }

        except subprocess.TimeoutExpired:
            return {"healthy": False, "status": "launchctl timeout", "latency_ms": 0, "details": {}}
        except Exception as e:
            return {"healthy": False, "status": f"check failed: {e}", "latency_ms": 0, "details": {}}

    elif check_type == "process":
        # Simple process check (check if PID exists)
        # For script-managed components, we can check via their status command
        from . import infrastructure
        running, status_msg = infrastructure.get_infrastructure_status(component)
        return {
            "healthy": running,
            "status": status_msg,
            "latency_ms": 0,
            "details": {"running": running}
        }

    else:
        return {"healthy": False, "status": f"unknown health check type: {check_type}", "latency_ms": 0, "details": {}}

