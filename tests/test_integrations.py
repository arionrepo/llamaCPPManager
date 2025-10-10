# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/tests/test_integrations.py
# Description: Tests for IDE integration functionality (continue.dev)
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-10

"""
Tests for IDE Integrations

Business Purpose: Ensure that models are correctly synchronized with developer
IDEs like continue.dev for seamless coding assistance.
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from llamacpp_manager.integrations import (
    get_continue_config_path,
    read_continue_config,
    write_continue_config,
    add_model_to_continue,
    remove_model_from_continue,
    list_continue_models,
    sync_models_to_continue,
)


@pytest.fixture
def temp_continue_config(tmp_path):
    """Create temporary continue.dev config for testing."""
    config_dir = tmp_path / ".continue"
    config_dir.mkdir()
    config_path = config_dir / "config.json"

    # Mock get_continue_config_path to use temp directory
    with patch('llamacpp_manager.integrations.get_continue_config_path', return_value=config_path):
        yield config_path


def test_read_continue_config_not_exists(temp_continue_config):
    """Test reading config when file doesn't exist returns default structure."""
    config = read_continue_config()

    assert "models" in config
    assert "tabAutocompleteModel" in config
    assert config["models"] == []
    assert config["tabAutocompleteModel"] is None


def test_read_continue_config_exists(temp_continue_config):
    """Test reading existing config file."""
    # Write test config
    test_config = {
        "models": [
            {
                "title": "Test Model",
                "provider": "openai",
                "model": "test-model",
                "apiBase": "http://127.0.0.1:8080/v1",
                "apiKey": "not-needed"
            }
        ],
        "tabAutocompleteModel": None
    }

    with open(temp_continue_config, 'w') as f:
        json.dump(test_config, f)

    # Read config
    config = read_continue_config()

    assert len(config["models"]) == 1
    assert config["models"][0]["title"] == "Test Model"


def test_write_continue_config(temp_continue_config):
    """Test writing config to disk."""
    test_config = {
        "models": [
            {
                "title": "New Model",
                "provider": "openai",
                "model": "new-model",
                "apiBase": "http://127.0.0.1:8081/v1",
                "apiKey": "not-needed"
            }
        ],
        "tabAutocompleteModel": None
    }

    write_continue_config(test_config)

    # Verify file was written
    assert temp_continue_config.exists()

    # Verify content
    with open(temp_continue_config, 'r') as f:
        saved_config = json.load(f)

    assert saved_config["models"][0]["title"] == "New Model"


def test_add_model_to_continue_new(temp_continue_config):
    """Test adding a new model to continue.dev config."""
    was_added = add_model_to_continue("qwen-coder-7b", 8085)

    assert was_added is True

    # Verify model was added
    config = read_continue_config()
    assert len(config["models"]) == 1
    assert config["models"][0]["model"] == "qwen-coder-7b"
    assert config["models"][0]["apiBase"] == "http://127.0.0.1:8085/v1"
    assert config["models"][0]["title"] == "Qwen Coder 7B"


def test_add_model_to_continue_existing(temp_continue_config):
    """Test updating an existing model in continue.dev config."""
    # Add model first time
    add_model_to_continue("qwen-coder-7b", 8085)

    # Add same model with different port
    was_added = add_model_to_continue("qwen-coder-7b", 9999)

    assert was_added is False  # Model was updated, not added

    # Verify port was updated
    config = read_continue_config()
    assert len(config["models"]) == 1  # Still only one model
    assert config["models"][0]["apiBase"] == "http://127.0.0.1:9999/v1"


def test_add_model_to_continue_custom_title(temp_continue_config):
    """Test adding model with custom title."""
    add_model_to_continue("qwen-coder-7b", 8085, title="My Custom Model")

    config = read_continue_config()
    assert config["models"][0]["title"] == "My Custom Model"


def test_add_model_to_continue_custom_host(temp_continue_config):
    """Test adding model with custom host."""
    add_model_to_continue("qwen-coder-7b", 8085, host="192.168.1.100")

    config = read_continue_config()
    assert config["models"][0]["apiBase"] == "http://192.168.1.100:8085/v1"


def test_remove_model_from_continue_exists(temp_continue_config):
    """Test removing an existing model from continue.dev config."""
    # Add models
    add_model_to_continue("model-1", 8085)
    add_model_to_continue("model-2", 8086)

    # Remove one
    was_removed = remove_model_from_continue("model-1")

    assert was_removed is True

    # Verify only model-2 remains
    config = read_continue_config()
    assert len(config["models"]) == 1
    assert config["models"][0]["model"] == "model-2"


def test_remove_model_from_continue_not_exists(temp_continue_config):
    """Test removing a non-existent model returns False."""
    was_removed = remove_model_from_continue("non-existent")

    assert was_removed is False


def test_list_continue_models(temp_continue_config):
    """Test listing all models from continue.dev config."""
    # Add some models
    add_model_to_continue("model-1", 8085)
    add_model_to_continue("model-2", 8086)

    # List models
    models = list_continue_models()

    assert len(models) == 2
    assert models[0]["model"] == "model-1"
    assert models[1]["model"] == "model-2"


def test_sync_models_to_continue(temp_continue_config):
    """Test syncing multiple models from llamacpp-manager to continue.dev."""
    models_config = [
        {
            "name": "qwen-coder-7b",
            "port": 8085,
            "host": "127.0.0.1",
            "metadata": {
                "description": "Qwen Coder for coding tasks"
            }
        },
        {
            "name": "hermes-3-llama-8b",
            "port": 8086,
            "host": "127.0.0.1",
            "metadata": {
                "description": "Hermes 3 for agentic workflows"
            }
        },
        {
            "name": "invalid-model",
            # Missing port - should be skipped
        }
    ]

    count = sync_models_to_continue(models_config)

    # Only 2 valid models should be synced
    assert count == 2

    # Verify models were added
    config = read_continue_config()
    assert len(config["models"]) == 2


def test_read_continue_config_invalid_json(temp_continue_config):
    """Test reading config with invalid JSON returns default structure."""
    # Write invalid JSON
    with open(temp_continue_config, 'w') as f:
        f.write("{ invalid json }")

    config = read_continue_config()

    # Should return default structure instead of crashing
    assert "models" in config
    assert config["models"] == []
