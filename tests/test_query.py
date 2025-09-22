import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import yaml

from llamacpp_manager.query import (
    get_model_endpoint,
    check_model_available,
    query_model_completion,
    query_model_chat,
    list_available_models,
    ModelQueryError
)


@pytest.fixture
def temp_config():
    """Create a temporary config for testing"""
    config_data = {
        "llama_server_path": "/opt/homebrew/bin/llama-server",
        "log_dir": "/tmp/llamacpp-logs",
        "timeout_ms": 2000,
        "models": [
            {
                "name": "test-model",
                "model_path": "/path/to/model.gguf",
                "host": "127.0.0.1",
                "port": 8080
            },
            {
                "name": "remote-model",
                "model_path": "/path/to/remote.gguf",
                "host": "192.168.1.100",
                "port": 8081
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name

    with patch('llamacpp_manager.query.load_config') as mock_load:
        mock_load.return_value = config_data
        yield config_data

    Path(config_path).unlink(missing_ok=True)


class TestGetModelEndpoint:
    """Unit tests for get_model_endpoint function"""

    def test_get_existing_model_endpoint(self, temp_config):
        host, port = get_model_endpoint("test-model")
        assert host == "127.0.0.1"
        assert port == 8080

    def test_get_remote_model_endpoint(self, temp_config):
        host, port = get_model_endpoint("remote-model")
        assert host == "192.168.1.100"
        assert port == 8081

    def test_get_nonexistent_model_endpoint(self, temp_config):
        with pytest.raises(ModelQueryError) as exc_info:
            get_model_endpoint("nonexistent-model")
        assert "not found in config" in str(exc_info.value)


class TestCheckModelAvailable:
    """Unit tests for check_model_available function"""

    def test_available_model(self, temp_config):
        with patch('llamacpp_manager.query.check_endpoint') as mock_check:
            mock_check.return_value = {"up": True, "latency_ms": 100}
            result = check_model_available("test-model")
            assert result is True
            mock_check.assert_called_once_with("127.0.0.1", 8080, timeout_ms=5000)

    def test_unavailable_model(self, temp_config):
        with patch('llamacpp_manager.query.check_endpoint') as mock_check:
            mock_check.return_value = {"up": False}
            result = check_model_available("test-model")
            assert result is False

    def test_model_check_exception(self, temp_config):
        with patch('llamacpp_manager.query.check_endpoint') as mock_check:
            mock_check.side_effect = Exception("Connection failed")
            result = check_model_available("test-model")
            assert result is False

    def test_nonexistent_model_check(self, temp_config):
        result = check_model_available("nonexistent-model")
        assert result is False


class TestQueryModelCompletion:
    """Unit tests for query_model_completion function"""

    @pytest.fixture
    def mock_httpx_client(self):
        with patch('llamacpp_manager.query.httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "content": "Test completion response",
                "stop": True,
                "generation_settings": {}
            }
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            yield mock_client, mock_response

    def test_successful_completion_query(self, temp_config, mock_httpx_client):
        mock_client, mock_response = mock_httpx_client

        with patch('llamacpp_manager.query.check_model_available', return_value=True):
            result = query_model_completion("test-model", "Hello world")

            assert result["content"] == "Test completion response"
            mock_client.assert_called_once()
            client_instance = mock_client.return_value.__enter__.return_value
            client_instance.post.assert_called_once_with(
                "http://127.0.0.1:8080/completion",
                json={
                    "prompt": "Hello world",
                    "n_predict": 512,
                    "temperature": 0.7,
                    "stream": False
                }
            )

    def test_completion_with_custom_params(self, temp_config, mock_httpx_client):
        mock_client, mock_response = mock_httpx_client

        with patch('llamacpp_manager.query.check_model_available', return_value=True):
            result = query_model_completion(
                "test-model",
                "Hello world",
                max_tokens=256,
                temperature=0.9,
                top_k=40
            )

            client_instance = mock_client.return_value.__enter__.return_value
            client_instance.post.assert_called_once_with(
                "http://127.0.0.1:8080/completion",
                json={
                    "prompt": "Hello world",
                    "n_predict": 256,
                    "temperature": 0.9,
                    "stream": False,
                    "top_k": 40
                }
            )

    def test_completion_model_unavailable(self, temp_config):
        with patch('llamacpp_manager.query.check_model_available', return_value=False):
            with pytest.raises(ModelQueryError) as exc_info:
                query_model_completion("test-model", "Hello world")
            assert "not running or not reachable" in str(exc_info.value)

    def test_completion_http_error(self, temp_config):
        with patch('llamacpp_manager.query.check_model_available', return_value=True):
            with patch('llamacpp_manager.query.httpx.Client') as mock_client:
                mock_response = MagicMock()
                mock_response.raise_for_status.side_effect = Exception("HTTP Error")
                mock_client.return_value.__enter__.return_value.post.return_value = mock_response

                with pytest.raises(ModelQueryError) as exc_info:
                    query_model_completion("test-model", "Hello world")
                assert "Failed to query" in str(exc_info.value)


class TestQueryModelChat:
    """Unit tests for query_model_chat function"""

    @pytest.fixture
    def mock_httpx_client_chat(self):
        with patch('llamacpp_manager.query.httpx.Client') as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Hello! How can I help you today?"
                    },
                    "finish_reason": "stop"
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 12}
            }
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            yield mock_client, mock_response

    def test_successful_chat_query(self, temp_config, mock_httpx_client_chat):
        mock_client, mock_response = mock_httpx_client_chat
        messages = [{"role": "user", "content": "Hello"}]

        with patch('llamacpp_manager.query.check_model_available', return_value=True):
            result = query_model_chat("test-model", messages)

            assert result["choices"][0]["message"]["content"] == "Hello! How can I help you today?"
            mock_client.assert_called_once()
            client_instance = mock_client.return_value.__enter__.return_value
            client_instance.post.assert_called_once_with(
                "http://127.0.0.1:8080/v1/chat/completions",
                json={
                    "messages": messages,
                    "max_tokens": 512,
                    "temperature": 0.7,
                    "stream": False
                }
            )

    def test_chat_model_unavailable(self, temp_config):
        messages = [{"role": "user", "content": "Hello"}]
        with patch('llamacpp_manager.query.check_model_available', return_value=False):
            with pytest.raises(ModelQueryError) as exc_info:
                query_model_chat("test-model", messages)
            assert "not running or not reachable" in str(exc_info.value)


class TestListAvailableModels:
    """Unit tests for list_available_models function"""

    def test_list_all_available_models(self, temp_config):
        with patch('llamacpp_manager.query.check_model_available') as mock_check:
            # Mock first model as available, second as unavailable
            mock_check.side_effect = lambda name, **kwargs: name == "test-model"

            result = list_available_models()

            assert result == ["test-model"]
            assert len(mock_check.call_args_list) == 2

    def test_list_no_available_models(self, temp_config):
        with patch('llamacpp_manager.query.check_model_available', return_value=False):
            result = list_available_models()
            assert result == []

    def test_list_models_empty_config(self):
        with patch('llamacpp_manager.query.load_config') as mock_load:
            mock_load.return_value = {"models": []}
            result = list_available_models()
            assert result == []


# Integration tests
@pytest.mark.integration
class TestQueryIntegration:
    """Integration tests that require actual llama.cpp server running"""

    def test_real_model_availability_check(self):
        """Test against real model if available"""
        # This test will be skipped if no real server is running
        try:
            # Try to check if there's a server on default port
            from llamacpp_manager.query import check_endpoint
            health = check_endpoint("127.0.0.1", 8080, timeout_ms=1000)
            if not health.get("up"):
                pytest.skip("No llama.cpp server running on localhost:8080")
        except Exception:
            pytest.skip("No llama.cpp server running on localhost:8080")

        # If we get here, we have a real server to test against
        with patch('llamacpp_manager.query.load_config') as mock_load:
            mock_load.return_value = {
                "models": [{
                    "name": "live-test-model",
                    "model_path": "/test/path.gguf",
                    "host": "127.0.0.1",
                    "port": 8080
                }]
            }
            result = check_model_available("live-test-model")
            assert result is True