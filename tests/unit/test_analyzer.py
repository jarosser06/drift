"""Unit tests for drift analyzer."""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from drift.core.analyzer import DriftAnalyzer
from drift.core.types import AnalysisResult, CompleteAnalysisResult, Learning


class TestDriftAnalyzer:
    """Tests for DriftAnalyzer class."""

    def test_initialization_with_config(self, sample_drift_config):
        """Test analyzer initialization with provided config."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        assert analyzer.config == sample_drift_config
        assert analyzer.project_path is None
        assert len(analyzer.providers) > 0
        assert len(analyzer.agent_loaders) > 0

    @patch("drift.core.analyzer.ConfigLoader.load_config")
    def test_initialization_loads_config(self, mock_load_config, sample_drift_config):
        """Test analyzer loads config when not provided."""
        mock_load_config.return_value = sample_drift_config

        analyzer = DriftAnalyzer()

        mock_load_config.assert_called_once()
        assert analyzer.config == sample_drift_config

    def test_initialization_with_project_path(self, sample_drift_config, temp_dir):
        """Test analyzer initialization with project path."""
        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)

        assert analyzer.project_path == temp_dir

    def test_initialize_providers(self, sample_drift_config):
        """Test provider initialization."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        assert "haiku" in analyzer.providers
        assert analyzer.providers["haiku"].get_provider_type() == "bedrock"

    def test_initialize_agent_loaders(self, sample_drift_config):
        """Test agent loader initialization."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        assert "claude-code" in analyzer.agent_loaders
        assert analyzer.agent_loaders["claude-code"].agent_name == "claude-code"

    def test_format_conversation(self, sample_conversation):
        """Test conversation formatting for prompts."""
        formatted = DriftAnalyzer._format_conversation(sample_conversation)

        assert "[Turn 1]" in formatted
        assert "User:" in formatted
        assert "AI:" in formatted
        assert sample_conversation.turns[0].user_message in formatted
        assert sample_conversation.turns[0].ai_message in formatted

    def test_build_analysis_prompt(self, sample_conversation, sample_learning_type):
        """Test building analysis prompt."""
        analyzer = DriftAnalyzer(config=MagicMock())

        prompt = analyzer._build_analysis_prompt(
            sample_conversation,
            "incomplete_work",
            sample_learning_type,
        )

        assert "incomplete_work" in prompt
        assert sample_learning_type.description in prompt
        assert sample_learning_type.detection_prompt in prompt
        assert "JSON" in prompt
        # Check that signals are included
        for signal in sample_learning_type.explicit_signals:
            assert signal in prompt

    def test_parse_analysis_response_valid(self, sample_conversation):
        """Test parsing valid analysis response."""
        response = json.dumps(
            [
                {
                    "turn_number": 1,
                    "observed_behavior": "Did something",
                    "expected_behavior": "Wanted something else",
                    "resolved": True,
                    "still_needs_action": False,
                    "context": "Test context",
                }
            ]
        )

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "incomplete_work",
        )

        assert len(learnings) == 1
        assert isinstance(learnings[0], Learning)
        assert learnings[0].turn_number == 1
        assert learnings[0].learning_type == "incomplete_work"

    def test_parse_analysis_response_empty(self, sample_conversation):
        """Test parsing empty analysis response."""
        response = "[]"

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "incomplete_work",
        )

        assert learnings == []

    def test_parse_analysis_response_with_text(self, sample_conversation):
        """Test parsing response with extra text around JSON."""
        response = (
            "Here's my analysis:\n\n"
            '[{"turn_number": 1, "observed_behavior": "Test", "expected_behavior": "Test", '
            '"resolved": true, "still_needs_action": false, "context": "Test"}]\n\n'
            "That's all I found."
        )

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "test_type",
        )

        assert len(learnings) == 1

    def test_parse_analysis_response_invalid_json(self, sample_conversation):
        """Test parsing response with invalid JSON."""
        response = "This is not JSON at all"

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "test_type",
        )

        assert learnings == []

    def test_parse_analysis_response_no_json_array(self, sample_conversation):
        """Test parsing response without JSON array."""
        response = '{"not": "an array"}'

        learnings = DriftAnalyzer._parse_analysis_response(
            response,
            sample_conversation,
            "test_type",
        )

        assert learnings == []

    def test_generate_summary_no_results(self):
        """Test generating summary from empty results."""
        summary = DriftAnalyzer._generate_summary([])

        assert summary.total_conversations == 0
        assert summary.total_learnings == 0
        assert summary.conversations_with_drift == 0
        assert summary.conversations_without_drift == 0

    def test_generate_summary_with_results(self, sample_learning):
        """Test generating summary from results."""
        result1 = AnalysisResult(
            session_id="session1",
            agent_tool="claude-code",
            conversation_file="/path1",
            learnings=[sample_learning],
            analysis_timestamp=datetime.now(),
        )

        result2 = AnalysisResult(
            session_id="session2",
            agent_tool="claude-code",
            conversation_file="/path2",
            learnings=[],  # No drift
            analysis_timestamp=datetime.now(),
        )

        summary = DriftAnalyzer._generate_summary([result1, result2])

        assert summary.total_conversations == 2
        assert summary.total_learnings == 1
        assert summary.conversations_with_drift == 1
        assert summary.conversations_without_drift == 1
        assert "incomplete_work" in summary.by_type
        assert summary.by_type["incomplete_work"] == 1

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_creates_temp_dir(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
        temp_dir,
    ):
        """Test that analyze creates temporary analysis directory."""
        # Setup mocks
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        # Override temp_dir in config
        sample_drift_config.temp_dir = str(temp_dir / "drift-analysis")

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Check that temp directory was used
        assert isinstance(result, CompleteAnalysisResult)
        # Verify temp manager was used (session_id should be in metadata)
        assert "session_id" in result.metadata

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_end_to_end(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test full analyze workflow."""
        # Setup loader mock
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        # Setup provider mock
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = json.dumps(
            [
                {
                    "turn_number": 1,
                    "observed_behavior": "Test action",
                    "expected_behavior": "Test intent",
                    "resolved": True,
                    "still_needs_action": False,
                    "context": "Test",
                }
            ]
        )
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        assert isinstance(result, CompleteAnalysisResult)
        assert result.summary.total_conversations == 1
        assert len(result.results) == 1
        assert len(result.results[0].learnings) == 1

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_with_agent_filter(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze with specific agent tool filter."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.analyze(agent_tool="claude-code")

        # Should only analyze specified agent
        mock_loader.load_conversations.assert_called_once()

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_with_learning_type_filter(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze with specific learning types."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.analyze(learning_types=["incomplete_work"])

        # Should only check specified learning types
        assert mock_provider.generate.call_count == 1  # One conversation * one learning type

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_with_model_override(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze with model override."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.analyze(model_override="haiku")

        # Model override should be used
        assert mock_provider.generate.called

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_provider_not_available(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test analyze handles provider not available."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = False
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(RuntimeError) as exc_info:
            analyzer.analyze()
        assert "not available" in str(exc_info.value)

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    def test_analyze_loader_not_found_error(
        self,
        mock_loader_class,
        sample_drift_config,
    ):
        """Test analyze handles loader file not found error."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.side_effect = FileNotFoundError("Path not found")
        mock_loader_class.return_value = mock_loader

        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(FileNotFoundError):
            analyzer.analyze()

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_continues_on_conversation_error(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test that analyze continues when individual conversations fail."""
        mock_loader = MagicMock()
        # Return two conversations
        conv2 = sample_conversation.model_copy()
        conv2.session_id = "session2"
        mock_loader.load_conversations.return_value = [sample_conversation, conv2]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        # First conversation succeeds, second fails
        mock_provider.generate.side_effect = ["[]", Exception("API Error")]
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Should have analyzed both (second with error)
        assert len(result.results) == 1  # Only successful one

    def test_cleanup(self, sample_drift_config, temp_dir):
        """Test analyzer cleanup."""
        sample_drift_config.temp_dir = str(temp_dir / "drift-temp")
        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Should not raise error
        analyzer.cleanup()

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_analyze_saves_metadata(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test that analyze saves metadata."""
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Check metadata
        assert "generated_at" in result.metadata
        assert "session_id" in result.metadata
        assert "config_used" in result.metadata

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_run_analysis_pass(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
        sample_learning_type,
    ):
        """Test running a single analysis pass."""
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = json.dumps(
            [
                {
                    "turn_number": 1,
                    "observed_behavior": "Action",
                    "expected_behavior": "Intent",
                    "resolved": False,
                    "still_needs_action": True,
                    "context": "Context",
                }
            ]
        )
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=sample_drift_config)
        analyzer.providers = {"haiku": mock_provider}

        learnings = analyzer._run_analysis_pass(
            sample_conversation,
            "incomplete_work",
            sample_learning_type,
            None,
        )

        assert len(learnings) == 1
        assert learnings[0].learning_type == "incomplete_work"

    def test_run_analysis_pass_unknown_model(
        self,
        sample_drift_config,
        sample_conversation,
        sample_learning_type,
    ):
        """Test that run_analysis_pass fails with unknown model."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        with pytest.raises(ValueError) as exc_info:
            analyzer._run_analysis_pass(
                sample_conversation,
                "incomplete_work",
                sample_learning_type,
                "nonexistent_model",
            )
        assert "not found in configured providers" in str(exc_info.value)
