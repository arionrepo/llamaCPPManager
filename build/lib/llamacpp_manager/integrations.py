# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/src/llamacpp_manager/integrations.py
# Description: Integration with IDE tools like continue.dev for seamless model configuration
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-10

"""
IDE Integrations Module

Business Purpose: Automatically configure downloaded models in developer IDEs
like continue.dev, enabling developers to use local models immediately after
download without manual configuration.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


def get_continue_config_path() -> Path:
    """
    Get path to continue.dev configuration file.

    Business Purpose: Locate user's continue.dev config to enable automatic
    model registration. Prefers config.yaml over config.json.

    Returns:
        Path to ~/.continue/config.yaml (or config.json if yaml doesn't exist)

    Example:
        config_path = get_continue_config_path()
        # Returns: /Users/username/.continue/config.yaml
    """
    continue_dir = Path.home() / ".continue"
    yaml_path = continue_dir / "config.yaml"
    json_path = continue_dir / "config.json"

    # Prefer YAML if it exists
    if yaml_path.exists():
        return yaml_path
    return json_path


def read_continue_config() -> Dict[str, Any]:
    """
    Read existing continue.dev configuration.

    Business Purpose: Load current IDE configuration to preserve existing
    settings while adding new models. Supports both YAML and JSON formats.

    Returns:
        Dictionary with continue.dev config, or default structure if not exists

    Example:
        config = read_continue_config()
        existing_models = config.get("models", [])
    """
    config_path = get_continue_config_path()

    if not config_path.exists():
        # Return default structure
        return {
            "models": [],
            "tabAutocompleteModel": None
        }

    try:
        with open(config_path, 'r') as f:
            if config_path.suffix == '.yaml' or config_path.suffix == '.yml':
                return yaml.safe_load(f) or {}
            else:
                return json.load(f)
    except (json.JSONDecodeError, yaml.YAMLError, IOError):
        # Return default structure if file is invalid
        return {
            "models": [],
            "tabAutocompleteModel": None
        }


def write_continue_config(config: Dict[str, Any]) -> None:
    """
    Write continue.dev configuration to disk.

    Business Purpose: Persist model configuration so developers can
    immediately use newly downloaded models in their IDE. Preserves format (YAML/JSON).

    Args:
        config: Complete continue.dev configuration dictionary

    Example:
        config = read_continue_config()
        config["models"].append(new_model)
        write_continue_config(config)
    """
    config_path = get_continue_config_path()

    # Ensure directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Write with pretty formatting in the appropriate format
    with open(config_path, 'w') as f:
        if config_path.suffix == '.yaml' or config_path.suffix == '.yml':
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        else:
            json.dump(config, f, indent=2)


def add_model_to_continue(
    model_name: str,
    port: int,
    title: Optional[str] = None,
    host: str = "127.0.0.1"
) -> bool:
    """
    Add model to continue.dev configuration.

    Business Purpose: Automatically register newly configured models in
    continue.dev so developers can use them immediately for coding assistance.

    Args:
        model_name: Model identifier (e.g., "qwen-coder-7b")
        port: Port where model is running
        title: Display name in IDE (defaults to formatted model_name)
        host: Host where model is running (default: 127.0.0.1)

    Returns:
        True if model was added successfully, False if already exists

    Example:
        # After configuring a model on port 8084
        add_model_to_continue("qwen-coder-7b", 8084)
        # Model now appears in continue.dev model selector
    """
    # Read existing config
    config = read_continue_config()

    # Check if model already exists
    existing_models = config.get("models", [])
    for model in existing_models:
        # Check both 'model' and 'name' fields (YAML uses 'name', JSON uses 'model')
        model_id = model.get("model") or model.get("name")
        if model_id == model_name or model.get("apiBase", "").endswith(f":{port}/v1"):
            # Update existing model with new port
            model["apiBase"] = f"http://{host}:{port}/v1"
            write_continue_config(config)
            return False

    # Create display title
    if not title:
        # Convert "qwen-coder-7b" -> "Qwen Coder 7B"
        title = model_name.replace("-", " ").title()

    # Determine format based on config path
    config_path = get_continue_config_path()
    is_yaml = config_path.suffix in ['.yaml', '.yml']

    # Create new model entry (different format for YAML vs JSON)
    if is_yaml:
        new_model = {
            "name": title,
            "provider": "openai",
            "model": model_name,
            "apiBase": f"http://{host}:{port}/v1",
            "apiKey": "not-needed"
        }
    else:
        new_model = {
            "title": title,
            "provider": "openai",
            "model": model_name,
            "apiBase": f"http://{host}:{port}/v1",
            "apiKey": "not-needed"
        }

    # Add to models list
    if "models" not in config:
        config["models"] = []
    config["models"].append(new_model)

    # Write updated config
    write_continue_config(config)
    return True


def remove_model_from_continue(model_name: str) -> bool:
    """
    Remove model from continue.dev configuration.

    Business Purpose: Clean up IDE configuration when models are removed
    to avoid showing unavailable models to developers.

    Args:
        model_name: Model identifier to remove

    Returns:
        True if model was removed, False if not found

    Example:
        remove_model_from_continue("old-model")
        # Model no longer appears in continue.dev
    """
    # Read existing config
    config = read_continue_config()

    # Filter out the model
    original_models = config.get("models", [])
    filtered_models = [m for m in original_models if m.get("model") != model_name]

    # Check if anything was removed
    if len(filtered_models) == len(original_models):
        return False

    config["models"] = filtered_models
    write_continue_config(config)
    return True


def list_continue_models() -> List[Dict[str, Any]]:
    """
    List all models configured in continue.dev.

    Business Purpose: Show developers which models are available in their
    IDE for debugging and verification purposes.

    Returns:
        List of model configurations

    Example:
        models = list_continue_models()
        for model in models:
            print(f"{model['title']} at {model['apiBase']}")
    """
    config = read_continue_config()
    return config.get("models", [])


def sync_models_to_continue(models_config: List[Dict[str, Any]]) -> int:
    """
    Sync all configured models to continue.dev.

    Business Purpose: Ensure IDE configuration matches llamacpp-manager
    configuration for consistent developer experience.

    Args:
        models_config: List of model configurations from llamacpp-manager

    Returns:
        Number of models added/updated

    Example:
        from llamacpp_manager.config import list_models
        cfg = load_config()
        models = list_models(cfg)
        count = sync_models_to_continue(models)
        print(f"Synced {count} models to continue.dev")
    """
    count = 0

    for model in models_config:
        name = model.get("name")
        port = model.get("port")
        host = model.get("host", "127.0.0.1")

        if name and port:
            # Get display title from metadata if available
            metadata = model.get("metadata", {})
            title = metadata.get("description", None)

            add_model_to_continue(name, port, title=title, host=host)
            count += 1

    return count
