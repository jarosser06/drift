"""Unit tests for LLM providers."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from anthropic import AnthropicError
from botocore.exceptions import ClientError, NoCredentialsError

from drift.config.models import ModelConfig, ProviderConfig, ProviderType
from drift.providers.anthropic import AnthropicProvider
from drift.providers.bedrock import BedrockProvider


class TestBedrockProvider:
    """Tests for BedrockProvider."""

    @pytest.fixture
    def bedrock_provider_config(self):
        """Bedrock provider configuration fixture."""
        return ProviderConfig(
            provider=ProviderType.BEDROCK,
            params={"region": "us-east-1"},
        )

    @pytest.fixture
    def bedrock_model_config(self):
        """Bedrock model configuration fixture."""
        return ModelConfig(
            provider="bedrock",
            model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
            params={
                "max_tokens": 4096,
                "temperature": 0.0,
            },
        )

    @patch("drift.providers.bedrock.boto3")
    def test_initialization_success(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test successful provider initialization."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.provider_config == bedrock_provider_config
        assert provider.model_config == bedrock_model_config
        assert provider.client is not None
        mock_boto3.client.assert_called_once_with(
            "bedrock-runtime",
            region_name="us-east-1",
        )

    @patch("drift.providers.bedrock.boto3")
    def test_initialization_uses_default_region(self, mock_boto3):
        """Test initialization uses default region when not specified."""
        provider_config = ProviderConfig(
            provider=ProviderType.BEDROCK,
            params={},  # No region specified
        )
        model_config = ModelConfig(
            provider="bedrock",
            model_id="test-model",
            params={},
        )
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        BedrockProvider(provider_config, model_config)

        mock_boto3.client.assert_called_once_with(
            "bedrock-runtime",
            region_name="us-east-1",  # Default
        )

    @patch("drift.providers.bedrock.boto3")
    def test_initialization_failure(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test provider initialization handles client creation failure."""
        mock_boto3.client.side_effect = Exception("AWS Error")

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.client is None

    @patch("drift.providers.bedrock.boto3")
    def test_is_available_true(self, mock_boto3, bedrock_provider_config, bedrock_model_config):
        """Test is_available returns True when client is initialized."""
        mock_client = MagicMock()
        mock_client._client_config = {}
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.is_available() is True

    @patch("drift.providers.bedrock.boto3")
    def test_is_available_false_no_client(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test is_available returns False when client is None."""
        mock_boto3.client.side_effect = Exception("No credentials")

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.is_available() is False

    @patch("drift.providers.bedrock.boto3")
    def test_is_available_false_no_credentials(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test is_available returns False when credentials are missing."""
        mock_client = MagicMock()
        mock_client._client_config = Mock(side_effect=NoCredentialsError())
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.is_available() is False

    @patch("drift.providers.bedrock.boto3")
    def test_is_available_false_attribute_error(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test is_available returns False when client config is missing."""
        mock_client = MagicMock()
        del mock_client._client_config  # Remove the attribute
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.is_available() is False

    @patch("drift.providers.bedrock.boto3")
    def test_is_available_false_generic_error(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test is_available returns False on generic errors."""
        mock_client = MagicMock()
        mock_client._client_config = Mock(side_effect=RuntimeError("Some error"))
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.is_available() is False

    @patch("drift.providers.bedrock.boto3")
    def test_generate_success(self, mock_boto3, bedrock_provider_config, bedrock_model_config):
        """Test successful text generation."""
        mock_client = MagicMock()
        mock_client._client_config = {}

        response_body = {
            "content": [{"text": "Generated response text"}],
            "stop_reason": "end_turn",
        }

        mock_response = {"body": Mock(read=lambda: json.dumps(response_body).encode())}
        mock_client.invoke_model.return_value = mock_response
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)
        result = provider.generate("Test prompt")

        assert result == "Generated response text"
        mock_client.invoke_model.assert_called_once()

        # Verify the request structure
        call_args = mock_client.invoke_model.call_args
        assert call_args[1]["modelId"] == bedrock_model_config.model_id

        request_body = json.loads(call_args[1]["body"])
        assert request_body["messages"][0]["content"] == "Test prompt"
        assert request_body["max_tokens"] == 4096
        assert request_body["temperature"] == 0.0

    @patch("drift.providers.bedrock.boto3")
    def test_generate_with_system_prompt(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test generation with system prompt."""
        mock_client = MagicMock()
        mock_client._client_config = {}

        response_body = {"content": [{"text": "Response"}]}
        mock_response = {"body": Mock(read=lambda: json.dumps(response_body).encode())}
        mock_client.invoke_model.return_value = mock_response
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)
        provider.generate("User prompt", system_prompt="System instructions")

        # Verify system prompt is included
        call_args = mock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]["body"])
        assert request_body["system"] == "System instructions"

    @patch("drift.providers.bedrock.boto3")
    def test_generate_with_additional_params(self, mock_boto3):
        """Test generation with additional parameters."""
        provider_config = ProviderConfig(
            provider=ProviderType.BEDROCK,
            params={"region": "us-east-1"},
        )
        model_config = ModelConfig(
            provider="bedrock",
            model_id="test-model",
            params={"top_p": 0.9, "stop_sequences": ["STOP"]},
        )

        mock_client = MagicMock()
        mock_client._client_config = {}
        response_body = {"content": [{"text": "Response"}]}
        mock_response = {"body": Mock(read=lambda: json.dumps(response_body).encode())}
        mock_client.invoke_model.return_value = mock_response
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(provider_config, model_config)
        provider.generate("Test")

        # Verify additional params are included
        call_args = mock_client.invoke_model.call_args
        request_body = json.loads(call_args[1]["body"])
        assert request_body["top_p"] == 0.9
        assert request_body["stop_sequences"] == ["STOP"]

    @patch("drift.providers.bedrock.boto3")
    def test_generate_not_available(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test generate raises error when provider not available."""
        mock_boto3.client.side_effect = Exception("No client")

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        with pytest.raises(RuntimeError) as exc_info:
            provider.generate("Test prompt")
        assert "Bedrock provider is not available" in str(exc_info.value)

    @patch("drift.providers.bedrock.boto3")
    def test_generate_api_error(self, mock_boto3, bedrock_provider_config, bedrock_model_config):
        """Test generate handles API errors."""
        mock_client = MagicMock()
        mock_client._client_config = {}
        mock_client.invoke_model.side_effect = ClientError(
            {"Error": {"Code": "ValidationException", "Message": "Invalid request"}},
            "InvokeModel",
        )
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")
        assert "Bedrock API error" in str(exc_info.value)

    @patch("drift.providers.bedrock.boto3")
    def test_generate_invalid_json_response(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test generate handles invalid JSON in response."""
        mock_client = MagicMock()
        mock_client._client_config = {}
        mock_response = {"body": Mock(read=lambda: b"invalid json")}
        mock_client.invoke_model.return_value = mock_response
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")
        assert "Failed to parse Bedrock response" in str(exc_info.value)

    @patch("drift.providers.bedrock.boto3")
    def test_generate_unexpected_response_format(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test generate handles unexpected response format."""
        mock_client = MagicMock()
        mock_client._client_config = {}
        response_body = {"unexpected": "format"}  # Missing 'content' field
        mock_response = {"body": Mock(read=lambda: json.dumps(response_body).encode())}
        mock_client.invoke_model.return_value = mock_response
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")
        assert "Unexpected response format" in str(exc_info.value)

    @patch("drift.providers.bedrock.boto3")
    def test_generate_empty_content(
        self, mock_boto3, bedrock_provider_config, bedrock_model_config
    ):
        """Test generate handles empty content array."""
        mock_client = MagicMock()
        mock_client._client_config = {}
        response_body = {"content": []}  # Empty content
        mock_response = {"body": Mock(read=lambda: json.dumps(response_body).encode())}
        mock_client.invoke_model.return_value = mock_response
        mock_boto3.client.return_value = mock_client

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")
        assert "Unexpected response format" in str(exc_info.value)

    @patch("drift.providers.bedrock.boto3")
    def test_get_model_id(self, mock_boto3, bedrock_provider_config, bedrock_model_config):
        """Test getting model ID."""
        mock_boto3.client.return_value = MagicMock()

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.get_model_id() == bedrock_model_config.model_id

    @patch("drift.providers.bedrock.boto3")
    def test_get_provider_type(self, mock_boto3, bedrock_provider_config, bedrock_model_config):
        """Test getting provider type."""
        mock_boto3.client.return_value = MagicMock()

        provider = BedrockProvider(bedrock_provider_config, bedrock_model_config)

        assert provider.get_provider_type() == "bedrock"


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    @pytest.fixture
    def anthropic_provider_config(self):
        """Anthropic provider configuration fixture."""
        return ProviderConfig(
            provider=ProviderType.ANTHROPIC,
            params={},
        )

    @pytest.fixture
    def anthropic_provider_config_custom_env(self):
        """Anthropic provider configuration with custom API key env."""
        return ProviderConfig(
            provider=ProviderType.ANTHROPIC,
            params={"api_key_env": "CUSTOM_API_KEY"},
        )

    @pytest.fixture
    def anthropic_model_config(self):
        """Anthropic model configuration fixture."""
        return ModelConfig(
            provider="anthropic",
            model_id="claude-sonnet-4-5-20250929",
            params={
                "max_tokens": 4096,
                "temperature": 0.0,
            },
        )

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_initialization_success(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test successful provider initialization."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        assert provider.provider_config == anthropic_provider_config
        assert provider.model_config == anthropic_model_config
        assert provider.client is not None
        mock_anthropic.assert_called_once_with(api_key="test-api-key")

    @patch.dict("os.environ", {"CUSTOM_API_KEY": "custom-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_initialization_custom_api_key_env(
        self, mock_anthropic, anthropic_provider_config_custom_env, anthropic_model_config
    ):
        """Test initialization with custom API key environment variable."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        AnthropicProvider(anthropic_provider_config_custom_env, anthropic_model_config)

        mock_anthropic.assert_called_once_with(api_key="custom-key")

    @patch.dict("os.environ", {}, clear=True)
    @patch("drift.providers.anthropic.Anthropic")
    def test_initialization_no_api_key(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test provider initialization handles missing API key."""
        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        assert provider.client is None
        mock_anthropic.assert_not_called()

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_initialization_handles_exception(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test provider initialization handles client creation failure."""
        mock_anthropic.side_effect = Exception("Initialization error")

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        assert provider.client is None

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_is_available_true(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test is_available returns True when client is initialized."""
        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        assert provider.is_available() is True

    @patch.dict("os.environ", {}, clear=True)
    @patch("drift.providers.anthropic.Anthropic")
    def test_is_available_false_no_api_key(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test is_available returns False when API key is missing."""
        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        assert provider.is_available() is False

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_success(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test successful text generation."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Generated response text")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)
        result = provider.generate("Test prompt")

        assert result == "Generated response text"
        mock_client.messages.create.assert_called_once()

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_with_system_prompt(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test generation with system prompt."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)
        provider.generate("User prompt", system_prompt="System instructions")

        # Verify system prompt is included
        call_args = mock_client.messages.create.call_args
        assert "system" in call_args[1]
        assert call_args[1]["system"] == "System instructions"

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_with_additional_params(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test generation with additional model parameters."""
        model_config = ModelConfig(
            provider="anthropic",
            model_id="claude-sonnet-4-5-20250929",
            params={"max_tokens": 2048, "temperature": 0.5, "top_p": 0.9, "top_k": 40},
        )
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Response")]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, model_config)
        provider.generate("Test")

        # Verify additional params are included
        call_args = mock_client.messages.create.call_args
        assert call_args[1]["top_p"] == 0.9
        assert call_args[1]["top_k"] == 40

    @patch.dict("os.environ", {}, clear=True)
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_raises_error_when_not_available(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test generate raises error when provider not available."""
        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        with pytest.raises(RuntimeError) as exc_info:
            provider.generate("Test prompt")
        assert "Anthropic provider is not available" in str(exc_info.value)
        assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @patch.dict("os.environ", {"CUSTOM_API_KEY": "test-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_error_message_custom_env(
        self, mock_anthropic, anthropic_provider_config_custom_env, anthropic_model_config
    ):
        """Test error message includes custom API key env variable name."""
        # Initialize without the custom env var set
        with patch.dict("os.environ", {}, clear=True):
            provider = AnthropicProvider(
                anthropic_provider_config_custom_env, anthropic_model_config
            )

            with pytest.raises(RuntimeError) as exc_info:
                provider.generate("Test prompt")
            assert "CUSTOM_API_KEY" in str(exc_info.value)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_handles_anthropic_error(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test generate handles Anthropic API errors."""
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = AnthropicError("API Error")
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")
        assert "Anthropic API error" in str(exc_info.value)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_handles_empty_response(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test generate handles empty response content."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")
        assert "Unexpected response format" in str(exc_info.value)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_generate_handles_none_response(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test generate handles None response content."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = None
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        with pytest.raises(Exception) as exc_info:
            provider.generate("Test prompt")
        assert "Unexpected response format" in str(exc_info.value)

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_get_model_id(self, mock_anthropic, anthropic_provider_config, anthropic_model_config):
        """Test getting model ID."""
        mock_anthropic.return_value = MagicMock()

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        assert provider.get_model_id() == anthropic_model_config.model_id

    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-api-key"})
    @patch("drift.providers.anthropic.Anthropic")
    def test_get_provider_type(
        self, mock_anthropic, anthropic_provider_config, anthropic_model_config
    ):
        """Test getting provider type."""
        mock_anthropic.return_value = MagicMock()

        provider = AnthropicProvider(anthropic_provider_config, anthropic_model_config)

        assert provider.get_provider_type() == "anthropic"
