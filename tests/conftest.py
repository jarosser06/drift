"""Pytest configuration and shared fixtures for drift tests."""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

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
from drift.core.types import AnalysisSummary, CompleteAnalysisResult, Conversation, Rule, Turn


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_provider_config():
    """Sample provider configuration."""
    return ProviderConfig(
        provider=ProviderType.BEDROCK,
        params={"region": "us-east-1"},
    )


@pytest.fixture
def sample_model_config():
    """Sample model configuration."""
    return ModelConfig(
        provider="bedrock",
        model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
        params={
            "max_tokens": 4096,
            "temperature": 0.0,
        },
    )


@pytest.fixture
def sample_learning_type():
    """Sample drift learning type configuration."""
    from drift.config.models import PhaseDefinition

    return RuleDefinition(
        description="AI stopped before completing the full scope of work",
        scope="conversation_level",
        context=(
            "AI stopping before completing full scope wastes user time and "
            "breaks workflow momentum."
        ),
        requires_project_context=False,
        supported_clients=None,
        phases=[
            PhaseDefinition(
                name="detection",
                type="prompt",
                prompt=(
                    "Look for instances where the AI claimed to be done but the user "
                    "had to ask for completion"
                ),
                model="haiku",
                available_resources=[],
            )
        ],
    )


@pytest.fixture
def sample_agent_config():
    """Sample agent tool configuration."""
    return AgentToolConfig(
        conversation_path="~/.claude/projects/",
        enabled=True,
    )


@pytest.fixture
def sample_drift_config(
    sample_provider_config, sample_model_config, sample_learning_type, sample_agent_config
):
    """Sample complete drift configuration."""
    return DriftConfig(
        providers={"bedrock": sample_provider_config},
        models={"haiku": sample_model_config},
        default_model="haiku",
        rule_definitions={"incomplete_work": sample_learning_type},
        agent_tools={"claude-code": sample_agent_config},
        conversations=ConversationSelection(mode=ConversationMode.LATEST, days=7),
        temp_dir="/tmp/drift-test",
    )


@pytest.fixture
def sample_turn():
    """Sample conversation turn."""
    return Turn(
        number=1,
        uuid="turn-123",
        user_message="Please implement user authentication",
        ai_message="I've implemented the login functionality.",
        timestamp=datetime.now(),
    )


@pytest.fixture
def sample_conversation(sample_turn):
    """Sample conversation."""
    return Conversation(
        session_id="session-123",
        agent_tool="claude-code",
        file_path="/path/to/conversation.jsonl",
        project_path="/path/to/project",
        turns=[sample_turn],
        started_at=datetime.now() - timedelta(hours=1),
        ended_at=datetime.now(),
        metadata={"turn_count": 1},
    )


@pytest.fixture
def sample_learning():
    """Sample learning instance."""
    return Rule(
        turn_number=1,
        turn_uuid="turn-123",
        agent_tool="claude-code",
        conversation_file="/path/to/conversation.jsonl",
        observed_behavior="Implemented only login functionality",
        expected_behavior=(
            "Implement complete authentication including login, logout, and session handling"
        ),
        rule_type="incomplete_work",
        context="User had to ask for logout and session handling separately",
    )


@pytest.fixture
def mock_complete_result():
    """Create a mock complete analysis result with no rules."""
    return CompleteAnalysisResult(
        metadata={
            "generated_at": "2024-01-01T10:00:00",
            "session_id": "test-123",
            "config_used": {"default_model": "haiku"},
        },
        summary=AnalysisSummary(
            total_conversations=1,
            total_rule_violations=0,
            conversations_without_drift=1,
            rules_checked=[],
            rules_passed=[],
            rules_warned=[],
            rules_failed=[],
            rules_errored=[],
            rule_errors={},
        ),
        results=[],
    )


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock API response."""
    return {
        "body": type(
            "Body",
            (),
            {
                "read": lambda: json.dumps(
                    {
                        "content": [
                            {
                                "text": json.dumps(
                                    [
                                        {
                                            "turn_number": 1,
                                            "observed_behavior": "Implemented only login",
                                            "expected_behavior": "Complete auth system",
                                            "resolved": True,
                                            "still_needs_action": True,
                                            "context": "Missing logout and session handling",
                                        }
                                    ]
                                )
                            }
                        ]
                    }
                ).encode()
            },
        )()
    }


@pytest.fixture
def sample_conversation_jsonl(temp_dir):
    """Create a sample Claude Code conversation JSONL file in real format."""
    conversation_file = temp_dir / "test-session.jsonl"

    # Real Claude Code format with nested message structure
    messages = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Please implement user authentication",
                    }
                ],
            },
            "timestamp": "2024-01-01T10:00:00Z",
            "cwd": "/path/to/project",
            "sessionId": "test-session",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "I've implemented the login functionality.",
                    }
                ],
            },
            "timestamp": "2024-01-01T10:01:00Z",
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What about logout and session handling?",
                    }
                ],
            },
            "timestamp": "2024-01-01T10:02:00Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "I'll add those now.",
                    }
                ],
            },
            "timestamp": "2024-01-01T10:03:00Z",
        },
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "You should have mentioned that those were missing.",
                    }
                ],
            },
            "timestamp": "2024-01-01T10:04:00Z",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "You're right, I should have implemented the complete "
                            "authentication system initially."
                        ),
                    }
                ],
            },
            "timestamp": "2024-01-01T10:05:00Z",
        },
    ]

    with open(conversation_file, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    return conversation_file


@pytest.fixture
def sample_config_yaml(temp_dir):
    """Create a sample configuration YAML file."""
    config_file = temp_dir / "config.yaml"

    config_content = """
providers:
  bedrock:
    provider: bedrock
    params:
      region: us-east-1

models:
  haiku:
    provider: bedrock
    model_id: us.anthropic.claude-3-haiku-20240307-v1:0
    params:
      max_tokens: 4096
      temperature: 0.0

default_model: haiku

rule_definitions:
  incomplete_work:
    description: AI stopped before completing work
    detection_prompt: Look for incomplete work
    analysis_method: ai_analyzed
    scope: turn_level
    context: AI stopping before completion wastes user time
    requires_project_context: false
    supported_clients: null
    explicit_signals:
      - Finish
      - Complete
    implicit_signals:
      - User asks for missing parts
    examples:
      - "User: implement auth | AI: adds login | User: what about logout?"

agent_tools:
  claude-code:
    conversation_path: ~/.claude/projects/
    enabled: true

conversations:
  mode: latest
  days: 7

temp_dir: /tmp/drift
"""

    config_file.write_text(config_content)
    return config_file


@pytest.fixture
def make_config_yaml():
    """Create custom config YAML content."""

    def _make_config(rule_types=None):
        """Generate config YAML with custom learning types.

        Args:
            rule_types: Dict of learning type names to configs

        Returns:
            String containing YAML config content
        """
        import yaml

        config = {
            "providers": {"bedrock": {"provider": "bedrock", "params": {"region": "us-east-1"}}},
            "models": {
                "haiku": {
                    "provider": "bedrock",
                    "model_id": "us.anthropic.claude-3-haiku-20240307-v1:0",
                    "params": {"max_tokens": 4096, "temperature": 0.0},
                }
            },
            "default_model": "haiku",
            "agent_tools": {
                "claude-code": {"conversation_path": "~/.claude/projects/", "enabled": True}
            },
            "conversations": {"mode": "latest", "days": 7},
            "temp_dir": "/tmp/drift",
        }

        if rule_types:
            config["rule_definitions"] = rule_types

        return yaml.dump(config, default_flow_style=False)

    return _make_config


@pytest.fixture
def claude_code_project_dir(temp_dir):
    """Create a Claude Code project directory structure with conversations in real format."""
    import os
    import time

    projects_dir = temp_dir / "claude_projects"
    projects_dir.mkdir()

    # Create project with conversation (recent)
    project1 = projects_dir / "project1"
    project1.mkdir()

    conversation1 = project1 / "session1.jsonl"
    # Real Claude Code format with nested message structure
    messages = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Create a login page",
                    }
                ],
            },
            "timestamp": datetime.now().isoformat(),
            "cwd": str(project1),
            "sessionId": "session1",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "I've created a login page.",
                    }
                ],
            },
            "timestamp": (datetime.now() + timedelta(seconds=10)).isoformat(),
        },
    ]

    with open(conversation1, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    # Create another project (old)
    project2 = projects_dir / "project2"
    project2.mkdir()

    conversation2 = project2 / "session2.jsonl"
    old_time = datetime.now() - timedelta(days=10)
    messages2 = [
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Old conversation",
                    }
                ],
            },
            "timestamp": old_time.isoformat(),
            "cwd": str(project2),
            "sessionId": "session2",
        },
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "text",
                        "text": "Old response",
                    }
                ],
            },
            "timestamp": (old_time + timedelta(seconds=10)).isoformat(),
        },
    ]

    with open(conversation2, "w") as f:
        for msg in messages2:
            f.write(json.dumps(msg) + "\n")

    # Set the modification time of the old conversation file to 10 days ago
    old_timestamp = time.time() - (10 * 24 * 60 * 60)
    os.utime(conversation2, (old_timestamp, old_timestamp))

    return projects_dir
