import pytest
from unittest.mock import patch, MagicMock
import tempfile
import yaml
from pathlib import Path

from llamacpp_manager.cli import main
from llamacpp_manager.query import ModelQueryError


@pytest.fixture
def temp_config_with_models():
    """Create a temporary config with test models"""
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
                "name": "chat-model",
                "model_path": "/path/to/chat.gguf",
                "host": "127.0.0.1",
                "port": 8081
            }
        ]
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name

    with patch('llamacpp_manager.cli.load_config') as mock_load:
        mock_load.return_value = config_data
        yield config_data

    Path(config_path).unlink(missing_ok=True)


class TestQueryListCommand:
    """Unit tests for 'llamacpp-manager query list' command"""

    def test_query_list_with_available_models(self, temp_config_with_models, capsys):
        with patch('llamacpp_manager.cli.list_available_models') as mock_list:
            mock_list.return_value = ["test-model", "chat-model"]

            result = main(["query", "list"])

            assert result == 0
            captured = capsys.readouterr()
            assert "Available models:" in captured.out
            assert "test-model" in captured.out
            assert "chat-model" in captured.out

    def test_query_list_no_available_models(self, temp_config_with_models, capsys):
        with patch('llamacpp_manager.cli.list_available_models') as mock_list:
            mock_list.return_value = []

            result = main(["query", "list"])

            assert result == 0
            captured = capsys.readouterr()
            assert "No models are currently available" in captured.out

    def test_query_list_error(self, temp_config_with_models, capsys):
        with patch('llamacpp_manager.cli.list_available_models') as mock_list:
            mock_list.side_effect = Exception("Connection error")

            result = main(["query", "list"])

            assert result == 2
            captured = capsys.readouterr()
            assert "error: Connection error" in captured.err


class TestQueryCompleteCommand:
    """Unit tests for 'llamacpp-manager query complete' command"""

    def test_query_complete_success(self, temp_config_with_models, capsys):
        mock_response = {"content": "Hello! This is a test completion."}

        with patch('llamacpp_manager.cli.query_model_completion') as mock_query:
            mock_query.return_value = mock_response

            result = main(["query", "complete", "test-model", "Hello world"])

            assert result == 0
            captured = capsys.readouterr()
            assert "Hello! This is a test completion." in captured.out
            mock_query.assert_called_once_with(
                "test-model",
                "Hello world",
                max_tokens=512,
                temperature=0.7,
                stream=False,
                timeout=30.0
            )

    def test_query_complete_with_custom_params(self, temp_config_with_models, capsys):
        mock_response = {"content": "Custom response"}

        with patch('llamacpp_manager.cli.query_model_completion') as mock_query:
            mock_query.return_value = mock_response

            result = main([
                "query", "complete", "test-model", "Hello",
                "--max-tokens", "256",
                "--temperature", "0.9",
                "--timeout", "60.0"
            ])

            assert result == 0
            mock_query.assert_called_once_with(
                "test-model",
                "Hello",
                max_tokens=256,
                temperature=0.9,
                stream=False,
                timeout=60.0
            )

    def test_query_complete_streaming(self, temp_config_with_models, capsys):
        mock_chunks = [
            {"content": "Hello"},
            {"content": " world"},
            {"content": "!"}
        ]

        with patch('llamacpp_manager.cli.query_model_completion') as mock_query:
            mock_query.return_value = iter(mock_chunks)

            result = main(["query", "complete", "test-model", "Hello", "--stream"])

            assert result == 0
            captured = capsys.readouterr()
            assert "Hello world!" in captured.out
            mock_query.assert_called_once_with(
                "test-model",
                "Hello",
                max_tokens=512,
                temperature=0.7,
                stream=True,
                timeout=30.0
            )

    def test_query_complete_model_error(self, temp_config_with_models, capsys):
        with patch('llamacpp_manager.cli.query_model_completion') as mock_query:
            mock_query.side_effect = ModelQueryError("Model not available")

            result = main(["query", "complete", "test-model", "Hello"])

            assert result == 2
            captured = capsys.readouterr()
            assert "error: Model not available" in captured.err


class TestQueryChatCommand:
    """Unit tests for 'llamacpp-manager query chat' command"""

    def test_query_chat_success(self, temp_config_with_models, capsys):
        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Hello! How can I help you?"
                }
            }]
        }

        with patch('llamacpp_manager.cli.query_model_chat') as mock_query:
            mock_query.return_value = mock_response

            result = main([
                "query", "chat", "chat-model",
                "--message", "user:Hello there"
            ])

            assert result == 0
            captured = capsys.readouterr()
            assert "Hello! How can I help you?" in captured.out
            mock_query.assert_called_once_with(
                "chat-model",
                [{"role": "user", "content": "Hello there"}],
                max_tokens=512,
                temperature=0.7,
                stream=False,
                timeout=30.0
            )

    def test_query_chat_multiple_messages(self, temp_config_with_models, capsys):
        mock_response = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "I understand both messages."
                }
            }]
        }

        with patch('llamacpp_manager.cli.query_model_chat') as mock_query:
            mock_query.return_value = mock_response

            result = main([
                "query", "chat", "chat-model",
                "--message", "system:You are a helpful assistant",
                "--message", "user:Hello there"
            ])

            assert result == 0
            mock_query.assert_called_once_with(
                "chat-model",
                [
                    {"role": "system", "content": "You are a helpful assistant"},
                    {"role": "user", "content": "Hello there"}
                ],
                max_tokens=512,
                temperature=0.7,
                stream=False,
                timeout=30.0
            )

    def test_query_chat_streaming(self, temp_config_with_models, capsys):
        mock_chunks = [
            {"choices": [{"delta": {"content": "Hello"}}]},
            {"choices": [{"delta": {"content": " there"}}]},
            {"choices": [{"delta": {"content": "!"}}]}
        ]

        with patch('llamacpp_manager.cli.query_model_chat') as mock_query:
            mock_query.return_value = iter(mock_chunks)

            result = main([
                "query", "chat", "chat-model",
                "--message", "user:Hello",
                "--stream"
            ])

            assert result == 0
            captured = capsys.readouterr()
            assert "Hello there!" in captured.out

    def test_query_chat_no_messages(self, temp_config_with_models, capsys):
        result = main(["query", "chat", "chat-model"])

        assert result == 2
        captured = capsys.readouterr()
        assert "error: at least one --message is required" in captured.err

    def test_query_chat_invalid_message_format(self, temp_config_with_models, capsys):
        result = main([
            "query", "chat", "chat-model",
            "--message", "invalid-format-no-colon"
        ])

        assert result == 2
        captured = capsys.readouterr()
        assert "error: invalid message format" in captured.err

    def test_query_chat_invalid_role(self, temp_config_with_models, capsys):
        result = main([
            "query", "chat", "chat-model",
            "--message", "invalid_role:Hello there"
        ])

        assert result == 2
        captured = capsys.readouterr()
        assert "error: invalid role 'invalid_role'" in captured.err

    def test_query_chat_model_error(self, temp_config_with_models, capsys):
        with patch('llamacpp_manager.cli.query_model_chat') as mock_query:
            mock_query.side_effect = ModelQueryError("Chat model not available")

            result = main([
                "query", "chat", "chat-model",
                "--message", "user:Hello"
            ])

            assert result == 2
            captured = capsys.readouterr()
            assert "error: Chat model not available" in captured.err


class TestQueryCommandIntegration:
    """Integration tests for query commands"""

    def test_query_help(self, capsys):
        """Test that query help works"""
        with pytest.raises(SystemExit):
            main(["query", "--help"])

        captured = capsys.readouterr()
        assert "complete" in captured.out
        assert "chat" in captured.out
        assert "list" in captured.out

    def test_query_complete_help(self, capsys):
        """Test that query complete help works"""
        with pytest.raises(SystemExit):
            main(["query", "complete", "--help"])

        captured = capsys.readouterr()
        assert "model_name" in captured.out
        assert "prompt" in captured.out
        assert "--max-tokens" in captured.out

    def test_query_chat_help(self, capsys):
        """Test that query chat help works"""
        with pytest.raises(SystemExit):
            main(["query", "chat", "--help"])

        captured = capsys.readouterr()
        assert "model_name" in captured.out
        assert "--message" in captured.out


# Integration test that requires a real server
@pytest.mark.integration
class TestQueryRealIntegration:
    """Integration tests against real llama.cpp server"""

    def test_query_list_real_server(self, capsys):
        """Test query list against real server if available"""
        try:
            from llamacpp_manager.health import check_endpoint
            health = check_endpoint("127.0.0.1", 8080, timeout_ms=1000)
            if not health.get("up"):
                pytest.skip("No llama.cpp server running on localhost:8080")
        except Exception:
            pytest.skip("No llama.cpp server running on localhost:8080")

        # Mock config with real server port
        config_data = {
            "models": [{
                "name": "live-model",
                "model_path": "/test/path.gguf",
                "host": "127.0.0.1",
                "port": 8080
            }]
        }

        with patch('llamacpp_manager.cli.load_config') as mock_load:
            mock_load.return_value = config_data

            result = main(["query", "list"])

            assert result == 0
            captured = capsys.readouterr()
            # Should show the live model as available
            assert ("Available models:" in captured.out and "live-model" in captured.out) or \
                   "No models are currently available" in captured.out