from __future__ import annotations

import http.client
import socket
import time
from typing import Any, Dict, Optional


def _http_get(host: str, port: int, path: str, timeout: float) -> Optional[Dict[str, Any]]:
    try:
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
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
                if http_status == 200:
                    if '"status":"ok"' in body or "models" in body:
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

