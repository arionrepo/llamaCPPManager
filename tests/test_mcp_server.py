import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import tempfile
import yaml
from pathlib import Path

from llamacpp_manager.mcp_server import (
    app,
    handle_list_models,
    handle_list_available_models,
    handle_start_model,
    handle_stop_model,
    handle_model_status,
    handle_query_completion,
    handle_query_chat,
    handle_add_model,
    handle_remove_model,
    StartModelInput,
    StopModelInput,
    ModelStatusInput,
    QueryCompletionInput,
    QueryChatInput,
    AddModelInput,
    RemoveModelInput
)


@pytest.fixture
def temp_config_mcp():
    """Create a temporary config for MCP testing"""
    config_data = {
        "llama_server_path": "/opt/homebrew/bin/llama-server",
        "log_dir": "/tmp/llamacpp-logs",
        "timeout_ms": 2000,
        "models": [
            {
                "name": "test-model",
                "model_path": "/path/to/model.gguf",
                "host": "127.0.0.1",
                "port": 8080,
                "autostart": True
            },
            {
                "name": "chat-model",
                "model_path": "/path/to/chat.gguf",
                "host": "127.0.0.1",
                "port": 8081,
                "autostart": False
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name

    with patch('llamacpp_manager.mcp_server.load_config') as mock_load:
        mock_load.return_value = config_data
        yield config_data

    Path(config_path).unlink(missing_ok=True)


class TestMCPServerTools:
    """Unit tests for MCP server tool registration"""

    def test_server_creation(self):
        """Test that the MCP server can be created"""
        assert app is not None
        assert app.name == "llamacpp-manager"


class TestMCPHandlerFunctions:
    """Unit tests for individual MCP handler functions"""

    @pytest.mark.asyncio
    async def test_handle_list_models(self, temp_config_mcp):
        """Test listing all models"""
        result = await handle_list_models()

        assert len(result) == 1
        assert result[0].type == "text"
        assert "test-model" in result[0].text
        assert "chat-model" in result[0].text
        assert "127.0.0.1:8080" in result[0].text
        assert "127.0.0.1:8081" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_list_models_empty_config(self):
        """Test listing models with empty config"""
        with patch('llamacpp_manager.mcp_server.load_config') as mock_load:
            mock_load.return_value = {"models": []}

            result = await handle_list_models()

            assert len(result) == 1
            assert "No models configured" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_list_available_models(self, temp_config_mcp):
        """Test listing available models"""
        with patch('llamacpp_manager.mcp_server.list_available_models') as mock_list:
            mock_list.return_value = ["test-model"]

            result = await handle_list_available_models()

            assert len(result) == 1
            assert "Available models:" in result[0].text
            assert "test-model" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_list_available_models_none(self, temp_config_mcp):
        """Test listing available models when none are available"""
        with patch('llamacpp_manager.mcp_server.list_available_models') as mock_list:
            mock_list.return_value = []

            result = await handle_list_available_models()

            assert len(result) == 1
            assert "No models are currently available" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_start_model_direct(self, temp_config_mcp):
        """Test starting a model in direct mode"""
        input_data = StartModelInput(model_name="test-model", mode="direct")

        with patch('llamacpp_manager.mcp_server.start_process') as mock_start, \
             patch('llamacpp_manager.mcp_server.write_pid') as mock_write_pid:

            mock_start.return_value = 12345

            result = await handle_start_model(input_data)

            assert len(result) == 1
            assert "Started test-model directly with PID 12345" in result[0].text
            mock_start.assert_called_once()
            mock_write_pid.assert_called_once_with("test-model", 12345)

    @pytest.mark.asyncio
    async def test_handle_start_model_not_found(self, temp_config_mcp):
        """Test starting a model that doesn't exist"""
        input_data = StartModelInput(model_name="nonexistent-model")

        result = await handle_start_model(input_data)

        assert len(result) == 1
        assert "not found in configuration" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_stop_model_direct(self, temp_config_mcp):
        """Test stopping a model in direct mode"""
        input_data = StopModelInput(model_name="test-model", mode="direct")

        with patch('llamacpp_manager.mcp_server.read_pid') as mock_read_pid, \
             patch('llamacpp_manager.mcp_server.stop_process') as mock_stop, \
             patch('llamacpp_manager.mcp_server.remove_pid') as mock_remove_pid:

            mock_read_pid.return_value = 12345

            result = await handle_stop_model(input_data)

            assert len(result) == 1
            assert "Stopped test-model (PID 12345)" in result[0].text
            mock_stop.assert_called_once_with(12345)
            mock_remove_pid.assert_called_once_with("test-model")

    @pytest.mark.asyncio
    async def test_handle_stop_model_no_pid(self, temp_config_mcp):
        """Test stopping a model with no PID file"""
        input_data = StopModelInput(model_name="test-model", mode="direct")

        with patch('llamacpp_manager.mcp_server.read_pid') as mock_read_pid:
            mock_read_pid.side_effect = FileNotFoundError()

            result = await handle_stop_model(input_data)

            assert len(result) == 1
            assert "No PID file found for test-model" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_model_status_single(self, temp_config_mcp):
        """Test getting status for a single model"""
        input_data = ModelStatusInput(model_name="test-model")

        with patch('llamacpp_manager.mcp_server.read_pid') as mock_read_pid, \
             patch('llamacpp_manager.mcp_server.process_alive') as mock_alive, \
             patch('llamacpp_manager.mcp_server.check_endpoint') as mock_check:

            mock_read_pid.return_value = 12345
            mock_alive.return_value = True
            mock_check.return_value = {"up": True, "latency_ms": 50}

            result = await handle_model_status(input_data)

            assert len(result) == 1
            assert "test-model: UP (direct) PID=12345" in result[0].text
            assert "latency=50ms" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_model_status_all(self, temp_config_mcp):
        """Test getting status for all models"""
        input_data = ModelStatusInput()  # No specific model

        with patch('llamacpp_manager.mcp_server.read_pid') as mock_read_pid, \
             patch('llamacpp_manager.mcp_server.process_alive') as mock_alive, \
             patch('llamacpp_manager.mcp_server.check_endpoint') as mock_check:

            mock_read_pid.side_effect = [12345, FileNotFoundError()]
            mock_alive.return_value = True
            mock_check.side_effect = [
                {"up": True, "latency_ms": 50},
                {"up": False}
            ]

            result = await handle_model_status(input_data)

            assert len(result) == 1
            assert "test-model: UP (direct)" in result[0].text
            assert "chat-model: DOWN (stopped)" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_query_completion(self, temp_config_mcp):
        """Test query completion"""
        input_data = QueryCompletionInput(
            model_name="test-model",
            prompt="Hello world",
            max_tokens=100,
            temperature=0.8
        )

        with patch('llamacpp_manager.mcp_server.check_model_available') as mock_check, \
             patch('llamacpp_manager.mcp_server.query_model_completion') as mock_query:

            mock_check.return_value = True
            mock_query.return_value = {"content": "Hello! This is a test response."}

            result = await handle_query_completion(input_data)

            assert len(result) == 1
            assert "Hello! This is a test response." in result[0].text
            mock_query.assert_called_once_with(
                "test-model",
                "Hello world",
                max_tokens=100,
                temperature=0.8,
                stream=False
            )

    @pytest.mark.asyncio
    async def test_handle_query_completion_unavailable(self, temp_config_mcp):
        """Test query completion with unavailable model"""
        input_data = QueryCompletionInput(model_name="test-model", prompt="Hello")

        with patch('llamacpp_manager.mcp_server.check_model_available') as mock_check:
            mock_check.return_value = False

            result = await handle_query_completion(input_data)

            assert len(result) == 1
            assert "is not available" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_query_chat(self, temp_config_mcp):
        """Test query chat"""
        input_data = QueryChatInput(
            model_name="chat-model",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=200
        )

        with patch('llamacpp_manager.mcp_server.check_model_available') as mock_check, \
             patch('llamacpp_manager.mcp_server.query_model_chat') as mock_query:

            mock_check.return_value = True
            mock_query.return_value = {
                "choices": [{
                    "message": {"content": "Hello! How can I help you?"}
                }]
            }

            result = await handle_query_chat(input_data)

            assert len(result) == 1
            assert "Hello! How can I help you?" in result[0].text
            mock_query.assert_called_once_with(
                "chat-model",
                [{"role": "user", "content": "Hello"}],
                max_tokens=200,
                temperature=0.7,
                stream=False
            )

    @pytest.mark.asyncio
    async def test_handle_add_model(self, temp_config_mcp):
        """Test adding a new model"""
        input_data = AddModelInput(
            name="new-model",
            model_path="/path/to/new.gguf",
            host="127.0.0.1",
            port=8082,
            autostart=True
        )

        with patch('llamacpp_manager.mcp_server.add_model') as mock_add, \
             patch('llamacpp_manager.mcp_server.save_config') as mock_save:

            result = await handle_add_model(input_data)

            assert len(result) == 1
            assert "Added model 'new-model' at 127.0.0.1:8082" in result[0].text
            mock_add.assert_called_once()
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_remove_model(self, temp_config_mcp):
        """Test removing a model"""
        input_data = RemoveModelInput(name="test-model")

        with patch('llamacpp_manager.mcp_server.remove_model') as mock_remove, \
             patch('llamacpp_manager.mcp_server.save_config') as mock_save:

            mock_remove.return_value = True

            result = await handle_remove_model(input_data)

            assert len(result) == 1
            assert "Removed model 'test-model'" in result[0].text
            mock_remove.assert_called_once()
            mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_remove_model_not_found(self, temp_config_mcp):
        """Test removing a model that doesn't exist"""
        input_data = RemoveModelInput(name="nonexistent-model")

        with patch('llamacpp_manager.mcp_server.remove_model') as mock_remove:
            mock_remove.return_value = False

            result = await handle_remove_model(input_data)

            assert len(result) == 1
            assert "Model 'nonexistent-model' not found" in result[0].text


class TestMCPServerIntegration:
    """Integration tests for MCP server functionality"""

    def test_input_schemas(self):
        """Test that input schemas are properly defined"""
        # Test that all input schema classes can be instantiated
        StartModelInput(model_name="test")
        StopModelInput(model_name="test")
        ModelStatusInput()
        QueryCompletionInput(model_name="test", prompt="hello")
        QueryChatInput(model_name="test", messages=[{"role": "user", "content": "hi"}])
        AddModelInput(name="test", model_path="/path", port=8080)
        RemoveModelInput(name="test")

        # Test schema generation
        assert StartModelInput.model_json_schema() is not None
        assert QueryCompletionInput.model_json_schema() is not None