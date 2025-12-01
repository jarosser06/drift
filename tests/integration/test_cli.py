"""Integration tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest

from drift.cli.main import main
from drift.core.types import AnalysisSummary, CompleteAnalysisResult
from tests.mock_provider import MockProvider
from tests.test_utils import CliRunner


@pytest.fixture
def cli_runner():
    """Create CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_complete_result():
    """Create a mock complete analysis result."""
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
        ),
        results=[],
    )


class TestAnalyzeCommand:
    """Tests for the analyze CLI command."""

    def test_version_option(self, cli_runner):
        """Test --version option."""
        result = cli_runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "drift version" in result.stdout

    def test_help_option(self, cli_runner):
        """Test --help option."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "drift" in result.stdout.lower()
        assert "analyzer" in result.stdout.lower()

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    @patch("drift.config.loader.ConfigLoader.load_config")
    def test_analyze_default_options(
        self,
        mock_load_config,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test analyze command with default options."""
        mock_load_config.return_value = sample_drift_config

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        assert result.exit_code == 0
        assert "# Drift Analysis Results" in result.stdout
        assert "Total conversations: 0" in result.stdout  # No actual conversations loaded

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_json_format(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with JSON format."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--format", "json", "--project", str(temp_dir)])

        assert result.exit_code == 0
        assert '"metadata"' in result.stdout
        assert '"summary"' in result.stdout

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_with_agent_tool_filter(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with agent tool filter."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            main,
            ["--scope", "conversation", "--agent-tool", "claude-code", "--project", str(temp_dir)],
        )

        assert result.exit_code == 0
        call_kwargs = mock_analyzer.analyze.call_args[1]
        assert call_kwargs["agent_tool"] == "claude-code"

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_with_learning_types(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with learning types filter."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            main,
            ["--scope", "conversation", "--rules", "incomplete_work", "--project", str(temp_dir)],
        )

        assert result.exit_code == 0
        call_kwargs = mock_analyzer.analyze.call_args[1]
        assert call_kwargs["rule_types"] == ["incomplete_work"]

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_with_multiple_types(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with multiple learning types."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            main,
            ["--rules", "incomplete_work,wrong_assumption", "--project", str(temp_dir)],
        )

        # Should fail because wrong_assumption is not in sample config
        assert result.exit_code == 1
        assert "Unknown rules" in result.stderr

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_latest_option(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with --latest option."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--latest", "--project", str(temp_dir)])

        assert result.exit_code == 0
        # Config should be modified to use latest mode
        config = mock_config_loader.load_config.return_value
        assert config.conversations.mode.value == "latest"

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_days_option(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with --days option."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--days", "5", "--project", str(temp_dir)])

        assert result.exit_code == 0
        config = mock_config_loader.load_config.return_value
        assert config.conversations.mode.value == "last_n_days"
        assert config.conversations.days == 5

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_all_option(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with --all option."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--all", "--project", str(temp_dir)])

        assert result.exit_code == 0
        config = mock_config_loader.load_config.return_value
        assert config.conversations.mode.value == "all"

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_conflicting_mode_options(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test that conflicting mode options are rejected."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        result = cli_runner.invoke(
            main,
            ["--latest", "--all", "--project", str(temp_dir)],
        )

        assert result.exit_code == 1
        assert "Only one of" in result.stderr

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_with_model_override(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with model override."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            main,
            ["--scope", "conversation", "--model", "haiku", "--project", str(temp_dir)],
        )

        assert result.exit_code == 0
        call_kwargs = mock_analyzer.analyze.call_args[1]
        assert call_kwargs["model_override"] == "haiku"

    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_invalid_project_path(
        self,
        mock_config_loader,
        cli_runner,
    ):
        """Test analyze command with invalid project path."""
        mock_config_loader.ensure_global_config_exists.return_value = None

        result = cli_runner.invoke(
            main,
            ["--project", "/nonexistent/path/to/project"],
        )

        assert result.exit_code == 1
        assert "does not exist" in result.stderr

    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_invalid_format(
        self,
        mock_config_loader,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test analyze command with invalid format."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        result = cli_runner.invoke(
            main,
            ["--format", "xml", "--project", str(temp_dir)],
        )

        assert result.exit_code == 1
        assert "Invalid format" in result.stderr

    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_invalid_agent_tool(
        self,
        mock_config_loader,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test analyze command with invalid agent tool."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        result = cli_runner.invoke(
            main,
            ["--agent-tool", "nonexistent", "--project", str(temp_dir)],
        )

        assert result.exit_code == 1
        assert "Unknown agent tool" in result.stderr

    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_invalid_model(
        self,
        mock_config_loader,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test analyze command with invalid model."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        result = cli_runner.invoke(
            main,
            ["--model", "nonexistent", "--project", str(temp_dir)],
        )

        assert result.exit_code == 1
        assert "Unknown model" in result.stderr

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_file_not_found_error(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test analyze command handles FileNotFoundError."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze_documents.side_effect = FileNotFoundError("Path not found")
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        assert result.exit_code == 1
        assert "Path not found" in result.stderr

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_generic_error(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test analyze command handles generic errors."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze_documents.side_effect = Exception("Something went wrong")
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        assert result.exit_code == 1
        assert "Analysis failed" in result.stderr

    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_config_error(
        self,
        mock_config_loader,
        cli_runner,
        temp_dir,
    ):
        """Test analyze command handles config errors."""
        mock_config_loader.load_config.side_effect = ValueError("Invalid config")
        mock_config_loader.ensure_global_config_exists.return_value = None

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        assert result.exit_code == 1
        assert "Configuration error" in result.stderr

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_exit_code_with_learnings(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        sample_learning,
        temp_dir,
    ):
        """Test analyze command exits with code 2 when rules are found."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        from drift.core.types import AnalysisResult

        result_with_learnings = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
                conversations_with_drift=1,
            ),
            results=[
                AnalysisResult(
                    session_id="session",
                    agent_tool="claude-code",
                    conversation_file="/path",
                    rules=[sample_learning],
                )
            ],
        )

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = result_with_learnings
        mock_analyzer.analyze_documents.return_value = result_with_learnings
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        # Exit code 2 indicates drift was found
        assert result.exit_code == 2

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_exit_code_no_learnings(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command exits with code 0 when no rules found."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        # Exit code 0 indicates success with no drift
        assert result.exit_code == 0

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_no_rules_configured(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_provider_config,
        sample_model_config,
        temp_dir,
    ):
        """Test analyze exits with error when no drift rules are configured."""
        from drift.config.models import AgentToolConfig, DriftConfig

        # Config with no drift learning types
        config_no_rules = DriftConfig(
            providers={"bedrock": sample_provider_config},
            models={"haiku": sample_model_config},
            default_model="haiku",
            rule_definitions={},  # Empty!
            agent_tools={"claude-code": AgentToolConfig(conversation_path="/tmp")},
        )

        mock_config_loader.load_config.return_value = config_no_rules
        mock_config_loader.ensure_global_config_exists.return_value = None

        # Return empty result
        empty_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "message": "No conversation-based learning types configured",
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = empty_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        # Should exit with error code 1
        assert result.exit_code == 1
        assert "No drift learning types configured" in result.stderr
        assert ".drift.yaml" in result.stderr

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_skipped_rules_warning(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test analyze shows warning when rules are skipped."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        # Return result with skipped rules
        result_with_skipped = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "message": "No conversations available for analysis",
                "skipped_rules": ["incomplete_work", "agent_delegation_miss"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        mock_analyzer = MagicMock()
        # Default scope is now 'project', so only analyze_documents is called
        mock_analyzer.analyze_documents.return_value = result_with_skipped
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--project", str(temp_dir)])

        # Should exit with error code 0 since no rules
        assert result.exit_code == 0
        assert "Skipped 2 rule(s):" in result.stderr
        assert "incomplete_work" in result.stderr
        assert "agent_delegation_miss" in result.stderr

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_no_llm_flag_filters_llm_rules(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test --no-llm flag filters out LLM-based rules correctly."""
        from drift.config.models import PhaseDefinition, RuleDefinition

        # Create test config with mix of LLM and programmatic rules
        config = sample_drift_config
        config.rule_definitions = {
            # LLM rule - has 'prompt'
            "llm_rule": RuleDefinition(
                description="LLM-based rule",
                scope="conversation_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="prompt",
                        prompt="Find issues",
                        available_resources=[],
                    )
                ],
            ),
            # Programmatic rule - has 'type' at conversation_level
            "programmatic_rule": RuleDefinition(
                description="Programmatic rule",
                scope="conversation_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="file_exists",
                        file_path="test.txt",
                        failure_message="Missing",
                        expected_behavior="Should exist",
                    )
                ],
            ),
        }

        mock_config_loader.load_config.return_value = config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            main, ["--scope", "conversation", "--no-llm", "--project", str(temp_dir)]
        )

        # Should show warning about skipping LLM rule
        assert "Skipping 1 LLM-based rule(s)" in result.stderr
        assert "running 1 programmatic rule(s)" in result.stderr
        assert "Skipped: llm_rule" in result.stderr
        assert "Running: programmatic_rule" in result.stderr

        # Analyzer should be called with only programmatic rule
        mock_analyzer.analyze.assert_called_once()
        call_args = mock_analyzer.analyze.call_args
        rule_types = call_args.kwargs["rule_types"]
        assert rule_types == ["programmatic_rule"]

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_no_llm_flag_with_conversation_scope_filters_correctly(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        temp_dir,
    ):
        """Test --no-llm with conversation scope doesn't duplicate skipped rules."""
        from drift.config.models import PhaseDefinition, RuleDefinition

        # Create config with LLM conversation rule and programmatic project rule
        config = sample_drift_config
        config.rule_definitions = {
            "llm_conversation_rule": RuleDefinition(
                description="LLM conversation rule",
                scope="conversation_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="prompt",
                        prompt="Find issues",
                        available_resources=[],
                    )
                ],
            ),
            "programmatic_project_rule": RuleDefinition(
                description="Programmatic project rule",
                scope="project_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="file_exists",
                        file_path="test.txt",
                        failure_message="Missing",
                        expected_behavior="Should exist",
                    )
                ],
            ),
        }

        mock_config_loader.load_config.return_value = config
        mock_config_loader.ensure_global_config_exists.return_value = None

        # Return empty result (no conversations)
        result_empty = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "message": "No conversations available for analysis",
                "skipped_rules": ["programmatic_project_rule"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = result_empty
        mock_analyzer.analyze_documents.return_value = result_empty
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--scope", "all", "--no-llm", "--project", str(temp_dir)])

        # Should show LLM rule was skipped due to --no-llm
        assert "Skipping 1 LLM-based rule(s)" in result.stderr
        assert "llm_conversation_rule" in result.stderr

        # Programmatic project rule still runs via analyze_documents
        assert "running 1 programmatic rule(s)" in result.stderr
        assert "programmatic_project_rule" in result.stderr

        # Analyzer should be called with empty list (no conversation-level programmatic rules)
        mock_analyzer.analyze.assert_called_once()
        call_args = mock_analyzer.analyze.call_args
        rule_types = call_args.kwargs["rule_types"]
        assert rule_types == []

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_no_llm_with_project_scope_runs_programmatic_rules(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test --no-llm with project scope runs programmatic rules correctly."""
        from drift.config.models import PhaseDefinition, RuleDefinition

        config = sample_drift_config
        config.rule_definitions = {
            "llm_rule": RuleDefinition(
                description="LLM rule",
                scope="project_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="prompt",
                        prompt="Find issues",
                        available_resources=[],
                    )
                ],
            ),
            "programmatic_rule": RuleDefinition(
                description="Programmatic rule",
                scope="project_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="file_exists",
                        file_path="test.txt",
                        failure_message="Missing",
                        expected_behavior="Should exist",
                    )
                ],
            ),
        }

        mock_config_loader.load_config.return_value = config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            main, ["--no-llm", "--scope", "project", "--project", str(temp_dir)]
        )

        # Should show warning with counts
        assert "Skipping 1 LLM-based rule(s)" in result.stderr
        assert "running 1 programmatic rule(s)" in result.stderr
        assert "llm_rule" in result.stderr
        assert "programmatic_rule" in result.stderr

        # Should call analyze_documents with only programmatic rule
        mock_analyzer.analyze_documents.assert_called_once()
        call_args = mock_analyzer.analyze_documents.call_args
        rule_types = call_args.kwargs["rule_types"]
        assert rule_types == ["programmatic_rule"]

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_no_llm_with_all_llm_rules_passes_empty_list(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test that --no-llm with ALL LLM rules passes empty list, not None."""
        from drift.config.models import PhaseDefinition, RuleDefinition

        config = sample_drift_config

        # Create config with ONLY LLM rules (no programmatic rules)
        config.rule_definitions = {
            "llm_rule_1": RuleDefinition(
                name="llm_rule_1",
                scope="conversation_level",
                description="LLM rule 1",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test1",
                        type="prompt",
                        prompt="Find issues",
                        expected_behavior="Should work",
                        failure_message="Failed",
                    )
                ],
            ),
            "llm_rule_2": RuleDefinition(
                name="llm_rule_2",
                scope="conversation_level",
                description="LLM rule 2",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test2",
                        type="prompt",
                        prompt="Find more issues",
                        expected_behavior="Should work",
                        failure_message="Failed",
                    )
                ],
            ),
        }

        mock_config_loader.load_config.return_value = config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            main, ["--scope", "conversation", "--no-llm", "--project", str(temp_dir)]
        )

        # Should show warning that all rules are skipped
        assert "Skipping 2 LLM-based rule(s)" in result.stderr
        assert "running 0 programmatic rule(s)" in result.stderr

        # CRITICAL: Should pass empty list [], NOT None
        # If None is passed, analyzer will run ALL rules
        mock_analyzer.analyze.assert_called_once()
        call_args = mock_analyzer.analyze.call_args
        rule_types = call_args.kwargs["rule_types"]
        assert rule_types == [], f"Expected empty list [], got {rule_types}"

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_no_llm_with_scope_all_filters_correctly(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test --no-llm with --scope all filters both conversation and project rules."""
        from drift.config.models import PhaseDefinition, RuleDefinition

        config = sample_drift_config

        # Mix of LLM and programmatic rules at different scopes
        config.rule_definitions = {
            # Conversation-level LLM rule
            "conv_llm": RuleDefinition(
                name="conv_llm",
                scope="conversation_level",
                description="Conv LLM rule",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="prompt",
                        prompt="Find issues",
                        expected_behavior="Should work",
                        failure_message="Failed",
                    )
                ],
            ),
            # Conversation-level programmatic rule
            "conv_prog": RuleDefinition(
                name="conv_prog",
                scope="conversation_level",
                description="Conv programmatic rule",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="file_exists",
                        file_path="test.txt",
                        failure_message="Missing",
                        expected_behavior="Should exist",
                    )
                ],
            ),
            # Project-level LLM rule
            "proj_llm": RuleDefinition(
                name="proj_llm",
                scope="project_level",
                description="Proj LLM rule",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="prompt",
                        prompt="Find issues",
                        expected_behavior="Should work",
                        failure_message="Failed",
                    )
                ],
            ),
            # Project-level programmatic rule
            "proj_prog": RuleDefinition(
                name="proj_prog",
                scope="project_level",
                description="Proj programmatic rule",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test",
                        type="file_exists",
                        file_path="test.txt",
                        failure_message="Missing",
                        expected_behavior="Should exist",
                    )
                ],
            ),
        }

        mock_config_loader.load_config.return_value = config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer.analyze_documents.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(main, ["--no-llm", "--scope", "all", "--project", str(temp_dir)])

        # Should skip 2 LLM rules and run 2 programmatic rules
        assert "Skipping 2 LLM-based rule(s)" in result.stderr
        assert "running 2 programmatic rule(s)" in result.stderr
        assert "conv_llm" in result.stderr
        assert "proj_llm" in result.stderr
        assert "conv_prog" in result.stderr
        assert "proj_prog" in result.stderr

        # Should call both analyze methods with correct filtered lists
        mock_analyzer.analyze.assert_called_once()
        conv_call_args = mock_analyzer.analyze.call_args
        conv_learning_types = conv_call_args.kwargs["rule_types"]
        assert conv_learning_types == ["conv_prog"]

        mock_analyzer.analyze_documents.assert_called_once()
        doc_call_args = mock_analyzer.analyze_documents.call_args
        doc_learning_types = doc_call_args.kwargs["rule_types"]
        assert doc_learning_types == ["proj_prog"]

    def test_no_llm_flag_actually_prevents_llm_calls(
        self,
        cli_runner,
        temp_dir,
        sample_drift_config,
    ):
        """Test that --no-llm actually prevents LLM calls from being made."""
        from unittest.mock import MagicMock, patch

        from drift.config.models import PhaseDefinition, RuleDefinition

        config = sample_drift_config

        # Create config with ONLY LLM rules
        config.rule_definitions = {
            "llm_rule_1": RuleDefinition(
                name="llm_rule_1",
                scope="conversation_level",
                description="LLM rule 1",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test1",
                        type="prompt",
                        prompt="Find issues",
                        expected_behavior="Should work",
                        failure_message="Failed",
                    )
                ],
            ),
            "llm_rule_2": RuleDefinition(
                name="llm_rule_2",
                scope="conversation_level",
                description="LLM rule 2",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="test2",
                        type="prompt",
                        prompt="Find more issues",
                        expected_behavior="Should work",
                        failure_message="Failed",
                    )
                ],
            ),
        }

        with patch("drift.cli.commands.analyze.ConfigLoader") as mock_config_loader:
            mock_config_loader.load_config.return_value = config
            mock_config_loader.ensure_global_config_exists.return_value = None

            with patch("drift.cli.commands.analyze.DriftAnalyzer") as mock_analyzer_class:
                mock_analyzer = MagicMock()

                # Mock the analyze method to track if it was called
                mock_analyzer.analyze.return_value = CompleteAnalysisResult(
                    metadata={
                        "generated_at": "2024-01-01T10:00:00",
                        "session_id": "test-123",
                    },
                    summary=AnalysisSummary(
                        total_conversations=0,
                        total_rule_violations=0,
                    ),
                    results=[],
                )
                mock_analyzer_class.return_value = mock_analyzer

                # Mock the provider's generate method to ensure it's NEVER called
                with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
                    cli_runner.invoke(
                        main, ["--scope", "conversation", "--no-llm", "--project", str(temp_dir)]
                    )

                    # CRITICAL: LLM generate should NEVER be called with --no-llm
                    assert mock_generate.call_count == 0, (
                        f"LLM generate was called {mock_generate.call_count} times! "
                        f"With --no-llm flag, it should be 0. Calls: {mock_generate.call_args_list}"
                    )

                    # Should pass empty list to analyzer
                    mock_analyzer.analyze.assert_called_once()
                    call_args = mock_analyzer.analyze.call_args
                    rule_types = call_args.kwargs["rule_types"]
                    assert rule_types == [], f"Expected empty list, got {rule_types}"

    def test_no_llm_flag_prevents_real_llm_calls_integration(
        self,
        cli_runner,
        claude_code_project_dir,
        sample_config_yaml,
    ):
        """Integration test that --no-llm prevents REAL LLM calls (no analyzer mocking)."""
        from unittest.mock import patch

        import yaml

        # Create config with LLM rule + programmatic rule
        with open(sample_config_yaml) as f:
            config_dict = yaml.safe_load(f)
        config_dict["rule_definitions"] = {
            "llm_rule": {
                "description": "LLM rule",
                "scope": "conversation_level",
                "context": "Test",
                "requires_project_context": False,
                "phases": [
                    {
                        "name": "test",
                        "type": "prompt",
                        "prompt": "Find issues",
                        "available_resources": [],
                    }
                ],
            },
            "programmatic_rule": {
                "description": "Programmatic rule",
                "scope": "conversation_level",
                "context": "Test",
                "requires_project_context": False,
                "phases": [
                    {
                        "name": "test",
                        "type": "file_exists",
                        "file_path": "test.txt",
                        "failure_message": "Missing",
                        "expected_behavior": "Should exist",
                    }
                ],
            },
        }

        # Write config to project dir
        config_path = claude_code_project_dir / ".drift.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_dict, f)

        # This test uses REAL analyzer but mocks the LLM provider generate method
        # If the test is slow or generate is called, the bug is REAL
        with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
            # Set up mock to fail loudly if called
            mock_generate.side_effect = AssertionError(
                "LLM generate() was called! --no-llm flag is not working!"
            )

            result = cli_runner.invoke(
                main,
                ["--no-llm", "--project", str(claude_code_project_dir)],
            )

            # If we get here without assertion error, generate was never called (good!)
            assert result.exit_code in [0, 2], (
                f"Unexpected exit code: {result.exit_code}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
            assert mock_generate.call_count == 0, (
                f"LLM generate was called {mock_generate.call_count} times with --no-llm! "
                f"This is a CRITICAL bug!"
            )

    def test_default_scope_is_all(self, cli_runner, claude_code_project_dir, make_config_yaml):
        """Test that default scope is 'project' (not 'conversation' or 'all')."""
        # Create config with both conversation and project rules
        config_content = make_config_yaml(
            rule_types={
                "conversation_rule": {
                    "description": "Conv rule",
                    "scope": "conversation_level",
                    "context": "Test",
                    "requires_project_context": False,
                    "phases": [
                        {"name": "test", "type": "prompt", "model": "haiku", "prompt": "test"}
                    ],
                },
                "project_rule": {
                    "description": "Project rule",
                    "scope": "project_level",
                    "context": "Test",
                    "requires_project_context": False,
                    "phases": [
                        {
                            "name": "check",
                            "type": "file_exists",
                            "file_path": "README.md",
                            "failure_message": "Missing README",
                            "expected_behavior": "Should have README",
                        }
                    ],
                },
            }
        )
        config_path = claude_code_project_dir / ".drift.yaml"
        config_path.write_text(config_content)

        with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
            mock_generate.return_value = "[]"

            # Run without explicit --scope (should default to 'project')
            result = cli_runner.invoke(
                main,
                ["--project", str(claude_code_project_dir)],
            )

            # Check that only project analysis runs (not conversation)
            # The project rule should have run (checks for README.md)
            assert result.exit_code in [0, 2]
            assert "project_rule" in result.stdout or "Rules checked" in result.stdout
            # Conversation rule should NOT have run
            assert (
                mock_generate.call_count == 0
            ), "Conversation rules should not run with default scope"

    def test_no_llm_project_scope_runs_programmatic_rules(
        self, cli_runner, claude_code_project_dir, make_config_yaml
    ):
        """Test that --no-llm --scope project runs programmatic rules and reports stats."""
        config_content = make_config_yaml(
            rule_types={
                "llm_rule": {
                    "description": "LLM-based rule",
                    "scope": "project_level",
                    "context": "Test",
                    "requires_project_context": True,
                    "document_bundle": {
                        "bundle_type": "skill",
                        "file_patterns": [".claude/skills/*/SKILL.md"],
                        "bundle_strategy": "individual",
                    },
                    "phases": [
                        {"name": "test", "type": "prompt", "model": "sonnet", "prompt": "analyze"}
                    ],
                },
                "programmatic_rule": {
                    "description": "Programmatic rule",
                    "scope": "project_level",
                    "context": "Test",
                    "requires_project_context": True,
                    "phases": [
                        {
                            "name": "check",
                            "type": "file_exists",
                            "file_path": "README.md",
                            "failure_message": "Missing README",
                            "expected_behavior": "Should have README",
                        }
                    ],
                },
            }
        )
        config_path = claude_code_project_dir / ".drift.yaml"
        config_path.write_text(config_content)

        # Create README.md so rule passes
        (claude_code_project_dir / "README.md").write_text("# Test")

        with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
            mock_generate.side_effect = AssertionError("LLM should not be called with --no-llm!")

            result = cli_runner.invoke(
                main,
                ["--no-llm", "--scope", "project", "--project", str(claude_code_project_dir)],
            )

            # Debug output
            if result.exit_code != 0:
                print(f"\nSTDOUT:\n{result.stdout}")
                print(f"\nSTDERR:\n{result.stderr}")
                print(f"\nException:\n{result.exception}")

            assert result.exit_code == 0
            assert mock_generate.call_count == 0

            # Verify output shows correct rule statistics
            assert "Skipping 1 LLM-based rule(s)" in result.stderr
            assert "running 1 programmatic rule(s)" in result.stderr
            assert "Skipped: llm_rule" in result.stderr
            assert "Running: programmatic_rule" in result.stderr

            # Verify programmatic rule stats are reported
            assert "Rules checked: 1" in result.stdout
            assert "Rules passed: 1" in result.stdout
            assert "programmatic_rule" in result.stdout
            assert "No issues found" in result.stdout

    def test_no_llm_all_scope_merges_stats_correctly(
        self, cli_runner, claude_code_project_dir, make_config_yaml
    ):
        """Test that --no-llm --scope all merges conversation and project rule stats."""
        config_content = make_config_yaml(
            rule_types={
                "conv_llm": {
                    "description": "Conv LLM",
                    "scope": "conversation_level",
                    "context": "Test",
                    "requires_project_context": False,
                    "phases": [
                        {"name": "test", "type": "prompt", "model": "haiku", "prompt": "test"}
                    ],
                },
                "project_programmatic": {
                    "description": "Project programmatic",
                    "scope": "project_level",
                    "context": "Test",
                    "requires_project_context": True,
                    "phases": [
                        {
                            "name": "check",
                            "type": "file_exists",
                            "file_path": "README.md",
                            "failure_message": "Missing README",
                            "expected_behavior": "Should have README",
                        }
                    ],
                },
            }
        )
        config_path = claude_code_project_dir / ".drift.yaml"
        config_path.write_text(config_content)

        # Create README.md so rule passes
        (claude_code_project_dir / "README.md").write_text("# Test")

        with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
            mock_generate.side_effect = AssertionError("LLM should not be called!")

            result = cli_runner.invoke(
                main,
                ["--no-llm", "--scope", "all", "--project", str(claude_code_project_dir)],
            )

            assert result.exit_code == 0
            assert mock_generate.call_count == 0

            # Verify both conversation and project rules are considered
            assert "Skipping 1 LLM-based rule(s)" in result.stderr
            assert "running 1 programmatic rule(s)" in result.stderr

            # Verify merged stats include project rule
            assert "Rules checked: 1" in result.stdout
            assert "Rules passed: 1" in result.stdout
            assert "project_programmatic" in result.stdout

    def test_no_llm_conversation_scope_no_project_rules(
        self, cli_runner, claude_code_project_dir, make_config_yaml
    ):
        """Test that --no-llm --scope conversation doesn't run project rules."""
        config_content = make_config_yaml(
            rule_types={
                "conv_llm": {
                    "description": "Conv LLM",
                    "scope": "conversation_level",
                    "context": "Test",
                    "requires_project_context": False,
                    "phases": [
                        {"name": "test", "type": "prompt", "model": "haiku", "prompt": "test"}
                    ],
                },
                "project_programmatic": {
                    "description": "Project programmatic",
                    "scope": "project_level",
                    "context": "Test",
                    "requires_project_context": True,
                    "phases": [
                        {
                            "name": "check",
                            "type": "file_exists",
                            "file_path": "README.md",
                            "failure_message": "Missing README",
                            "expected_behavior": "Should have README",
                        }
                    ],
                },
            }
        )
        config_path = claude_code_project_dir / ".drift.yaml"
        config_path.write_text(config_content)

        with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
            mock_generate.side_effect = AssertionError("LLM should not be called!")

            result = cli_runner.invoke(
                main,
                [
                    "--no-llm",
                    "--scope",
                    "conversation",
                    "--project",
                    str(claude_code_project_dir),
                ],
            )

            assert result.exit_code == 0
            assert mock_generate.call_count == 0

            # Verify only conversation rules are considered
            assert "Skipping 1 LLM-based rule(s)" in result.stderr
            assert "running 0 programmatic rule(s)" in result.stderr
            assert "conv_llm" in result.stderr

            # project_programmatic should NOT be mentioned
            assert "project_programmatic" not in result.stderr

    def test_programmatic_project_rule_execution_and_reporting(
        self, cli_runner, claude_code_project_dir, make_config_yaml
    ):
        """Test that programmatic project-level rules execute and report correctly."""
        config_content = make_config_yaml(
            rule_types={
                "readme_check": {
                    "description": "README existence check",
                    "scope": "project_level",
                    "context": "Projects should have README",
                    "requires_project_context": True,
                    "phases": [
                        {
                            "name": "check_readme",
                            "type": "file_exists",
                            "file_path": "README.md",
                            "failure_message": "README.md is missing",
                            "expected_behavior": "Project should have README.md",
                        }
                    ],
                },
                "license_check": {
                    "description": "LICENSE existence check",
                    "scope": "project_level",
                    "context": "Projects should have LICENSE",
                    "requires_project_context": True,
                    "phases": [
                        {
                            "name": "check_license",
                            "type": "file_exists",
                            "file_path": "LICENSE",
                            "failure_message": "LICENSE is missing",
                            "expected_behavior": "Project should have LICENSE",
                        }
                    ],
                },
            }
        )
        config_path = claude_code_project_dir / ".drift.yaml"
        config_path.write_text(config_content)

        # Create README and LICENSE so both rules pass
        (claude_code_project_dir / "README.md").write_text("# Test")
        (claude_code_project_dir / "LICENSE").write_text("MIT License")

        with patch("drift.providers.bedrock.BedrockProvider.generate") as mock_generate:
            mock_generate.side_effect = AssertionError("No LLM calls expected!")

            result = cli_runner.invoke(
                main,
                ["--no-llm", "--scope", "project", "--project", str(claude_code_project_dir)],
            )

            # Both rules should pass (README and LICENSE exist)
            assert result.exit_code == 0
            assert mock_generate.call_count == 0

            # Verify output shows rule statistics
            assert "Rules checked: 2" in result.stdout
            assert "Rules passed: 2" in result.stdout

            # Verify specific rule results
            assert "readme_check" in result.stdout
            assert "license_check" in result.stdout
            assert "No issues found" in result.stdout
