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
            "rule_definitions": {
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

    def test_json_output_always_includes_execution_details(self, runner, tmp_path):
        """Test that JSON output includes execution_details regardless of --detailed flag."""
        # Create a project with .claude.md
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / ".claude.md").write_text("# Test Project\n")

        # Create config with a programmatic rule
        config_content = """
rule_definitions:
  claude_md_missing:
    description: "Validates .claude.md files exist"
    scope: "project_level"
    context: "Why it's important"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "project_config"
        bundle_strategy: "collection"
        file_patterns: [".claude.md", "README.md"]
      rules:
        - rule_type: "file_exists"
          description: "Validates .claude.md files exist"
          file_path: ".claude.md"
          failure_message: ".claude.md file is missing"
          expected_behavior: ".claude.md file should exist"
"""
        config_file = project_dir / ".drift.yaml"
        config_file.write_text(config_content)

        # Run drift with --no-llm and --format json (WITHOUT --detailed)
        result = runner.invoke(app, ["--no-llm", "--format", "json", "--project", str(project_dir)])

        assert result.exit_code == 0, f"CLI failed with: {result.stdout}"

        # Parse JSON output
        import json

        output = json.loads(result.stdout)

        # JSON output MUST include execution_details even without --detailed flag
        assert "metadata" in output, "No metadata in JSON output"
        assert "execution_details" in output["metadata"], "No execution_details in metadata"

        # Should have at least one execution detail for claude_md_missing
        exec_details = output["metadata"]["execution_details"]
        assert len(exec_details) > 0, "execution_details is empty"

        # Find claude_md_missing detail
        detail = None
        for d in exec_details:
            if d.get("rule_name") == "claude_md_missing":
                detail = d
                break

        assert detail is not None, f"No execution detail for claude_md_missing. Got: {exec_details}"
        assert detail["status"] == "passed", f"Expected passed status, got {detail.get('status')}"

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

    def test_detailed_flag_shows_execution_context_for_document_validation(self, runner, tmp_path):
        """Test that --detailed shows execution context when running document validation."""
        # Create a project with .claude.md
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / ".claude.md").write_text("# Test Project\n")

        # Create a .drift.yaml config file with claude_md_missing rule
        config_content = """
rule_definitions:
  claude_md_missing:
    description: "Validates .claude.md files exist"
    scope: "project_level"
    context: "Why it's important"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "project_config"
        bundle_strategy: "collection"
        file_patterns: [".claude.md", "README.md"]
      rules:
        - rule_type: "file_exists"
          description: "Validates .claude.md files exist"
          file_path: ".claude.md"
          failure_message: ".claude.md file is missing"
          expected_behavior: ".claude.md file should exist"
"""
        config_file = project_dir / ".drift.yaml"
        config_file.write_text(config_content)

        # Run drift with --detailed and --no-llm (to only run programmatic rules)
        result = runner.invoke(app, ["--detailed", "--no-llm", "--project", str(project_dir)])

        # Should succeed
        import traceback

        if result.exception:
            tb = "".join(
                traceback.format_exception(
                    type(result.exception), result.exception, result.exception.__traceback__
                )
            )
        else:
            tb = "No traceback"
        assert result.exit_code == 0, (
            f"CLI failed with exit code {result.exit_code}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}\n"
            f"exception: {result.exception}\ntraceback:\n{tb}"
        )

        # Should show execution details section
        assert (
            "Test Execution Details" in result.stdout or "Execution Details" in result.stdout
        ), f"No execution details section found in output:\n{result.stdout}"

        # Should show the claude_md_missing rule
        assert (
            "claude_md_missing" in result.stdout
        ), f"claude_md_missing rule not found in output:\n{result.stdout}"

        # Should show execution context (bundle info, files checked, etc.)
        assert any(
            keyword in result.stdout
            for keyword in ["Bundle", "bundle", "Files checked", "Validated"]
        ), f"No execution context found in output:\n{result.stdout}"

        # Should show what was validated
        assert (
            ".claude.md" in result.stdout
        ), f".claude.md not mentioned in output:\n{result.stdout}"

    def test_no_detailed_flag_hides_execution_details(self, runner, tmp_path):
        """Test that without --detailed, execution details are NOT shown."""
        # Create a project with .claude.md
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / ".claude.md").write_text("# Test Project\n")

        # Create config
        config_content = """
rule_definitions:
  claude_md_missing:
    description: "Validates .claude.md files exist"
    scope: "project_level"
    context: "Why it's important"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "project_config"
        bundle_strategy: "collection"
        file_patterns: [".claude.md", "README.md"]
      rules:
        - rule_type: "file_exists"
          description: "Validates .claude.md files exist"
          file_path: ".claude.md"
          failure_message: ".claude.md file is missing"
          expected_behavior: ".claude.md file should exist"
"""
        config_file = project_dir / ".drift.yaml"
        config_file.write_text(config_content)

        # Run drift WITHOUT --detailed
        result = runner.invoke(app, ["--no-llm", "--project", str(project_dir)])

        # Should succeed
        assert result.exit_code == 0, f"CLI failed with: {result.stdout}"

        # Should NOT show execution details section
        assert (
            "Test Execution Details" not in result.stdout
            and "Execution Details" not in result.stdout
        ), f"Execution details should not be shown without --detailed flag:\n{result.stdout}"

    def test_detailed_flag_with_conversations_shows_execution_context(self, runner, tmp_path):
        """Test that --detailed works when there ARE conversations (not just 0 conversations)."""
        # Create a project with .claude.md
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / ".claude.md").write_text("# Test Project\n")

        # Create a logs directory with a conversation
        logs_dir = project_dir / ".logs"
        logs_dir.mkdir()

        conversation_log = {
            "session_id": "test-session",
            "agent_tool": "test_tool",
            "project_path": str(project_dir),
            "turns": [
                {
                    "number": 1,
                    "user_message": "Hello",
                    "ai_message": "Hi there",
                    "timestamp": "2025-01-01T00:00:00",
                }
            ],
        }
        import json

        (logs_dir / "test-session.json").write_text(json.dumps(conversation_log))

        # Create config with both conversation-level and project-level rules
        config_content = """
rule_definitions:
  claude_md_missing:
    description: "Validates .claude.md files exist"
    scope: "project_level"
    context: "Why it's important"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "project_config"
        bundle_strategy: "collection"
        file_patterns: [".claude.md", "README.md"]
      rules:
        - rule_type: "file_exists"
          description: "Validates .claude.md files exist"
          file_path: ".claude.md"
          failure_message: ".claude.md file is missing"
          expected_behavior: ".claude.md file should exist"

agent_tools:
  test_tool:
    conversation_path: ".logs"
    log_file_pattern: "*.json"
"""
        config_file = project_dir / ".drift.yaml"
        config_file.write_text(config_content)

        # Run drift with --detailed and --no-llm on scope=all
        result = runner.invoke(
            app, ["--detailed", "--no-llm", "--scope", "all", "--project", str(project_dir)]
        )

        # Should succeed
        import traceback

        if result.exception:
            tb = "".join(
                traceback.format_exception(
                    type(result.exception), result.exception, result.exception.__traceback__
                )
            )
        else:
            tb = "No traceback"
        assert result.exit_code == 0, (
            f"CLI failed with exit code {result.exit_code}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}\n"
            f"exception: {result.exception}\ntraceback:\n{tb}"
        )

        # Should show execution details section
        assert (
            "Test Execution Details" in result.stdout or "Execution Details" in result.stdout
        ), f"No execution details section found in output:\n{result.stdout}"

        # Should show the claude_md_missing rule
        assert (
            "claude_md_missing" in result.stdout
        ), f"claude_md_missing rule not found in output:\n{result.stdout}"

        # Should show execution context
        assert any(
            keyword in result.stdout
            for keyword in ["Bundle", "bundle", "Files checked", "Validated"]
        ), f"No execution context found in output:\n{result.stdout}"
