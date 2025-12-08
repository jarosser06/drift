"""Tests for Claude Code CLI provider."""

import json
import subprocess
from unittest.mock import MagicMock, Mock, patch

import pytest

from drift.config.models import ModelConfig, ProviderConfig, ProviderType
from drift.providers.claude_code import ClaudeCodeProvider


@pytest.fixture
def provider_config():
    """Create a Claude Code provider config."""
    return ProviderConfig(provider=ProviderType.CLAUDE_CODE, params={})


@pytest.fixture
def model_config():
    """Create a model config for Claude Code."""
    return ModelConfig(
        provider="claude-code",
        model_id="sonnet",
        params={"max_tokens": 4096, "temperature": 0.0},
    )


@pytest.fixture
def mock_cache():
    """Create a mock cache."""
    return MagicMock()


class TestClaudeCodeProviderInit:
    """Test Claude Code provider initialization."""

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_init_with_available_cli(self, mock_run, mock_which, provider_config, model_config):
        """Test initialization when Claude Code CLI is available."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        provider = ClaudeCodeProvider(provider_config, model_config)

        assert provider.is_available()
        mock_which.assert_called_once_with("claude")
        mock_run.assert_called_once()

    @patch("drift.providers.claude_code.shutil.which")
    def test_init_with_missing_cli(self, mock_which, provider_config, model_config):
        """Test initialization when Claude Code CLI is not installed."""
        mock_which.return_value = None

        provider = ClaudeCodeProvider(provider_config, model_config)

        assert not provider.is_available()

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_init_with_failing_version_check(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test initialization when version check fails."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = Mock(returncode=1, stdout="", stderr="command not found")

        provider = ClaudeCodeProvider(provider_config, model_config)

        assert not provider.is_available()

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_init_with_timeout(self, mock_run, mock_which, provider_config, model_config):
        """Test initialization when version check times out."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 5)

        provider = ClaudeCodeProvider(provider_config, model_config)

        assert not provider.is_available()


class TestClaudeCodeProviderGenerate:
    """Test Claude Code provider generation."""

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_success_with_json_response(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test successful generation with JSON response."""
        # Mock CLI availability
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # Mock generation response
        response_data = {"response": "This is the AI response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)
        result = provider.generate("What is 2+2?")

        assert result == "This is the AI response"
        assert mock_run.call_count == 2

        # Check generate call arguments
        generate_call = mock_run.call_args_list[1]
        assert generate_call[0][0][0] == "claude"
        assert generate_call[0][0][1] == "-p"
        assert generate_call[0][0][2] == "What is 2+2?"
        assert "--model" in generate_call[0][0]
        assert "sonnet" in generate_call[0][0]
        assert "--output-format" in generate_call[0][0]
        assert "json" in generate_call[0][0]

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_different_json_fields(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation with different JSON response field names."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # Test different field names
        test_cases = [
            {"result": "Response via result"},
            {"content": "Response via content"},
            {"text": "Response via text"},
            {"message": "Response via message"},
        ]

        for response_data in test_cases:
            generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")
            mock_run.side_effect = [version_result, generate_result]

            provider = ClaudeCodeProvider(provider_config, model_config)
            result = provider.generate("Test prompt")

            assert list(response_data.values())[0] in result

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_non_json_fallback(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation falls back to raw text when JSON parsing fails."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        generate_result = Mock(returncode=0, stdout="This is raw text response", stderr="")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)
        result = provider.generate("Test prompt")

        assert result == "This is raw text response"

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_system_prompt(self, mock_run, mock_which, provider_config, model_config):
        """Test generation with system prompt."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Combined prompt response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)
        result = provider.generate("User prompt", system_prompt="System instructions")

        assert result == "Combined prompt response"

        # Check that system prompt was prepended to user prompt
        generate_call = mock_run.call_args_list[1]
        prompt_arg = generate_call[0][0][2]
        assert "System instructions" in prompt_arg
        assert "User prompt" in prompt_arg

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_opus_model(self, mock_run, mock_which, provider_config):
        """Test generation with opus model."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Opus response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        # Create model config with opus
        opus_config = ModelConfig(
            provider="claude-code",
            model_id="opus",
            params={},
        )

        provider = ClaudeCodeProvider(provider_config, opus_config)
        provider.generate("Test prompt")

        # Check model argument
        generate_call = mock_run.call_args_list[1]
        assert "opus" in generate_call[0][0]

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_full_model_id(self, mock_run, mock_which, provider_config):
        """Test generation with full Claude model ID."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        # Create model config with full model ID
        full_id_config = ModelConfig(
            provider="claude-code",
            model_id="claude-sonnet-4-5-20250929",
            params={},
        )

        provider = ClaudeCodeProvider(provider_config, full_id_config)
        provider.generate("Test prompt")

        # Should extract "sonnet" from full ID
        generate_call = mock_run.call_args_list[1]
        assert "sonnet" in generate_call[0][0]

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_custom_timeout(self, mock_run, mock_which, provider_config):
        """Test generation with custom timeout."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        # Create model config with custom timeout
        timeout_config = ModelConfig(
            provider="claude-code",
            model_id="sonnet",
            params={"timeout": 300},
        )

        provider = ClaudeCodeProvider(provider_config, timeout_config)
        provider.generate("Test prompt")

        # Check timeout was used
        generate_call = mock_run.call_args_list[1]
        assert generate_call[1]["timeout"] == 300

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_when_unavailable(self, mock_run, mock_which, provider_config, model_config):
        """Test generation raises error when provider is unavailable."""
        mock_which.return_value = None

        provider = ClaudeCodeProvider(provider_config, model_config)

        with pytest.raises(RuntimeError) as exc_info:
            provider.generate("Test prompt")

        assert "Claude Code provider is not available" in str(exc_info.value)
        assert "install" in str(exc_info.value).lower()

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_cli_error(self, mock_run, mock_which, provider_config, model_config):
        """Test generation handles CLI errors."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        generate_result = Mock(returncode=1, stdout="", stderr="Error: Invalid argument")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")

        assert "Claude Code CLI error" in str(exc_info.value)
        assert "Invalid argument" in str(exc_info.value)

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_timeout_error(self, mock_run, mock_which, provider_config, model_config):
        """Test generation handles timeout errors."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        mock_run.side_effect = [
            version_result,
            subprocess.TimeoutExpired("claude", 120),
        ]

        provider = ClaudeCodeProvider(provider_config, model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")

        assert "timed out" in str(exc_info.value)
        assert "120 seconds" in str(exc_info.value)


class TestClaudeCodeProviderCaching:
    """Test Claude Code provider with caching."""

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_cache_hit(
        self, mock_run, mock_which, provider_config, model_config, mock_cache
    ):
        """Test generation with cache hit."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        mock_run.side_effect = [version_result]

        # Mock cache to return cached response
        mock_cache.get.return_value = "Cached response"

        provider = ClaudeCodeProvider(provider_config, model_config, mock_cache)
        result = provider.generate(
            "Test prompt",
            cache_key="test_key",
            content_hash="abc123",
        )

        assert result == "Cached response"
        mock_cache.get.assert_called_once_with("test_key", "abc123")
        # Should not call CLI since we hit cache
        assert mock_run.call_count == 1  # Only version check

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_cache_miss(
        self, mock_run, mock_which, provider_config, model_config, mock_cache
    ):
        """Test generation with cache miss."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Fresh response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        # Mock cache to return None (cache miss)
        mock_cache.get.return_value = None

        provider = ClaudeCodeProvider(provider_config, model_config, mock_cache)
        result = provider.generate(
            "Test prompt",
            cache_key="test_key",
            content_hash="abc123",
            drift_type="test_type",
        )

        assert result == "Fresh response"
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once_with("test_key", "abc123", "Fresh response", "test_type")


class TestClaudeCodeProviderMethods:
    """Test Claude Code provider utility methods."""

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_get_model_id(self, mock_run, mock_which, provider_config, model_config):
        """Test get_model_id returns correct model ID."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        provider = ClaudeCodeProvider(provider_config, model_config)

        assert provider.get_model_id() == "sonnet"

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_get_provider_type(self, mock_run, mock_which, provider_config, model_config):
        """Test get_provider_type returns correct type."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        provider = ClaudeCodeProvider(provider_config, model_config)

        assert provider.get_provider_type() == "claude-code"


class TestClaudeCodeProviderEdgeCases:
    """Test Claude Code provider edge cases and error conditions."""

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_init_with_generic_exception(self, mock_run, mock_which, provider_config, model_config):
        """Test initialization handles generic exceptions."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.side_effect = Exception("Unexpected error")

        provider = ClaudeCodeProvider(provider_config, model_config)

        assert not provider.is_available()

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_get_model_name_with_unknown_model(self, mock_run, mock_which, provider_config):
        """Test _get_model_name with unknown model ID falls back to sonnet."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # Create config with unknown model ID
        unknown_config = ModelConfig(
            provider="claude-code",
            model_id="unknown-model-xyz",
            params={},
        )

        provider = ClaudeCodeProvider(provider_config, unknown_config)

        # Should default to sonnet and log warning
        assert provider._get_model_name() == "sonnet"

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_haiku_model(self, mock_run, mock_which, provider_config):
        """Test generation with haiku model."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Haiku response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        # Create model config with haiku
        haiku_config = ModelConfig(
            provider="claude-code",
            model_id="haiku",
            params={},
        )

        provider = ClaudeCodeProvider(provider_config, haiku_config)
        provider.generate("Test prompt")

        # Check model argument
        generate_call = mock_run.call_args_list[1]
        assert "haiku" in generate_call[0][0]

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_full_opus_model_id(self, mock_run, mock_which, provider_config):
        """Test generation with full Opus model ID extracts 'opus'."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Opus response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        # Create model config with full opus model ID
        opus_config = ModelConfig(
            provider="claude-code",
            model_id="claude-opus-4-5-20250929",
            params={},
        )

        provider = ClaudeCodeProvider(provider_config, opus_config)
        provider.generate("Test prompt")

        # Check that "opus" was extracted from full ID
        generate_call = mock_run.call_args_list[1]
        assert "opus" in generate_call[0][0]

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_full_haiku_model_id(self, mock_run, mock_which, provider_config):
        """Test generation with full Haiku model ID extracts 'haiku'."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        response_data = {"response": "Haiku response"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        # Create model config with full haiku model ID
        haiku_config = ModelConfig(
            provider="claude-code",
            model_id="claude-haiku-4-5-20250929",
            params={},
        )

        provider = ClaudeCodeProvider(provider_config, haiku_config)
        provider.generate("Test prompt")

        # Check that "haiku" was extracted from full ID
        generate_call = mock_run.call_args_list[1]
        assert "haiku" in generate_call[0][0]

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_dict_response_no_known_fields(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation with dict response but no known text fields."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # Response with unknown field names
        response_data = {"unknown_field": "", "another_field": "Some text"}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)

        # Should raise Exception when no known fields found
        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")

        assert "Could not extract response text from Claude Code output" in str(exc_info.value)
        assert "unknown_field" in str(exc_info.value)

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_dict_response_only_empty_values(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation with dict response containing only empty values."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # Response with only empty values
        response_data = {"field1": "", "field2": ""}
        generate_result = Mock(returncode=0, stdout=json.dumps(response_data), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)

        # Should raise Exception when no known fields found
        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")

        assert "Could not extract response text from Claude Code output" in str(exc_info.value)

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_string_json_response(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation when JSON response is a string (not dict)."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # JSON response that's just a string
        generate_result = Mock(returncode=0, stdout=json.dumps("Direct string response"), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)
        result = provider.generate("Test prompt")

        assert result == "Direct string response"

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_unexpected_json_type(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation with unexpected JSON response type (list, number, etc)."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # JSON response that's a list
        generate_result = Mock(returncode=0, stdout=json.dumps([1, 2, 3]), stderr="")

        mock_run.side_effect = [version_result, generate_result]

        provider = ClaudeCodeProvider(provider_config, model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")

        # The ValueError gets wrapped in an Exception
        assert "Error calling Claude Code CLI" in str(exc_info.value)
        assert "Unexpected response type" in str(exc_info.value)

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_file_not_found_error(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation handles FileNotFoundError."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        mock_run.side_effect = [version_result, FileNotFoundError("claude command not found")]

        provider = ClaudeCodeProvider(provider_config, model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")

        assert "Claude Code CLI not found" in str(exc_info.value)
        assert "PATH" in str(exc_info.value)

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_generate_with_generic_exception(
        self, mock_run, mock_which, provider_config, model_config
    ):
        """Test generation handles generic exceptions."""
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # Generic exception that's not a known error type
        mock_run.side_effect = [version_result, OSError("Generic OS error")]

        provider = ClaudeCodeProvider(provider_config, model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")

        assert "Error calling Claude Code CLI" in str(exc_info.value)
        assert "Generic OS error" in str(exc_info.value)
