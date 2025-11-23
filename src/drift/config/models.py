"""Configuration models for drift."""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    BEDROCK = "bedrock"
    OPENAI = "openai"


class ProviderConfig(BaseModel):
    """Provider-specific configuration (auth, region, etc)."""

    provider: ProviderType = Field(..., description="Provider type (bedrock, openai)")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific parameters (e.g., region, auth, endpoints)",
    )


class ModelConfig(BaseModel):
    """Configuration for a specific LLM model."""

    provider: str = Field(..., description="Name of provider config to use")
    model_id: str = Field(..., description="Model identifier for the provider")
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Model-specific parameters (e.g., temperature, max_tokens, top_k)",
    )


class DriftLearningType(BaseModel):
    """Definition of a drift learning type."""

    description: str = Field(..., description="What this learning type represents")
    detection_prompt: str = Field(
        ..., description="Prompt instructions for detecting this drift type"
    )
    analysis_method: Literal["programmatic", "ai_analyzed"] = Field(
        ..., description="How this rule is evaluated"
    )
    scope: Literal["turn_level", "conversation_level"] = Field(
        ..., description="What scope this rule analyzes"
    )
    context: str = Field(..., description="Why this rule exists for optimization")
    requires_project_context: bool = Field(
        ..., description="Whether rule needs project info to function"
    )
    supported_clients: Optional[List[str]] = Field(
        None, description="Which clients this rule applies to (None = all clients)"
    )
    explicit_signals: List[str] = Field(
        default_factory=list, description="Explicit phrases indicating this drift"
    )
    implicit_signals: List[str] = Field(
        default_factory=list, description="Behavioral patterns indicating this drift"
    )
    examples: List[str] = Field(default_factory=list, description="Example conversations")
    model: Optional[str] = Field(None, description="Optional model override for this type")


class AgentToolConfig(BaseModel):
    """Configuration for an agent tool."""

    conversation_path: str = Field(..., description="Path to conversation files")
    enabled: bool = Field(True, description="Whether this agent tool is enabled")

    @field_validator("conversation_path")
    @classmethod
    def expand_path(cls, v: str) -> str:
        """Expand user home directory in path."""
        return str(Path(v).expanduser())


class ConversationMode(str, Enum):
    """Mode for selecting which conversations to analyze."""

    LATEST = "latest"
    LAST_N_DAYS = "last_n_days"
    ALL = "all"


class ConversationSelection(BaseModel):
    """Configuration for conversation selection."""

    mode: ConversationMode = Field(
        ConversationMode.LATEST, description="How to select conversations"
    )
    days: int = Field(7, description="Number of days (for last_n_days mode)")

    @field_validator("days")
    @classmethod
    def validate_days(cls, v: int) -> int:
        """Validate days is positive."""
        if v <= 0:
            raise ValueError("days must be positive")
        return v


class DriftConfig(BaseModel):
    """Complete drift configuration."""

    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Provider configurations"
    )
    models: Dict[str, ModelConfig] = Field(
        default_factory=dict, description="Available model definitions"
    )
    default_model: str = Field("haiku", description="Default model to use")
    drift_learning_types: Dict[str, DriftLearningType] = Field(
        default_factory=dict, description="Drift learning type definitions"
    )
    agent_tools: Dict[str, AgentToolConfig] = Field(
        default_factory=dict, description="Agent tool configurations"
    )
    conversations: ConversationSelection = Field(
        default_factory=lambda: ConversationSelection(mode=ConversationMode.LATEST, days=7),
        description="Conversation selection settings",
    )
    temp_dir: str = Field("/tmp/drift", description="Temporary directory for analysis")

    @field_validator("default_model")
    @classmethod
    def validate_default_model(cls, v: str, info: Any) -> str:
        """Validate default model exists in models dict."""
        # Note: validation will happen after full object construction
        # So we can't validate against models here. Will validate in loader.
        return v

    @field_validator("temp_dir")
    @classmethod
    def expand_temp_dir(cls, v: str) -> str:
        """Expand user home directory in temp dir path."""
        return str(Path(v).expanduser())

    def get_model_for_learning_type(self, learning_type: str) -> str:
        """Get the model to use for a specific learning type.

        Args:
            learning_type: Name of the drift learning type

        Returns:
            Model name to use (from learning type override or default)
        """
        if learning_type in self.drift_learning_types:
            type_config = self.drift_learning_types[learning_type]
            if type_config.model:
                return type_config.model
        return self.default_model

    def get_enabled_agent_tools(self) -> Dict[str, AgentToolConfig]:
        """Get only enabled agent tools.

        Returns:
            Dictionary of enabled agent tool configurations
        """
        return {name: config for name, config in self.agent_tools.items() if config.enabled}
