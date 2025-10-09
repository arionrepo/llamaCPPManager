# File: /Users/liborballaty/LocalProjects/GitHubProjectsDocuments/llamaCPPManager/tests/test_model_manager.py
# Description: Tests for unified model manager with exclusive groups
# Author: Libor Ballaty <libor@arionetworks.com>
# Created: 2025-10-07

import pytest
from unittest.mock import Mock, patch, MagicMock
from llamacpp_manager.model_manager import ModelManager, DeploymentType
from llamacpp_manager.config import ModelSpec


@pytest.fixture
def sample_config_with_groups():
    """Sample config with model groups."""
    return {
        "llama_server_path": "/usr/bin/llama-server",
        "log_dir": "/tmp/logs",
        "timeout_ms": 2000,
        "model_groups": {
            "coding-models": {
                "exclusive": True,
                "auto_stop_minutes": 120,
                "members": ["qwen-coder-32b", "qwen-coder-14b", "deepseek-lite"]
            }
        },
        "models": [
            {
                "name": "qwen-coder-32b",
                "model_path": "/models/qwen-32b.gguf",
                "host": "127.0.0.1",
                "port": 8090,
                "deployment_type": "native",
                "group": "coding-models",
                "args": [],
                "env": {},
                "autostart": False,
                "metadata": {
                    "size_gb": 35,
                    "ram_gb": 40,
                    "use_case": "Complex refactoring"
                }
            },
            {
                "name": "qwen-coder-14b",
                "model_path": "/models/qwen-14b.gguf",
                "host": "127.0.0.1",
                "port": 8091,
                "deployment_type": "native",
                "group": "coding-models",
                "args": [],
                "env": {},
                "autostart": False
            },
            {
                "name": "phi3",
                "model_path": "/models/phi3.gguf",
                "host": "127.0.0.1",
                "port": 8081,
                "deployment_type": "native",
                "args": [],
                "env": {},
                "autostart": False
            }
        ],
        "infrastructure": {},
        "monitoring": {"enabled": True, "interval_seconds": 30}
    }


@pytest.fixture
def model_manager(sample_config_with_groups):
    """Model manager with mocked config."""
    with patch('llamacpp_manager.model_manager.load_config', return_value=sample_config_with_groups):
        manager = ModelManager()
        return manager


def test_model_manager_initialization(model_manager):
    """Test ModelManager initializes correctly."""
    assert model_manager.config is not None
    assert "coding-models" in model_manager.model_groups
    assert model_manager.model_groups["coding-models"]["exclusive"] is True


def test_get_deployment_type_native(model_manager):
    """Test deployment type detection for native models."""
    model_config = model_manager.config["models"][0]
    dtype = model_manager._get_deployment_type(model_config)
    assert dtype == DeploymentType.NATIVE


def test_get_deployment_type_defaults_to_native(model_manager):
    """Test deployment type defaults to native if not specified."""
    model_config = {"name": "test", "model_path": "/test.gguf", "port": 9000}
    dtype = model_manager._get_deployment_type(model_config)
    assert dtype == DeploymentType.NATIVE


@patch('llamacpp_manager.model_manager.read_pid', side_effect=FileNotFoundError)
@patch('llamacpp_manager.model_manager.start_process', return_value=12345)
@patch('llamacpp_manager.model_manager.port_in_use', return_value=False)
@patch('llamacpp_manager.model_manager.write_pid')
def test_start_model_native(mock_write, mock_port, mock_start, mock_read_pid, model_manager):
    """Test starting a model with native deployment."""
    success, message = model_manager.start_model("phi3")

    assert success is True
    assert "started" in message
    mock_start.assert_called_once()


@patch('llamacpp_manager.model_manager.start_process', return_value=54321)
@patch('llamacpp_manager.model_manager.port_in_use', return_value=False)
@patch('llamacpp_manager.model_manager.stop_process')
@patch('llamacpp_manager.model_manager.write_pid')
def test_start_model_stops_siblings_in_exclusive_group(mock_write, mock_stop_proc, mock_port, mock_start, model_manager):
    """Test that starting a model in exclusive group stops siblings."""
    # Mock: qwen-32b is running, qwen-14b is not
    def mock_read_pid_lookup(model_name):
        if model_name == "qwen-coder-32b":
            return 12345  # Running
        raise FileNotFoundError  # Not running

    with patch('llamacpp_manager.model_manager.read_pid', side_effect=mock_read_pid_lookup):
        with patch('llamacpp_manager.model_manager.process_alive', return_value=True):
            # Start qwen-14b (should stop qwen-32b first)
            success, message = model_manager.start_model("qwen-coder-14b")

            # Should have stopped the sibling
            mock_stop_proc.assert_called_once()
            # Then started the requested model
            assert success is True


def test_start_model_not_found(model_manager):
    """Test starting a non-existent model."""
    success, message = model_manager.start_model("nonexistent")

    assert success is False
    assert "not found" in message


@patch('llamacpp_manager.model_manager.read_pid', return_value=12345)
@patch('llamacpp_manager.model_manager.process_alive', return_value=True)
@patch('llamacpp_manager.model_manager.stop_process')
def test_stop_model_native(mock_stop, mock_alive, mock_read, model_manager):
    """Test stopping a native model."""
    success, message = model_manager.stop_model("phi3")

    assert success is True
    mock_stop.assert_called_once()


@patch('llamacpp_manager.model_manager.read_pid', return_value=12345)
@patch('llamacpp_manager.model_manager.process_alive', return_value=True)
def test_get_active_models(mock_alive, mock_read, model_manager):
    """Test getting list of active models."""
    active = model_manager.get_active_models()

    # All models should appear as active (mocked PID)
    assert len(active) == 3
    assert all(model["deployment_type"] == "native" for model in active)


def test_get_group_active_model(model_manager):
    """Test getting active model in a group."""
    # Mock: qwen-32b is running, others are not
    def mock_read_pid_lookup(model_name):
        if model_name == "qwen-coder-32b":
            return 12345
        raise FileNotFoundError

    with patch('llamacpp_manager.model_manager.read_pid', side_effect=mock_read_pid_lookup):
        with patch('llamacpp_manager.model_manager.process_alive', return_value=True):
            active = model_manager.get_group_active_model("coding-models")
            assert active == "qwen-coder-32b"


@patch('llamacpp_manager.model_manager.read_pid', side_effect=FileNotFoundError)
def test_get_group_active_model_none_running(mock_read, model_manager):
    """Test getting active model when none are running."""
    active = model_manager.get_group_active_model("coding-models")
    assert active is None


def test_container_deployment_not_implemented(model_manager):
    """Test that container deployment returns not implemented."""
    model_config = {"name": "test", "deployment_type": "container"}
    success, message = model_manager._start_container(model_config)

    assert success is False
    assert "not yet implemented" in message
