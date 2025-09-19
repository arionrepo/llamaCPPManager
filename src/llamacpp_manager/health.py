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
    """Return status dict: { up, latency_ms, http_status?, version? }.

    Attempts TCP connect, then tries HTTP GET /v1/models and /.
    """
    timeout_s = max(0.1, timeout_ms / 1000.0)
    start = time.perf_counter()
    up = False
    http_status: Optional[int] = None
    version: Optional[str] = None

    # TCP connect
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            up = True
    except Exception:
        up = False

    elapsed_ms = int((time.perf_counter() - start) * 1000)

    if up:
        # attempt llama.cpp-friendly path first
        for path in ("/v1/models", "/"):
            r = _http_get(host, port, path, timeout_s)
            if not r:
                continue
            http_status = r["status"]
            # best-effort version sniffing
            try:
                b = r["body"].decode("utf-8", errors="ignore")
                if "llama" in b.lower() and "version" in b.lower():
                    version = "llama.cpp"
            except Exception:
                pass
            break

    return {
        "up": up,
        "latency_ms": elapsed_ms,
        "http_status": http_status,
        "version": version,
    }

