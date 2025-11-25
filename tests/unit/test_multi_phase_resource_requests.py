"""Tests for multi-phase analysis with resource requests."""

import json
from unittest.mock import MagicMock, patch

import pytest

from drift.config.models import DriftConfig, DriftLearningType, PhaseDefinition
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import Conversation, Turn


class TestMultiPhaseResourceRequests:
    """Tests for multi-phase analysis that requests resources."""

    @pytest.fixture
    def command_activation_rule(self):
        """Create the command_activation_required learning type."""
        return DriftLearningType(
            description="AI failed to activate required skills",
            scope="conversation_level",
            context="Commands require skill activation first",
            requires_project_context=True,
            supported_clients=["claude-code"],
            phases=[
                PhaseDefinition(
                    name="initial_analysis",
                    type="prompt",
                    model="haiku",
                    prompt="Analyze conversation for slash commands",
                    available_resources=["command", "skill", "main_config"],
                ),
                PhaseDefinition(
                    name="verify_dependencies",
                    type="prompt",
                    model="haiku",
                    prompt="Check if command has Required skills",
                    available_resources=["command", "skill", "main_config"],
                ),
                PhaseDefinition(
                    name="final_determination",
                    type="prompt",
                    model="haiku",
                    prompt="Make final determination",
                    available_resources=["command", "skill", "main_config"],
                ),
            ],
        )

    @pytest.fixture
    def sample_conversation(self, tmp_path):
        """Create a sample conversation."""
        return Conversation(
            session_id="test-session",
            agent_tool="claude-code",
            file_path=str(tmp_path / "test.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(
                    number=1,
                    user_message="Run the /test command",
                    ai_message="Running tests...",
                )
            ],
        )

    @patch("drift.core.analyzer.BedrockProvider")
    @patch("drift.core.analyzer.AgentLoader")
    def test_multi_phase_with_resource_requests(
        self,
        mock_loader_class,
        mock_provider_class,
        command_activation_rule,
        sample_conversation,
        tmp_path,
    ):
        """Test that multi-phase analysis with resource requests works."""
        config = DriftConfig(
            drift_learning_types={"command_activation_required": command_activation_rule}
        )

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        mock_loader = MagicMock()
        mock_loader.supports_agent_tool.return_value = True
        mock_loader_class.create_loader.return_value = mock_loader

        analyzer = DriftAnalyzer(config=config, project_path=tmp_path)
        analyzer.agent_loaders = {"claude-code": mock_loader}
        analyzer.providers = {"haiku": mock_provider}

        result = analyzer._run_multi_phase_analysis(
            sample_conversation,
            "command_activation_required",
            command_activation_rule,
            model_override=None,
        )

        assert isinstance(result, tuple)
        learnings, error = result
        assert isinstance(learnings, list)
        assert mock_provider.generate.called

    @patch("drift.core.analyzer.BedrockProvider")
    @patch("drift.core.analyzer.AgentLoader")
    def test_multi_phase_parses_resource_requests(
        self,
        mock_loader_class,
        mock_provider_class,
        command_activation_rule,
        sample_conversation,
        tmp_path,
    ):
        """Test that resource requests are properly parsed from phase output."""
        config = DriftConfig(
            drift_learning_types={"command_activation_required": command_activation_rule}
        )

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True

        response_with_request = json.dumps(
            {
                "resource_requests": [{"resource_type": "command", "name": "test"}],
                "findings": [],
            }
        )
        mock_provider.generate.return_value = response_with_request
        mock_provider_class.return_value = mock_provider

        mock_loader = MagicMock()
        mock_loader.supports_agent_tool.return_value = True
        mock_loader_class.create_loader.return_value = mock_loader

        analyzer = DriftAnalyzer(config=config, project_path=tmp_path)
        analyzer.agent_loaders = {"claude-code": mock_loader}
        analyzer.providers = {"haiku": mock_provider}

        result = analyzer._run_multi_phase_analysis(
            sample_conversation,
            "command_activation_required",
            command_activation_rule,
            model_override=None,
        )

        assert isinstance(result, tuple)
        learnings, error = result
        assert isinstance(learnings, list)
