"""Unit tests for configuration models."""

import pytest
from pydantic import ValidationError

from drift.config.models import (
    AgentToolConfig,
    ConversationMode,
    ConversationSelection,
    DriftConfig,
    ModelConfig,
    ProviderConfig,
    ProviderType,
    RuleDefinition,
)


class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_valid_provider_config(self):
        """Test creating a valid provider configuration."""
        config = ProviderConfig(
            provider=ProviderType.BEDROCK,
            params={"region": "us-east-1"},
        )
        assert config.provider == ProviderType.BEDROCK
        assert config.params == {"region": "us-east-1"}

    def test_default_params(self):
        """Test default params is empty dict."""
        config = ProviderConfig(
            provider=ProviderType.BEDROCK,
        )
        assert config.params == {}

    def test_multiple_params(self):
        """Test provider config with multiple parameters."""
        config = ProviderConfig(
            provider=ProviderType.BEDROCK,
            params={
                "region": "us-west-2",
                "endpoint_url": "https://custom.endpoint.com",
            },
        )
        assert config.params["region"] == "us-west-2"
        assert config.params["endpoint_url"] == "https://custom.endpoint.com"


class TestModelConfig:
    """Tests for ModelConfig model."""

    def test_valid_model_config(self):
        """Test creating a valid model configuration."""
        config = ModelConfig(
            provider="bedrock",
            model_id="claude-3-haiku",
            params={
                "max_tokens": 4096,
                "temperature": 0.5,
            },
        )
        assert config.provider == "bedrock"
        assert config.model_id == "claude-3-haiku"
        assert config.params["max_tokens"] == 4096
        assert config.params["temperature"] == 0.5

    def test_default_params(self):
        """Test default values for params field."""
        config = ModelConfig(
            provider="bedrock",
            model_id="test-model",
        )
        assert config.params == {}

    def test_model_params(self):
        """Test model configuration with various parameters."""
        config = ModelConfig(
            provider="bedrock",
            model_id="test-model",
            params={
                "max_tokens": 8192,
                "temperature": 0.7,
                "top_p": 0.9,
                "stop_sequences": ["STOP"],
            },
        )
        assert config.params["max_tokens"] == 8192
        assert config.params["temperature"] == 0.7
        assert config.params["top_p"] == 0.9
        assert config.params["stop_sequences"] == ["STOP"]


class TestDriftLearningType:
    """Tests for RuleDefinition model."""

    def test_valid_learning_type(self):
        """Test creating a valid drift learning type."""
        from drift.config.models import PhaseDefinition

        rule_type = RuleDefinition(
            description="Test learning type",
            scope="conversation_level",
            context="Test context for optimization",
            requires_project_context=False,
            supported_clients=None,
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Look for test patterns",
                    model="haiku",
                )
            ],
        )
        assert rule_type.description == "Test learning type"
        assert rule_type.phases[0].prompt == "Look for test patterns"
        assert rule_type.phases[0].type == "prompt"
        assert rule_type.scope == "conversation_level"
        assert rule_type.context == "Test context for optimization"
        assert rule_type.requires_project_context is False
        assert rule_type.supported_clients is None
        assert rule_type.phases[0].model == "haiku"
        assert rule_type.document_bundle is None

    def test_default_values(self):
        """Test default values for optional fields."""
        from drift.config.models import PhaseDefinition

        rule_type = RuleDefinition(
            description="Test",
            scope="conversation_level",
            context="Test context",
            requires_project_context=False,
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Detect",
                )
            ],
        )
        assert rule_type.phases[0].model is None
        assert rule_type.supported_clients is None
        assert rule_type.document_bundle is None


class TestAgentToolConfig:
    """Tests for AgentToolConfig model."""

    def test_valid_agent_config(self):
        """Test creating a valid agent tool configuration."""
        config = AgentToolConfig(
            conversation_path="/path/to/conversations",
            enabled=True,
        )
        assert config.conversation_path == "/path/to/conversations"
        assert config.enabled is True

    def test_path_expansion(self):
        """Test that tilde is expanded in conversation path."""
        config = AgentToolConfig(
            conversation_path="~/conversations",
        )
        # Should expand to user's home directory
        assert "~" not in config.conversation_path
        assert config.conversation_path.endswith("conversations")

    def test_default_enabled(self):
        """Test default value for enabled field."""
        config = AgentToolConfig(
            conversation_path="/path/to/conversations",
        )
        assert config.enabled is True


class TestConversationSelection:
    """Tests for ConversationSelection model."""

    def test_valid_selection(self):
        """Test creating a valid conversation selection."""
        selection = ConversationSelection(
            mode=ConversationMode.LAST_N_DAYS,
            days=14,
        )
        assert selection.mode == ConversationMode.LAST_N_DAYS
        assert selection.days == 14

    def test_default_values(self):
        """Test default values."""
        selection = ConversationSelection()
        assert selection.mode == ConversationMode.LATEST
        assert selection.days == 7

    def test_days_validation_valid(self):
        """Test days validation with valid value."""
        selection = ConversationSelection(days=1)
        assert selection.days == 1

        selection = ConversationSelection(days=30)
        assert selection.days == 30

    def test_days_validation_invalid(self):
        """Test days validation rejects non-positive values."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationSelection(days=0)
        assert "days must be positive" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ConversationSelection(days=-1)
        assert "days must be positive" in str(exc_info.value)


class TestDriftConfig:
    """Tests for DriftConfig model."""

    def test_valid_config(
        self, sample_provider_config, sample_model_config, sample_learning_type, sample_agent_config
    ):
        """Test creating a valid drift configuration."""
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            rule_definitions={"incomplete_work": sample_learning_type},
            agent_tools={"claude-code": sample_agent_config},
            temp_dir="/tmp/drift",
        )
        assert "bedrock" in config.providers
        assert "haiku" in config.models
        assert config.default_model == "haiku"
        assert "incomplete_work" in config.rule_definitions
        assert "claude-code" in config.agent_tools
        assert config.temp_dir == "/tmp/drift"

    def test_default_values(self):
        """Test default values for optional fields."""
        config = DriftConfig()
        assert config.providers == {}
        assert config.models == {}
        assert config.default_model == "haiku"
        assert config.rule_definitions == {}
        assert config.agent_tools == {}
        assert config.temp_dir == "/tmp/drift"

    def test_temp_dir_expansion(self):
        """Test that tilde is expanded in temp_dir."""
        config = DriftConfig(temp_dir="~/drift-temp")
        assert "~" not in config.temp_dir
        assert config.temp_dir.endswith("drift-temp")

    def test_get_model_for_learning_type_with_override(
        self, sample_provider_config, sample_model_config, sample_learning_type
    ):
        """Test getting model for learning type with model override."""
        sample_learning_type.phases[0].model = "sonnet"
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            rule_definitions={"incomplete_work": sample_learning_type},
        )
        model = config.get_model_for_rule("incomplete_work")
        assert model == "sonnet"

    def test_get_model_for_learning_type_without_override(
        self, sample_provider_config, sample_model_config, sample_learning_type
    ):
        """Test getting model for learning type without override uses default."""
        sample_learning_type.phases[0].model = None
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            rule_definitions={"incomplete_work": sample_learning_type},
        )
        model = config.get_model_for_rule("incomplete_work")
        assert model == "haiku"

    def test_get_model_for_nonexistent_learning_type(
        self, sample_provider_config, sample_model_config
    ):
        """Test getting model for nonexistent learning type returns default."""
        config = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
        )
        model = config.get_model_for_rule("nonexistent")
        assert model == "haiku"

    def test_get_enabled_agent_tools(self, sample_agent_config):
        """Test getting only enabled agent tools."""
        disabled_config = AgentToolConfig(
            conversation_path="/disabled/path",
            enabled=False,
        )
        config = DriftConfig(
            agent_tools={
                "claude-code": sample_agent_config,
                "disabled-tool": disabled_config,
            }
        )
        enabled = config.get_enabled_agent_tools()
        assert "claude-code" in enabled
        assert "disabled-tool" not in enabled
        assert len(enabled) == 1

    def test_get_enabled_agent_tools_empty(self):
        """Test getting enabled tools when all are disabled."""
        disabled_config = AgentToolConfig(
            conversation_path="/disabled/path",
            enabled=False,
        )
        config = DriftConfig(agent_tools={"disabled-tool": disabled_config})
        enabled = config.get_enabled_agent_tools()
        assert len(enabled) == 0


class TestProviderType:
    """Tests for ProviderType enum."""

    def test_provider_types(self):
        """Test provider type enum values."""
        assert ProviderType.BEDROCK == "bedrock"
        assert ProviderType.OPENAI == "openai"

    def test_provider_type_in_provider_config(self):
        """Test using provider type in provider config."""
        config = ProviderConfig(
            provider=ProviderType.BEDROCK,
        )
        assert config.provider == ProviderType.BEDROCK

        config = ProviderConfig(
            provider="openai",  # Can use string directly
        )
        assert config.provider == ProviderType.OPENAI


class TestConversationMode:
    """Tests for ConversationMode enum."""

    def test_conversation_modes(self):
        """Test conversation mode enum values."""
        assert ConversationMode.LATEST == "latest"
        assert ConversationMode.LAST_N_DAYS == "last_n_days"
        assert ConversationMode.ALL == "all"

    def test_mode_in_conversation_selection(self):
        """Test using mode in conversation selection."""
        selection = ConversationSelection(mode=ConversationMode.LATEST)
        assert selection.mode == ConversationMode.LATEST

        selection = ConversationSelection(mode="all")  # Can use string
        assert selection.mode == ConversationMode.ALL
