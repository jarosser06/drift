"""Configuration models for drift."""

import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    OPENAI = "openai"
    CLAUDE_CODE = "claude-code"


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


class ClientType(str, Enum):
    """Types of clients that can use validators."""

    ALL = "all"  # Validator works with all clients
    CLAUDE = "claude"  # Claude-specific validator


# Validation type pattern - must be namespaced
# e.g., "core:file_exists", "security:vulnerability_scan"
VALIDATION_TYPE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*:[a-z_][a-z0-9_]*$")


class ParamType(str, Enum):
    """Types of validation rule parameters."""

    STRING = "string"
    STRING_LIST = "string_list"
    RESOURCE_LIST = "resource_list"
    RESOURCE_CONTENT = "resource_content"
    FILE_CONTENT = "file_content"
    REGEX_PATTERN = "regex_pattern"


class ValidationRule(BaseModel):
    """A single validation rule."""

    rule_type: str = Field(
        ...,
        description="Type of validation (namespaced, e.g., 'core:file_exists')",
    )
    description: str = Field(..., description="Human-readable description of what this rule checks")

    # Typed parameters for validation
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Validation parameters with types specified "
            "(e.g., {'items': {'type': 'resource_list', 'value': 'command'}})"
        ),
    )

    # File existence/pattern rules (legacy, prefer params)
    file_path: Optional[str] = Field(None, description="File path or glob pattern to validate")

    # Regex rules (legacy, prefer params)
    pattern: Optional[str] = Field(None, description="Regular expression pattern to match")
    flags: Optional[int] = Field(None, description="Regex flags (e.g., re.MULTILINE=8)")

    # Count/size constraints (legacy, prefer params)
    min_count: Optional[int] = Field(None, description="Minimum number of files/matches")
    max_count: Optional[int] = Field(None, description="Maximum number of files/matches")
    min_size: Optional[int] = Field(None, description="Minimum file size in bytes")
    max_size: Optional[int] = Field(None, description="Maximum file size in bytes")

    # Cross-file validation (legacy, prefer params)
    source_pattern: Optional[str] = Field(
        None, description="Glob pattern for source files to check"
    )
    reference_pattern: Optional[str] = Field(
        None, description="Regex pattern to extract references from source files"
    )
    target_pattern: Optional[str] = Field(
        None, description="Glob pattern for target files that should exist"
    )

    # Error messaging (optional - validators provide defaults)
    failure_message: Optional[str] = Field(
        None,
        description=(
            "Message to display when validation fails " "(uses validator default if not provided)"
        ),
    )
    expected_behavior: Optional[str] = Field(
        None,
        description=(
            "Description of expected/correct behavior " "(uses validator default if not provided)"
        ),
    )

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

    @model_validator(mode="after")
    def migrate_legacy_fields_to_params(self) -> "ValidationRule":
        """Migrate legacy field values into params for backward compatibility.

        This allows YAML configs to use either the old field-based format or
        the new params-based format. Validators expect all parameters in params dict.
        """
        # Map of legacy field names to params keys
        legacy_field_mappings = {
            "file_path": "file_path",
            "pattern": "pattern",
            "flags": "flags",
            "min_count": "min_count",
            "max_count": "max_count",
            "min_size": "min_size",
            "max_size": "max_size",
            "source_pattern": "source_pattern",
            "reference_pattern": "reference_pattern",
            "target_pattern": "target_pattern",
        }

        # Migrate legacy fields to params if they're set and not already in params
        for field_name, param_key in legacy_field_mappings.items():
            field_value = getattr(self, field_name, None)
            if field_value is not None and param_key not in self.params:
                self.params[param_key] = field_value

        return self


class ValidationRulesConfig(BaseModel):
    """Configuration for rule-based validation."""

    rules: List[ValidationRule] = Field(..., description="List of validation rules to execute")
    scope: Literal["document_level", "project_level"] = Field(
        "document_level", description="Scope at which to execute validation"
    )
    document_bundle: DocumentBundleConfig = Field(
        ..., description="Document bundle configuration for loading files"
    )


class PhaseDefinition(BaseModel):
    """Definition of a single analysis phase."""

    name: str = Field(..., description="Name of this phase")
    type: str = Field(
        ...,
        description=(
            "Analysis type: 'prompt' for LLM-based, "
            "or validation type like 'core:file_exists', 'security:vulnerability_scan', etc."
        ),
    )
    provider: Optional[str] = Field(
        None,
        description=(
            "Provider for custom validators (format: 'module.path:ClassName'). "
            "Required for non-core types, must be None/empty for core: types."
        ),
    )
    prompt: Optional[str] = Field(None, description="Prompt instructions for prompt-based phases")
    model: Optional[str] = Field(
        None, description="Optional model override for prompt-based phases"
    )
    available_resources: List[str] = Field(
        default_factory=lambda: ["command", "skill", "agent", "main_config"],
        description="Resource types AI can request in prompt-based phases",
    )

    # For programmatic phases
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for programmatic validation phases"
    )
    file_path: Optional[str] = Field(None, description="File path for file validation phases")
    failure_message: Optional[str] = Field(None, description="Message when validation fails")
    expected_behavior: Optional[str] = Field(None, description="Description of expected behavior")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: Optional[str], info: Any) -> Optional[str]:
        """Validate provider field based on type.

        Core types (core:*) must not have a provider.
        Non-core types must have a provider.
        """
        # Access the type field from validation context
        values = info.data
        type_value = values.get("type", "")

        # Skip validation for 'prompt' type
        if type_value == "prompt":
            return v

        # Validate namespace format if type is specified
        if type_value and ":" in type_value:
            if not VALIDATION_TYPE_PATTERN.match(type_value):
                raise ValueError(
                    f"Invalid validation type format: '{type_value}'. "
                    "Must match pattern: namespace:type (e.g., 'core:file_exists')"
                )

            # Core types must not have provider
            if type_value.startswith("core:"):
                if v:
                    raise ValueError(
                        f"Core validation type '{type_value}' must not have a provider. "
                        "Set provider to None or omit it."
                    )
            # Non-core types must have provider
            else:
                if not v:
                    raise ValueError(
                        f"Custom validation type '{type_value}' requires a provider. "
                        "Specify provider as 'module.path:ClassName'."
                    )
                # Validate provider format: module.path:ClassName
                if ":" not in v or not v.split(":")[0] or not v.split(":")[1]:
                    raise ValueError(
                        f"Invalid provider format: '{v}'. Must be "
                        "'module.path:ClassName' "
                        "(e.g., 'mypackage.validators:SecurityValidator')"
                    )

        return v


class SeverityLevel(str, Enum):
    """Severity level for rule violations."""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


class RuleDefinition(BaseModel):
    """Definition of a rule for drift detection."""

    description: str = Field(..., description="What this rule checks for")
    scope: Literal["conversation_level", "project_level"] = Field(
        "project_level", description="What scope this rule analyzes (defaults to project_level)"
    )
    context: str = Field(..., description="Why this rule exists for optimization")
    requires_project_context: bool = Field(
        ..., description="Whether rule needs project info to function"
    )
    severity: Optional[SeverityLevel] = Field(
        None,
        description=(
            "Override severity level (pass/warning/fail). "
            "If None, defaults based on scope: conversation_level=warning, project_level=fail"
        ),
    )
    group_name: Optional[str] = Field(
        None,
        description=(
            "Group name for organizing rules in output. "
            "If None, uses default_group_name from config"
        ),
    )
    supported_clients: Optional[List[str]] = Field(
        None, description="Which clients this rule applies to (None = all clients)"
    )
    document_bundle: Optional[DocumentBundleConfig] = Field(
        None, description="Optional document bundle configuration for document/project scope"
    )
    validation_rules: Optional[ValidationRulesConfig] = Field(
        None, description="Optional validation rules configuration for programmatic analysis"
    )
    phases: Optional[List[PhaseDefinition]] = Field(
        None, description="Analysis phases (1 phase = single-shot, 2+ phases = multi-phase)"
    )


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


class ParallelExecutionConfig(BaseModel):
    """Configuration for parallel rule execution."""

    enabled: bool = Field(True, description="Enable parallel execution of validation rules")


class DriftConfig(BaseModel):
    """Complete drift configuration."""

    providers: Dict[str, ProviderConfig] = Field(
        default_factory=dict, description="Provider configurations"
    )
    models: Dict[str, ModelConfig] = Field(
        default_factory=dict, description="Available model definitions"
    )
    default_model: str = Field("haiku", description="Default model to use")
    default_group_name: str = Field(
        "General", description="Default group name for rules without explicit group_name"
    )
    rule_definitions: Dict[str, RuleDefinition] = Field(
        default_factory=dict, description="Rule definitions for drift detection"
    )
    agent_tools: Dict[str, AgentToolConfig] = Field(
        default_factory=dict, description="Agent tool configurations"
    )
    conversations: ConversationSelection = Field(
        default_factory=lambda: ConversationSelection(mode=ConversationMode.LATEST, days=7),
        description="Conversation selection settings",
    )
    temp_dir: str = Field("/tmp/drift", description="Temporary directory for analysis")
    cache_enabled: bool = Field(True, description="Enable LLM response caching")
    cache_dir: str = Field(".drift/cache", description="Directory for cache files")
    cache_ttl: int = Field(2592000, description="Cache TTL in seconds (default: 30 days)")
    parallel_execution: ParallelExecutionConfig = Field(
        default_factory=lambda: ParallelExecutionConfig(enabled=True),
        description="Parallel execution configuration for validation rules",
    )

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

    def get_model_for_rule(self, rule_name: str) -> str:
        """Get the model to use for a specific rule.

        Args:
            rule_name: Name of the rule

        Returns:
            Model name to use (from rule override or default)
        """
        if rule_name in self.rule_definitions:
            rule_config = self.rule_definitions[rule_name]
            # Check if first phase has a model override
            if rule_config.phases and len(rule_config.phases) > 0:
                first_phase = rule_config.phases[0]
                if first_phase.model:
                    return first_phase.model
        return self.default_model

    def get_enabled_agent_tools(self) -> Dict[str, AgentToolConfig]:
        """Get only enabled agent tools.

        Returns:
            Dictionary of enabled agent tool configurations
        """
        return {name: config for name, config in self.agent_tools.items() if config.enabled}
