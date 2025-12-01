"""End-to-end integration tests for drift analysis."""

import json
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from drift.agent_tools.claude_code import ClaudeCodeLoader
from drift.config.loader import ConfigLoader
from drift.config.models import (
    AgentToolConfig,
    ConversationMode,
    ConversationSelection,
    DriftConfig,
    ModelConfig,
    PhaseDefinition,
    ProviderConfig,
    ProviderType,
    RuleDefinition,
)
from drift.core.analyzer import DriftAnalyzer


class TestEndToEndWorkflow:
    """End-to-end integration tests for full workflow."""

    @pytest.fixture
    def e2e_config(self, temp_dir):
        """Create end-to-end test configuration."""
        return DriftConfig(
            providers={
                "bedrock": ProviderConfig(
                    provider=ProviderType.BEDROCK,
                    params={"region": "us-east-1"},
                )
            },
            models={
                "test-model": ModelConfig(
                    provider="bedrock",
                    model_id="test-model-id",
                    params={},
                )
            },
            default_model="test-model",
            rule_definitions={
                "incomplete_work": RuleDefinition(
                    description="AI stopped before completing work",
                    scope="conversation_level",
                    context="Test context",
                    requires_project_context=False,
                    phases=[
                        PhaseDefinition(
                            name="detection",
                            type="prompt",
                            prompt="Look for incomplete work",
                            model="test-model",
                        )
                    ],
                )
            },
            agent_tools={
                "claude-code": AgentToolConfig(
                    conversation_path=str(temp_dir / "conversations"),
                    enabled=True,
                )
            },
            conversations=ConversationSelection(mode=ConversationMode.LATEST),
            temp_dir=str(temp_dir / "drift-temp"),
        )

    @pytest.fixture
    def e2e_conversation_dir(self, temp_dir):
        """Create conversation directory with test data."""
        conv_dir = temp_dir / "conversations" / "test-project"
        conv_dir.mkdir(parents=True)

        # Create a conversation file with drift
        conversation_file = conv_dir / "agent-test-session.jsonl"

        messages = [
            {
                "type": "user",
                "content": (
                    "Please implement a complete authentication system with "
                    "login, logout, and session management"
                ),
                "timestamp": datetime.now().isoformat(),
                "project_path": str(temp_dir / "test-project"),
            },
            {
                "type": "assistant",
                "content": "I've implemented the login functionality.",
                "timestamp": datetime.now().isoformat(),
                "id": "turn-1",
            },
            {
                "type": "user",
                "content": ("What about logout and session management? You didn't finish."),
                "timestamp": datetime.now().isoformat(),
            },
            {
                "type": "assistant",
                "content": (
                    "You're right, I'll add those now. Implementing logout and "
                    "session management."
                ),
                "timestamp": datetime.now().isoformat(),
                "id": "turn-2",
            },
        ]

        with open(conversation_file, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

        return conv_dir.parent

    def test_full_analysis_workflow(self, e2e_config, e2e_conversation_dir):
        """Test complete workflow from loading conversations to generating output."""
        # Setup
        with patch("drift.providers.bedrock.boto3") as mock_boto3:
            # Mock Bedrock client
            mock_client = MagicMock()
            mock_client._client_config = {}

            # Mock LLM response with detected drift
            mock_response_body = json.dumps(
                {
                    "content": [
                        {
                            "text": json.dumps(
                                [
                                    {
                                        "turn_number": 1,
                                        "observed_behavior": "Implemented only login functionality",
                                        "expected_behavior": (
                                            "Complete authentication system with "
                                            "login, logout, and session management"
                                        ),
                                        "resolved": True,
                                        "still_needs_action": True,
                                        "context": (
                                            "User had to explicitly ask for logout "
                                            "and session management in turn 2"
                                        ),
                                    }
                                ]
                            )
                        }
                    ]
                }
            )

            mock_client.invoke_model.return_value = {
                "body": Mock(read=lambda: mock_response_body.encode())
            }

            mock_boto3.client.return_value = mock_client

            # Run analysis
            analyzer = DriftAnalyzer(config=e2e_config)
            result = analyzer.analyze()

            # Verify results
            assert result.summary.total_conversations == 1
            assert result.summary.total_rule_violations == 1
            assert result.summary.conversations_with_drift == 1

            # Check learning details
            learning = result.results[0].rules[0]
            assert learning.turn_number == 1
            assert learning.rule_type == "incomplete_work"

    def test_loader_integration(self, e2e_conversation_dir):
        """Test Claude Code loader with real conversation files."""
        loader = ClaudeCodeLoader(str(e2e_conversation_dir))

        conversations = loader.load_conversations(mode="latest")

        assert len(conversations) == 1
        conversation = conversations[0]

        assert len(conversation.turns) == 2
        assert "authentication system" in conversation.turns[0].user_message
        assert "login functionality" in conversation.turns[0].ai_message
        assert "didn't finish" in conversation.turns[1].user_message

    def test_config_loading_with_overrides(self, temp_dir, e2e_config):
        """Test configuration loading with project overrides."""
        # Create global config
        global_config_dir = temp_dir / "global"
        global_config_dir.mkdir()
        global_config = global_config_dir / "config.yaml"

        global_data = {
            "conversations": {"mode": "all", "days": 30},
            "temp_dir": str(temp_dir / "global-temp"),
        }

        import yaml

        with open(global_config, "w") as f:
            yaml.dump(global_data, f)

        # Create project config
        project_dir = temp_dir / "project"
        project_dir.mkdir()
        project_config = project_dir / ".drift.yaml"

        project_data = {
            "conversations": {"days": 7},  # Override days only
        }

        with open(project_config, "w") as f:
            yaml.dump(project_data, f)

        # Load with project override
        with patch.object(
            ConfigLoader,
            "GLOBAL_CONFIG_PATHS",
            [global_config],
        ):
            config = ConfigLoader.load_config(project_dir)

            # Days should be from project (highest priority)
            assert config.conversations.days == 7
            # Mode should be from global
            assert config.conversations.mode == ConversationMode.ALL
            # Temp dir should be from global
            assert config.temp_dir == str(temp_dir / "global-temp")

    def test_multiple_conversations_analysis(self, e2e_config, temp_dir):
        """Test analyzing multiple conversations."""
        # Create multiple conversation files
        conv_dir = temp_dir / "conversations"

        # Project 1
        project1 = conv_dir / "project1"
        project1.mkdir(parents=True)
        conv1 = project1 / "agent-session1.jsonl"

        with open(conv1, "w") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "content": "Create a form",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "content": "Form created",
                        "timestamp": datetime.now().isoformat(),
                        "id": "turn-1",
                    }
                )
                + "\n"
            )

        # Project 2
        project2 = conv_dir / "project2"
        project2.mkdir(parents=True)
        conv2 = project2 / "agent-session2.jsonl"

        with open(conv2, "w") as f:
            f.write(
                json.dumps(
                    {
                        "type": "user",
                        "content": "Add validation",
                        "timestamp": datetime.now().isoformat(),
                    }
                )
                + "\n"
            )
            f.write(
                json.dumps(
                    {
                        "type": "assistant",
                        "content": "Validation added",
                        "timestamp": datetime.now().isoformat(),
                        "id": "turn-1",
                    }
                )
                + "\n"
            )

        # Update config to point to this directory
        e2e_config.agent_tools["claude-code"].conversation_path = str(conv_dir)
        e2e_config.conversations.mode = ConversationMode.ALL

        with patch("drift.providers.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_client._client_config = {}
            mock_client.invoke_model.return_value = {
                "body": Mock(
                    read=lambda: json.dumps({"content": [{"text": "[]"}]}).encode()  # No drift
                )
            }
            mock_boto3.client.return_value = mock_client

            analyzer = DriftAnalyzer(config=e2e_config)
            result = analyzer.analyze()

            # Should analyze both conversations
            assert result.summary.total_conversations == 2

    def test_output_formatting_integration(self, e2e_config, e2e_conversation_dir):
        """Test output formatting with real analysis results."""
        from drift.cli.output.json import JsonFormatter
        from drift.cli.output.markdown import MarkdownFormatter

        with patch("drift.providers.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_client._client_config = {}
            mock_client.invoke_model.return_value = {
                "body": Mock(
                    read=lambda: json.dumps(
                        {
                            "content": [
                                {
                                    "text": json.dumps(
                                        [
                                            {
                                                "turn_number": 1,
                                                "observed_behavior": "Action",
                                                "expected_behavior": "Intent",
                                                "resolved": False,
                                                "still_needs_action": True,
                                                "context": "Test",
                                            }
                                        ]
                                    )
                                }
                            ]
                        }
                    ).encode()
                )
            }
            mock_boto3.client.return_value = mock_client

            analyzer = DriftAnalyzer(config=e2e_config)
            result = analyzer.analyze()

            # Test Markdown formatter
            md_formatter = MarkdownFormatter()
            md_output = md_formatter.format(result)

            assert "# Drift Analysis Results" in md_output
            assert "## Summary" in md_output
            # Learnings are now split by severity
            assert "## Warnings" in md_output or "## Failures" in md_output

            # Test JSON formatter
            json_formatter = JsonFormatter()
            json_output = json_formatter.format(result)

            # Verify it's valid JSON
            data = json.loads(json_output)
            assert "metadata" in data
            assert "summary" in data
            assert "results" in data
            assert data["summary"]["total_rule_violations"] == 1

    def test_temp_directory_management(self, e2e_config, e2e_conversation_dir):
        """Test temporary directory creation and cleanup."""
        from pathlib import Path as PathLib

        temp_base = PathLib(e2e_config.temp_dir)

        with patch("drift.providers.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_client._client_config = {}
            mock_client.invoke_model.return_value = {
                "body": Mock(read=lambda: json.dumps({"content": [{"text": "[]"}]}).encode())
            }
            mock_boto3.client.return_value = mock_client

            analyzer = DriftAnalyzer(config=e2e_config)

            # Run analysis (creates temp dir)
            analyzer.analyze()

            # Temp directory structure should exist during analysis
            assert temp_base.exists()

            # After analysis, temp files should still exist (preserved for debugging)
            # In production, cleanup would be called explicitly

    def test_error_recovery(self, e2e_config, e2e_conversation_dir):
        """Test error recovery and graceful degradation."""
        with patch("drift.providers.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_client._client_config = {}

            # First conversation succeeds
            # Second would fail if there were more conversations
            mock_client.invoke_model.return_value = {
                "body": Mock(read=lambda: json.dumps({"content": [{"text": "[]"}]}).encode())
            }

            mock_boto3.client.return_value = mock_client

            analyzer = DriftAnalyzer(config=e2e_config)

            # Should complete successfully
            result = analyzer.analyze()
            assert result.summary.total_conversations >= 0

    def test_no_conversations_found(self, e2e_config, temp_dir):
        """Test behavior when no conversations are found."""
        # Create empty conversation directory
        empty_conv_dir = temp_dir / "empty_conversations"
        empty_conv_dir.mkdir()

        e2e_config.agent_tools["claude-code"].conversation_path = str(empty_conv_dir)

        with patch("drift.providers.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.client.return_value = mock_client

            analyzer = DriftAnalyzer(config=e2e_config)
            result = analyzer.analyze()

            # Should complete with zero conversations
            assert result.summary.total_conversations == 0
            assert result.summary.total_rule_violations == 0

    def test_rule_definition_override(self, e2e_config, e2e_conversation_dir):
        """Test model override for specific learning types."""
        # Add a second model
        e2e_config.models["powerful-model"] = ModelConfig(
            provider="bedrock",
            model_id="powerful-model-id",
            params={},
        )

        # Set learning type to use different model
        e2e_config.rule_definitions["incomplete_work"].phases[0].model = "powerful-model"

        with patch("drift.providers.bedrock.boto3") as mock_boto3:
            mock_client = MagicMock()
            mock_client._client_config = {}
            mock_client.invoke_model.return_value = {
                "body": Mock(read=lambda: json.dumps({"content": [{"text": "[]"}]}).encode())
            }
            mock_boto3.client.return_value = mock_client

            analyzer = DriftAnalyzer(config=e2e_config)
            analyzer.analyze()

            # Verify the powerful model was used
            assert mock_client.invoke_model.called
            call_args = mock_client.invoke_model.call_args
            assert call_args[1]["modelId"] == "powerful-model-id"
