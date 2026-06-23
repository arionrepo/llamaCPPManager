import json
import sys
from typing import Any, Dict, Generator, Optional
from pathlib import Path

import httpx
from .config import load_config
from .health import check_endpoint


class ModelQueryError(Exception):
    pass


def get_model_endpoint(name: str) -> tuple[str, int]:
    # First try to find in config (native models)
    cfg = load_config()
    models = cfg.get("models", [])
    model = next((m for m in models if m.get("name") == name), None)
    if model:
        host = model.get("host", "127.0.0.1")
        port = int(model.get("port"))
        return host, port

    # If not in config, check if it's a Docker container
    from .docker_manager import DockerManager
    docker_mgr = DockerManager()

    # Check if model name matches a Docker container
    if name in docker_mgr.port_map:
        return "127.0.0.1", docker_mgr.port_map[name]

    # Also try adding "llm-" prefix if not already present
    if not name.startswith("llm-"):
        docker_name = f"llm-{name}"
        if docker_name in docker_mgr.port_map:
            return "127.0.0.1", docker_mgr.port_map[docker_name]

    raise ModelQueryError(f"Model '{name}' not found in config or Docker containers")


def check_model_available(name: str, timeout_ms: int = 5000) -> bool:
    try:
        host, port = get_model_endpoint(name)
        health = check_endpoint(host, port, timeout_ms=timeout_ms)
        return bool(health.get("up"))
    except Exception:
        return False


def query_model_completion(
    name: str,
    prompt: str,
    max_tokens: int = 512,
    temperature: float = 0.7,
    stream: bool = False,
    timeout: float = 90.0,  # Docker containers need extra time for first query
    **kwargs: Any
) -> Dict[str, Any] | Generator[Dict[str, Any], None, None]:
    if not check_model_available(name):
        raise ModelQueryError(f"Model '{name}' is not running or not reachable")

    host, port = get_model_endpoint(name)
    url = f"http://{host}:{port}/completion"

    payload = {
        "prompt": prompt,
        "n_predict": max_tokens,
        "temperature": temperature,
        "stream": stream,
        **kwargs
    }

    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            if stream:
                return _stream_completion(client, url, payload)
            else:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
    except httpx.RequestError as e:
        raise ModelQueryError(f"Failed to connect to model '{name}': {e}")
    except httpx.HTTPStatusError as e:
        raise ModelQueryError(f"Model '{name}' returned error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise ModelQueryError(f"Failed to query model '{name}': {e}")


def _stream_completion(client: httpx.Client, url: str, payload: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    with client.stream("POST", url, json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: "):
                try:
                    data = json.loads(line[6:])
                    yield data
                except json.JSONDecodeError:
                    continue


def query_model_chat(
    name: str,
    messages: list[Dict[str, str]],
    max_tokens: int = 512,
    temperature: float = 0.7,
    stream: bool = False,
    timeout: float = 90.0,  # Docker containers need extra time for first query
    **kwargs: Any
) -> Dict[str, Any] | Generator[Dict[str, Any], None, None]:
    if not check_model_available(name):
        raise ModelQueryError(f"Model '{name}' is not running or not reachable")

    host, port = get_model_endpoint(name)
    url = f"http://{host}:{port}/v1/chat/completions"

    payload: Dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": stream,
        **kwargs
    }

    # mlx_vlm.server requires a 'model' field (required in its ChatRequest schema);
    # standard llama.cpp and mlx-lm servers don't need it.
    cfg = load_config()
    _model_cfg = next((m for m in cfg.get("models", []) if m.get("name") == name), None)
    if _model_cfg and _model_cfg.get("deployment_type") == "mlx-vlm":
        payload.setdefault("model", _model_cfg.get("model_path", name))

    try:
        with httpx.Client(timeout=timeout, trust_env=False) as client:
            if stream:
                return _stream_chat(client, url, payload)
            else:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return response.json()
    except httpx.RequestError as e:
        raise ModelQueryError(f"Failed to connect to model '{name}': {e}")
    except httpx.HTTPStatusError as e:
        raise ModelQueryError(f"Model '{name}' returned error {e.response.status_code}: {e.response.text}")
    except Exception as e:
        raise ModelQueryError(f"Failed to query model '{name}': {e}")


def _stream_chat(client: httpx.Client, url: str, payload: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    with client.stream("POST", url, json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith("data: "):
                data_str = line[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    yield data
                except json.JSONDecodeError:
                    continue


def list_available_models() -> list[str]:
    cfg = load_config()
    models = cfg.get("models", [])
    available = []

    for model in models:
        name = model.get("name")
        if name and check_model_available(name, timeout_ms=1000):
            available.append(name)

    return available