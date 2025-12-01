"""Default configuration for drift."""

from typing import Dict

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

# Default provider configurations
DEFAULT_PROVIDERS = {
    "bedrock": ProviderConfig(
        provider=ProviderType.BEDROCK,
        params={
            "region": "us-east-1",
            # Auth via default AWS credentials chain (no explicit config needed)
        },
    ),
}

# Default model configurations
DEFAULT_MODELS = {
    "haiku": ModelConfig(
        provider="bedrock",
        model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
        params={
            "max_tokens": 4096,
            "temperature": 0.0,
        },
    ),
    "sonnet": ModelConfig(
        provider="bedrock",
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        params={
            "max_tokens": 4096,
            "temperature": 0.0,
        },
    ),
}

# Default rule definitions (empty - define in project .drift.yaml)
DEFAULT_RULE_DEFINITIONS: Dict[str, RuleDefinition] = {}

# Default agent tool configurations
DEFAULT_AGENT_TOOLS = {
    "claude-code": AgentToolConfig(
        conversation_path="~/.claude/projects/",
        enabled=True,
    ),
}

# Default conversation selection
DEFAULT_CONVERSATION_SELECTION = ConversationSelection(
    mode=ConversationMode.LATEST,
    days=7,
)


def get_default_config() -> DriftConfig:
    """Get the default drift configuration.

    Returns:
        Default DriftConfig instance
    """
    return DriftConfig(
        providers=DEFAULT_PROVIDERS,
        models=DEFAULT_MODELS,
        default_model="haiku",
        rule_definitions=DEFAULT_RULE_DEFINITIONS,
        agent_tools=DEFAULT_AGENT_TOOLS,
        conversations=DEFAULT_CONVERSATION_SELECTION,
        temp_dir="/tmp/drift",
    )
