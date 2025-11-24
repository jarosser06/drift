"""Configuration models for drift."""

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


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


class BundleStrategy(str, Enum):
    """Strategy for grouping files into bundles."""

    INDIVIDUAL = "individual"
    COLLECTION = "collection"


class DocumentBundleConfig(BaseModel):
    """Configuration for document bundle loading."""

    bundle_type: str = Field(..., description="Type of bundle (skill, command, agent, mixed, etc.)")
    file_patterns: List[str] = Field(
        ..., description="Glob patterns for files to include (e.g., '.claude/skills/*/SKILL.md')"
    )
    bundle_strategy: BundleStrategy = Field(..., description="How to group matching files")
    resource_patterns: List[str] = Field(
        default_factory=list,
        description="Optional glob patterns for supporting files within bundle directories",
    )


class ValidationType(str, Enum):
    """Types of validation rules."""

    FILE_EXISTS = "file_exists"
    FILE_NOT_EXISTS = "file_not_exists"
    REGEX_MATCH = "regex_match"
    REGEX_NOT_MATCH = "regex_not_match"
    FILE_COUNT = "file_count"
    FILE_SIZE = "file_size"
    CROSS_FILE_REFERENCE = "cross_file_reference"


class ValidationRule(BaseModel):
    """A single validation rule."""

    rule_type: ValidationType = Field(..., description="Type of validation to perform")
    description: str = Field(..., description="Human-readable description of what this rule checks")

    # File existence/pattern rules
    file_path: Optional[str] = Field(None, description="File path or glob pattern to validate")

    # Regex rules
    pattern: Optional[str] = Field(None, description="Regular expression pattern to match")
    flags: Optional[int] = Field(None, description="Regex flags (e.g., re.MULTILINE=8)")

    # Count/size constraints
    min_count: Optional[int] = Field(None, description="Minimum number of files/matches")
    max_count: Optional[int] = Field(None, description="Maximum number of files/matches")
    min_size: Optional[int] = Field(None, description="Minimum file size in bytes")
    max_size: Optional[int] = Field(None, description="Maximum file size in bytes")

    # Cross-file validation
    source_pattern: Optional[str] = Field(
        None, description="Glob pattern for source files to check"
    )
    reference_pattern: Optional[str] = Field(
        None, description="Regex pattern to extract references from source files"
    )
    target_pattern: Optional[str] = Field(
        None, description="Glob pattern for target files that should exist"
    )

    # Error messaging
    failure_message: str = Field(..., description="Message to display when validation fails")
    expected_behavior: str = Field(..., description="Description of expected/correct behavior")

    @field_validator("pattern")
    @classmethod
    def validate_regex_pattern(cls, v: Optional[str]) -> Optional[str]:
        """Validate that regex pattern is valid."""
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v

    @field_validator("reference_pattern")
    @classmethod
    def validate_reference_pattern(cls, v: Optional[str]) -> Optional[str]:
        """Validate that reference regex pattern is valid."""
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid reference regex pattern: {e}")
        return v


class ValidationRulesConfig(BaseModel):
    """Configuration for rule-based validation."""

    rules: List[ValidationRule] = Field(..., description="List of validation rules to execute")
    scope: Literal["document_level", "project_level"] = Field(
        "document_level", description="Scope at which to execute validation"
    )
    document_bundle: DocumentBundleConfig = Field(
        ..., description="Document bundle configuration for loading files"
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
    scope: Literal["turn_level", "conversation_level", "document_level", "project_level"] = Field(
        ..., description="What scope this rule analyzes"
    )
    context: str = Field(..., description="Why this rule exists for optimization")
    requires_project_context: bool = Field(
        ..., description="Whether rule needs project info to function"
    )
    supported_clients: Optional[List[str]] = Field(
        None, description="Which clients this rule applies to (None = all clients)"
    )
    model: Optional[str] = Field(None, description="Optional model override for this type")
    document_bundle: Optional[DocumentBundleConfig] = Field(
        None, description="Optional document bundle configuration for document/project scope"
    )
    validation_rules: Optional[ValidationRulesConfig] = Field(
        None, description="Optional validation rules configuration for programmatic analysis"
    )

    @model_validator(mode="after")
    def validate_analysis_method_consistency(self) -> "DriftLearningType":
        """Validate that validation_rules is consistent with analysis_method."""
        if self.analysis_method == "programmatic" and self.validation_rules is None:
            raise ValueError(
                "validation_rules must be provided when " "analysis_method is 'programmatic'"
            )

        if self.analysis_method == "ai_analyzed" and self.validation_rules is not None:
            raise ValueError(
                "validation_rules should not be provided when " "analysis_method is 'ai_analyzed'"
            )

        return self


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
