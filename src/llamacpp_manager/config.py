import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from .utils import app_support_dir, config_path, logs_dir, ensure_dir, read_yaml, write_yaml


DEFAULT_LLAMA_SERVER_PATH = "/opt/homebrew/bin/llama-server"
DEFAULT_CLOUDFLARED_PATH = "/opt/homebrew/bin/cloudflared"
DEFAULT_CONTROLLER_SCRIPT = "~/llms/controller.sh"
DEFAULT_CLOUDFLARED_INSTALLER = "~/llms/install_cloudflared_launchagent.sh"


@dataclass
class ModelSpec:
    name: str
    model_path: str
    host: str = "127.0.0.1"
    port: int = 0
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    autostart: bool = False
    deployment_type: str = "native"  # "native" or "container"
    group: Optional[str] = None  # Model group name for mutual exclusion
    metadata: Optional[Dict[str, Any]] = None  # size_gb, ram_gb, use_case, etc.

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Normalize None lists/maps to empty for YAML clarity
        if d.get("args") is None:
            d["args"] = []
        if d.get("env") is None:
            d["env"] = {}
        if d.get("metadata") is None:
            d["metadata"] = {}
        # Don't include group if None
        if d.get("group") is None:
            del d["group"]
        return d


@dataclass
class InfrastructureComponentSpec:
    """
    Represents infrastructure component configuration.

    Business Purpose: Encapsulates settings for infrastructure components
    (cloudflared tunnel, LLM controller) that are managed via external scripts.
    """
    name: str
    enabled: bool
    type: str  # "launchd_managed" or "script_managed"
    management_script: Optional[str] = None
    installer_script: Optional[str] = None
    launchd_label: Optional[str] = None
    log_dir: Optional[str] = None
    health_check: Optional[Dict[str, Any]] = None
    autostart: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Clean up None values for YAML
        return {k: v for k, v in d.items() if v is not None}


def default_infrastructure_config() -> Dict[str, Any]:
    """
    Return default infrastructure configuration.

    Business Purpose: Provides sensible defaults for infrastructure components
    based on the user's actual setup with controller.sh and cloudflared.
    """
    home = str(Path.home())
    return {
        "cloudflared": {
            "enabled": True,
            "type": "launchd_managed",
            "launchd_label": "llms.tunnel",
            "installer_script": f"{home}/llms/install_cloudflared_launchagent.sh",
            "log_dir": f"{home}/llms/logs",
            "health_check": {
                "type": "launchd_process",
                "interval_seconds": 30
            },
            "autostart": True
        },
        "llm_controller": {
            "enabled": True,
            "type": "script_managed",
            "management_script": f"{home}/llms/controller.sh",
            "log_dir": f"{home}/llms/logs",
            "health_check": {
                "type": "http",
                "endpoint": "http://127.0.0.1:8090/status",
                "interval_seconds": 30,
                "timeout_ms": 5000,
                "headers": {
                    "X-API-Key": "choose-a-shared-key"
                }
            },
            "autostart": True
        }
    }


def default_config() -> Dict[str, Any]:
    return {
        "llama_server_path": DEFAULT_LLAMA_SERVER_PATH,
        "log_dir": str(logs_dir()),
        "timeout_ms": 2000,
        "models": [],
        "model_groups": {},  # Optional model groups with mutual exclusion
        "infrastructure": default_infrastructure_config(),
        "monitoring": {
            "enabled": True,
            "interval_seconds": 30,
            "alert_on_failure": True
        }
    }


def load_config() -> Dict[str, Any]:
    path = config_path()
    if not path.exists():
        return default_config()
    cfg = read_yaml(path)
    # Backfill defaults
    for k, v in default_config().items():
        cfg.setdefault(k, v)
    cfg.setdefault("models", [])
    cfg.setdefault("model_groups", {})
    cfg.setdefault("infrastructure", default_infrastructure_config())
    cfg.setdefault("monitoring", {"enabled": True, "interval_seconds": 30, "alert_on_failure": True})
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    ensure_dir(app_support_dir())
    write_yaml(config_path(), cfg)


def validate_port_unique(cfg: Dict[str, Any], port: int, *, ignore_name: Optional[str] = None) -> Optional[str]:
    for m in cfg.get("models", []):
        if ignore_name and m.get("name") == ignore_name:
            continue
        try:
            if int(m.get("port")) == int(port):
                return m.get("name") or "<unknown>"
        except Exception:
            continue
    return None


def validate_model(cfg: Dict[str, Any], model: ModelSpec, *, updating: bool = False) -> List[str]:
    errors: List[str] = []
    if not model.name:
        errors.append("name is required")
    if not model.model_path:
        errors.append("model_path is required")
    else:
        p = Path(os.path.expanduser(model.model_path))
        if not p.exists():
            errors.append(f"model_path not found: {p}")
    if not (1 <= int(model.port) <= 65535):
        errors.append("port must be in 1..65535")
    # Unique port check
    conflict = validate_port_unique(cfg, model.port, ignore_name=model.name if updating else None)
    if conflict:
        errors.append(f"port {model.port} already used by model '{conflict}'")
    return errors


def list_models(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(cfg.get("models", []))


def get_model(cfg: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for m in cfg.get("models", []):
        if m.get("name") == name:
            return m
    return None


def add_model(cfg: Dict[str, Any], model: ModelSpec) -> None:
    if get_model(cfg, model.name):
        raise ValueError(f"model '{model.name}' already exists")
    errs = validate_model(cfg, model)
    if errs:
        raise ValueError("; ".join(errs))
    cfg.setdefault("models", []).append(model.to_dict())


def update_model(cfg: Dict[str, Any], name: str, updates: Dict[str, Any]) -> None:
    m = get_model(cfg, name)
    if not m:
        raise ValueError(f"model '{name}' not found")
    merged = {**m, **{k: v for k, v in updates.items() if v is not None}}
    spec = ModelSpec(
        name=merged.get("name", name),
        model_path=merged["model_path"],
        host=merged.get("host", "127.0.0.1"),
        port=int(merged["port"]),
        args=list(merged.get("args", []) or []),
        env=dict(merged.get("env", {}) or {}),
        autostart=bool(merged.get("autostart", False)),
    )
    errs = validate_model(cfg, spec, updating=True)
    if errs:
        raise ValueError("; ".join(errs))
    # apply updates back to original dict
    m.clear()
    m.update(spec.to_dict())


def remove_model(cfg: Dict[str, Any], name: str) -> bool:
    models = cfg.get("models", [])
    for i, m in enumerate(models):
        if m.get("name") == name:
            del models[i]
            return True
    return False


# Infrastructure component management functions

def list_infrastructure_components(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    List all infrastructure components from configuration.

    Business Purpose: Provides access to infrastructure component definitions
    for display, management, and health monitoring.

    Args:
        cfg: Full configuration dictionary

    Returns:
        Dictionary mapping component name to component configuration (with 'name' field added)

    Example:
        components = list_infrastructure_components(config)
        cloudflared = components.get("cloudflared")
    """
    infra = cfg.get("infrastructure", {})
    # Add the name field to each component
    result = {}
    for name, comp in infra.items():
        comp_with_name = dict(comp)  # Make a copy
        comp_with_name["name"] = name
        result[name] = comp_with_name
    return result


def get_infrastructure_component(cfg: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific infrastructure component configuration.

    Business Purpose: Retrieves settings for a specific infrastructure
    component to enable start/stop/health check operations.

    Args:
        cfg: Full configuration dictionary
        name: Component name (e.g., "cloudflared", "llm_controller")

    Returns:
        Component configuration dictionary with 'name' field added, or None if not found

    Example:
        component = get_infrastructure_component(config, "cloudflared")
        if component and component.get("enabled"):
            # Start the component
    """
    infra = cfg.get("infrastructure", {})
    comp = infra.get(name)
    if comp:
        # Add the name to the component dict so functions can use it
        comp = dict(comp)  # Make a copy to avoid modifying original
        comp["name"] = name
    return comp


# Model group management functions

def list_model_groups(cfg: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    List all model groups from configuration.

    Business Purpose: Provides access to model group definitions
    for enforcing mutual exclusion and resource management.

    Args:
        cfg: Full configuration dictionary

    Returns:
        Dictionary mapping group name to group configuration

    Example:
        groups = list_model_groups(config)
        coding_group = groups.get("coding-models")
        if coding_group.get("exclusive"):
            # Only one model can run at a time
    """
    return cfg.get("model_groups", {})


def get_model_group(cfg: Dict[str, Any], group_name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific model group configuration.

    Business Purpose: Retrieves settings for a model group to enable
    exclusive launching and resource management.

    Args:
        cfg: Full configuration dictionary
        group_name: Group name (e.g., "coding-models")

    Returns:
        Group configuration dictionary or None if not found

    Example:
        group = get_model_group(config, "coding-models")
        if group and group.get("exclusive"):
            members = group.get("members", [])
            # Stop other members before starting new one
    """
    return cfg.get("model_groups", {}).get(group_name)


def get_model_group_for_model(cfg: Dict[str, Any], model_name: str) -> Optional[str]:
    """
    Find which group a model belongs to.

    Business Purpose: Identifies the exclusive group membership of a model
    to enable automatic stopping of sibling models.

    Args:
        cfg: Full configuration dictionary
        model_name: Name of model to check

    Returns:
        Group name if model is in a group, None otherwise

    Example:
        group_name = get_model_group_for_model(config, "qwen-coder-32b")
        if group_name:
            group = get_model_group(config, group_name)
            if group.get("exclusive"):
                # Stop siblings before starting this model
    """
    model = get_model(cfg, model_name)
    if model:
        return model.get("group")
    return None
