"""Integration tests for CLI commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from drift.cli.main import app
from drift.core.types import AnalysisSummary, CompleteAnalysisResult


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
            total_learnings=0,
            conversations_without_drift=1,
        ),
        results=[],
    )


class TestAnalyzeCommand:
    """Tests for the analyze CLI command."""

    def test_version_option(self, cli_runner):
        """Test --version option."""
        result = cli_runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "drift version" in result.stdout

    def test_help_option(self, cli_runner):
        """Test --help option."""
        result = cli_runner.invoke(app, ["analyze", "--help"])

        assert result.exit_code == 0
        assert "analyze" in result.stdout.lower()
        assert "drift patterns" in result.stdout.lower()

    @patch("drift.cli.commands.analyze.DriftAnalyzer")
    @patch("drift.cli.commands.analyze.ConfigLoader")
    def test_analyze_default_options(
        self,
        mock_config_loader,
        mock_analyzer_class,
        cli_runner,
        sample_drift_config,
        mock_complete_result,
        temp_dir,
    ):
        """Test analyze command with default options."""
        # Setup mocks
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--project", str(temp_dir)])

        assert result.exit_code == 0
        assert "# Drift Analysis Results" in result.stdout
        mock_analyzer.analyze.assert_called_once()

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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--format", "json", "--project", str(temp_dir)])

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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            app,
            ["analyze", "--agent-tool", "claude-code", "--project", str(temp_dir)],
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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            app,
            ["analyze", "--types", "incomplete_work", "--project", str(temp_dir)],
        )

        assert result.exit_code == 0
        call_kwargs = mock_analyzer.analyze.call_args[1]
        assert call_kwargs["learning_types"] == ["incomplete_work"]

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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            app,
            ["analyze", "--types", "incomplete_work,wrong_assumption", "--project", str(temp_dir)],
        )

        # Should fail because wrong_assumption is not in sample config
        assert result.exit_code == 1
        assert "Unknown learning types" in result.stderr

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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--latest", "--project", str(temp_dir)])

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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--days", "5", "--project", str(temp_dir)])

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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--all", "--project", str(temp_dir)])

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
            app,
            ["analyze", "--latest", "--all", "--project", str(temp_dir)],
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
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(
            app,
            ["analyze", "--model", "haiku", "--project", str(temp_dir)],
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
            app,
            ["analyze", "--project", "/nonexistent/path/to/project"],
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
            app,
            ["analyze", "--format", "xml", "--project", str(temp_dir)],
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
            app,
            ["analyze", "--agent-tool", "nonexistent", "--project", str(temp_dir)],
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
            app,
            ["analyze", "--model", "nonexistent", "--project", str(temp_dir)],
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
        mock_analyzer.analyze.side_effect = FileNotFoundError("Path not found")
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--project", str(temp_dir)])

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
        mock_analyzer.analyze.side_effect = Exception("Something went wrong")
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--project", str(temp_dir)])

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

        result = cli_runner.invoke(app, ["analyze", "--project", str(temp_dir)])

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
        """Test analyze command exits with code 2 when learnings are found."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        from drift.core.types import AnalysisResult

        result_with_learnings = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=1,
                conversations_with_drift=1,
            ),
            results=[
                AnalysisResult(
                    session_id="session",
                    agent_tool="claude-code",
                    conversation_file="/path",
                    learnings=[sample_learning],
                )
            ],
        )

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = result_with_learnings
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--project", str(temp_dir)])

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
        """Test analyze command exits with code 0 when no learnings found."""
        mock_config_loader.load_config.return_value = sample_drift_config
        mock_config_loader.ensure_global_config_exists.return_value = None

        mock_analyzer = MagicMock()
        mock_analyzer.analyze.return_value = mock_complete_result
        mock_analyzer_class.return_value = mock_analyzer

        result = cli_runner.invoke(app, ["analyze", "--project", str(temp_dir)])

        # Exit code 0 indicates success with no drift
        assert result.exit_code == 0
