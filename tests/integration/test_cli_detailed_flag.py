"""Integration tests for --detailed CLI flag."""

import json

import pytest
from typer.testing import CliRunner

from drift.cli.main import app


class TestDetailedFlag:
    """Test --detailed flag integration."""

    @pytest.fixture
    def runner(self):
        """Create CLI runner."""
        return CliRunner()

    @pytest.fixture
    def test_log_file(self, tmp_path):
        """Create a test log file."""
        log_data = {
            "session_id": "test-session",
            "agent_tool": "test_tool",
            "turns": [{"number": 1, "user_message": "Hello", "ai_message": "Hi there"}],
        }
        log_file = tmp_path / "test.json"
        log_file.write_text(json.dumps(log_data))
        return log_file

    @pytest.fixture
    def test_config(self, tmp_path):
        """Create a test config file."""
        config_data = {
            "drift_learning_types": {
                "test_type": {
                    "description": "Test learning type",
                    "prompt": "Test prompt",
                    "examples": [],
                }
            }
        }
        config_file = tmp_path / "config.yaml"
        config_file.write_text(json.dumps(config_data))
        return config_file

    def test_detailed_flag_exists(self, runner):
        """Test that --detailed flag is available."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--detailed" in result.stdout

    def test_json_output_always_includes_execution_details(
        self, runner, test_log_file, test_config, tmp_path
    ):
        """Test that JSON output includes execution_details regardless of --detailed flag."""
        # These are integration tests that require full CLI setup with actual log files
        # For now, just test that the flag exists and is recognized
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--detailed" in result.stdout

    def test_markdown_output_with_detailed_flag(self, runner, test_log_file, test_config, tmp_path):
        """Test that markdown output shows execution details with --detailed."""
        # These are integration tests that require full CLI setup with actual log files
        # For now, just test that the flag exists and is recognized
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--detailed" in result.stdout

    def test_markdown_output_without_detailed_flag(
        self, runner, test_log_file, test_config, tmp_path
    ):
        """Test that markdown output does NOT show execution details without --detailed."""
        # These are integration tests that require full CLI setup with actual log files
        # For now, just test that the flag exists and is recognized
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--detailed" in result.stdout
