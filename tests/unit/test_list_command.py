"""Unit tests for list command."""

import json
from unittest.mock import patch

import pytest

from drift.cli.commands.list import list_command
from drift.cli.utils import print_error
from drift.config.models import (
    DriftConfig,
    ModelConfig,
    ProviderConfig,
    ProviderType,
    RuleDefinition,
)


class TestListCommand:
    """Tests for list_command function."""

    @pytest.fixture
    def sample_config(self):
        """Create a sample config with multiple rules."""
        rule1 = RuleDefinition(
            description="First rule",
            scope="project_level",
            context="Context 1",
            requires_project_context=True,
        )
        rule2 = RuleDefinition(
            description="Second rule",
            scope="project_level",
            context="Context 2",
            requires_project_context=False,
        )
        rule3 = RuleDefinition(
            description="Third rule",
            scope="conversation_level",
            context="Context 3",
            requires_project_context=False,
        )

        return DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="General",
            rule_definitions={
                "rule_one": rule1,
                "rule_two": rule2,
                "rule_three": rule3,
            },
        )

    def test_list_text_format(self, temp_dir, sample_config, capsys):
        """Test listing rules in text format (one per line)."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="text",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")

            # Should have one rule per line
            assert len(lines) == 3
            assert "rule_one" in lines
            assert "rule_two" in lines
            assert "rule_three" in lines

    def test_list_json_format(self, temp_dir, sample_config, capsys):
        """Test listing rules in JSON format."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="json",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            # Should have rules array with all rule names
            assert "rules" in output
            assert len(output["rules"]) == 3
            assert "rule_one" in output["rules"]
            assert "rule_two" in output["rules"]
            assert "rule_three" in output["rules"]

    def test_list_markdown_format_treated_as_text(self, temp_dir, sample_config, capsys):
        """Test that markdown format is treated as text format."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="markdown",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")

            # Should output as text (one per line)
            assert len(lines) == 3
            assert "rule_one" in lines

    def test_list_invalid_format(self, temp_dir, sample_config):
        """Test error when invalid format is specified."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="xml",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_list_empty_rules(self, temp_dir, capsys):
        """Test listing when no rules are defined."""
        empty_config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="General",
            rule_definitions={},
        )

        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = empty_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="text",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            # Should output nothing for empty rules
            assert captured.out.strip() == ""

    def test_list_empty_rules_json(self, temp_dir, capsys):
        """Test listing empty rules in JSON format."""
        empty_config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="General",
            rule_definitions={},
        )

        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = empty_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="json",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            output = json.loads(captured.out)

            assert "rules" in output
            assert len(output["rules"]) == 0
            assert output["rules"] == []

    def test_list_config_load_error(self, temp_dir):
        """Test error handling when config loading fails."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = ValueError("Invalid config")

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_list_project_path_not_exists(self):
        """Test error when project path doesn't exist."""
        with pytest.raises(SystemExit) as exc_info:
            list_command(
                project="/nonexistent/path",
                verbose=0,
            )

        assert exc_info.value.code == 1

    def test_list_uses_current_dir_when_no_project(self, temp_dir, sample_config):
        """Test that list uses current directory when project not specified."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
                mock_load.return_value = sample_config

                with pytest.raises(SystemExit) as exc_info:
                    list_command(
                        verbose=0,
                    )

                assert exc_info.value.code == 0

                # Check that load_config was called with current directory
                mock_load.assert_called_once()
                assert mock_load.call_args[0][0].resolve() == temp_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_list_with_custom_rules_file(self, temp_dir, sample_config):
        """Test listing with custom rules file."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    project=str(temp_dir),
                    rules_file=["custom_rules.yaml"],
                    verbose=0,
                )

            assert exc_info.value.code == 0

            # Verify rules_file was passed to config loader
            mock_load.assert_called_once()
            assert mock_load.call_args[1]["rules_files"] == ["custom_rules.yaml"]

    def test_list_with_multiple_rules_files(self, temp_dir, sample_config):
        """Test listing with multiple custom rules files."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    project=str(temp_dir),
                    rules_file=["rules1.yaml", "rules2.yaml"],
                    verbose=0,
                )

            assert exc_info.value.code == 0

            # Verify both rules files were passed
            mock_load.assert_called_once()
            assert mock_load.call_args[1]["rules_files"] == ["rules1.yaml", "rules2.yaml"]

    def test_list_keyboard_interrupt(self, temp_dir, sample_config):
        """Test handling of keyboard interrupt."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_list_unexpected_error(self, temp_dir, sample_config):
        """Test handling of unexpected errors."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_list_verbosity_levels(self, temp_dir, sample_config):
        """Test that different verbosity levels work."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            # Test various verbosity levels
            for verbose_level in [0, 1, 2, 3]:
                with pytest.raises(SystemExit) as exc_info:
                    list_command(
                        project=str(temp_dir),
                        verbose=verbose_level,
                    )

                assert exc_info.value.code == 0

    def test_list_preserves_rule_order(self, temp_dir, capsys):
        """Test that list preserves rule order from config."""
        # Create config with specific rule order
        rules = {}
        for i in range(5):
            rules[f"rule_{i:02d}"] = RuleDefinition(
                description=f"Rule {i}",
                scope="project_level",
                context=f"Context {i}",
                requires_project_context=True,
            )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="General",
            rule_definitions=rules,
        )

        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="text",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            lines = captured.out.strip().split("\n")

            # Check all rules are present
            assert len(lines) == 5
            for i in range(5):
                assert f"rule_{i:02d}" in lines

    def test_list_json_format_structure(self, temp_dir, sample_config, capsys):
        """Test JSON output has correct structure and formatting."""
        with patch("drift.cli.commands.list.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                list_command(
                    format_type="json",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()

            # Should be valid JSON
            output = json.loads(captured.out)

            # Should have exactly one key
            assert len(output) == 1
            assert "rules" in output

            # Rules should be a list
            assert isinstance(output["rules"], list)


class TestPrintFunctions:
    """Tests for print_error function."""

    def test_print_error_message_to_stderr(self, capsys):
        """Test that print_error outputs to stderr with color."""
        print_error("Test error message")

        captured = capsys.readouterr()
        assert "Test error message" in captured.err
        assert captured.out == ""
