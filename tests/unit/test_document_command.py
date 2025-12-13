"""Unit tests for document command."""

from unittest.mock import patch

import pytest

from drift.cli.commands.document import (
    document_command,
    format_rule_html,
    format_rule_markdown,
    print_error,
    print_success,
    print_warning,
)
from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    DriftConfig,
    ModelConfig,
    PhaseDefinition,
    ProviderConfig,
    ProviderType,
    RuleDefinition,
    SeverityLevel,
    ValidationRule,
    ValidationRulesConfig,
)


class TestDocumentCommand:
    """Tests for document_command function."""

    @pytest.fixture
    def sample_rule(self):
        """Create a sample rule for testing."""
        return RuleDefinition(
            description="Test skill validation",
            scope="project_level",
            context="Skills need documentation",
            requires_project_context=True,
            severity=SeverityLevel.FAIL,
            group_name="Testing",
            supported_clients=["claude-code"],
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_file",
                    type="core:file_exists",
                    params={"file_path": "SKILL.md"},
                )
            ],
        )

    @pytest.fixture
    def sample_config(self, sample_rule):
        """Create a sample config with rule."""
        return DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="General",
            rule_definitions={"skill_validation": sample_rule},
        )

    def test_document_no_rules_or_all_flag(self, temp_dir, sample_config):
        """Test error when neither --rules nor --all is specified."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_document_rule_not_found(self, temp_dir, sample_config):
        """Test error when specified rule doesn't exist."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="nonexistent_rule",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_document_single_rule_markdown_stdout(self, temp_dir, sample_config, capsys):
        """Test documenting single rule to stdout in markdown format."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    format_type="markdown",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "# skill_validation" in captured.out
            assert "Test skill validation" in captured.out
            assert "## Description" in captured.out
            assert "## Metadata" in captured.out
            assert "## Context" in captured.out
            assert "## Document Bundle" in captured.out
            assert "## Phases" in captured.out

    def test_document_single_rule_html_stdout(self, temp_dir, sample_config, capsys):
        """Test documenting single rule to stdout in HTML format."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    format_type="html",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "<h1>skill_validation</h1>" in captured.out
            assert "<h2>Description</h2>" in captured.out
            assert "<h2>Metadata</h2>" in captured.out
            assert "Test skill validation" in captured.out

    def test_document_multiple_rules_markdown(self, temp_dir, capsys):
        """Test documenting multiple rules to stdout in markdown format."""
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

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={
                "rule1": rule1,
                "rule2": rule2,
            },
        )

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="rule1,rule2",
                    project=str(temp_dir),
                    format_type="markdown",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "# Drift Rules Documentation" in captured.out
            assert "Documentation for 2 rules" in captured.out
            assert "# rule1" in captured.out
            assert "# rule2" in captured.out
            assert "First rule" in captured.out
            assert "Second rule" in captured.out
            assert "---" in captured.out

    def test_document_all_rules_markdown(self, temp_dir, sample_config, capsys):
        """Test documenting all rules with --all flag."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    all_rules=True,
                    project=str(temp_dir),
                    format_type="markdown",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "# skill_validation" in captured.out
            assert "Test skill validation" in captured.out

    def test_document_write_to_file(self, temp_dir, sample_config):
        """Test documenting rule to output file."""
        output_file = temp_dir / "documentation.md"

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    output=str(output_file),
                    format_type="markdown",
                    verbose=0,
                )

            assert exc_info.value.code == 0

        # Check file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert "# skill_validation" in content
        assert "Test skill validation" in content

    def test_document_write_to_file_creates_directories(self, temp_dir, sample_config):
        """Test that document creates parent directories for output file."""
        output_file = temp_dir / "nested" / "dir" / "documentation.md"

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    output=str(output_file),
                    format_type="markdown",
                    verbose=0,
                )

            assert exc_info.value.code == 0

        # Check file and directories were created
        assert output_file.exists()
        assert output_file.parent.exists()

    def test_document_output_file_write_error(self, temp_dir, sample_config):
        """Test error handling when output file can't be written."""
        # Use invalid path for output
        output_file = "/invalid/path/to/file.md"

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    output=output_file,
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_document_invalid_format(self, temp_dir, sample_config):
        """Test error when invalid format is specified."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    format_type="invalid_format",
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_document_config_load_error(self, temp_dir):
        """Test error handling when config loading fails."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = ValueError("Invalid config")

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_document_project_path_not_exists(self):
        """Test error when project path doesn't exist."""
        with pytest.raises(SystemExit) as exc_info:
            document_command(
                rules="skill_validation",
                project="/nonexistent/path",
                verbose=0,
            )

        assert exc_info.value.code == 1

    def test_document_uses_current_dir_when_no_project(self, temp_dir, sample_config):
        """Test that document uses current directory when project not specified."""
        import os

        # Change to temp_dir so Path.cwd() returns a valid path
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
                mock_load.return_value = sample_config

                with pytest.raises(SystemExit) as exc_info:
                    document_command(
                        rules="skill_validation",
                        verbose=0,
                    )

                assert exc_info.value.code == 0

                # Check that load_config was called with current directory (temp_dir)
                mock_load.assert_called_once()
                # Resolve both paths to handle macOS /var -> /private/var symlink
                assert mock_load.call_args[0][0].resolve() == temp_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_document_with_custom_rules_file(self, temp_dir, sample_config):
        """Test documenting with custom rules file."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    rules_file=["custom_rules.yaml"],
                    verbose=0,
                )

            assert exc_info.value.code == 0

            # Verify rules_file was passed to config loader
            mock_load.assert_called_once()
            assert mock_load.call_args[1]["rules_files"] == ["custom_rules.yaml"]

    def test_document_keyboard_interrupt(self, temp_dir, sample_config):
        """Test handling of keyboard interrupt."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_document_unexpected_error(self, temp_dir, sample_config):
        """Test handling of unexpected errors."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_document_verbosity_levels(self, temp_dir, sample_config):
        """Test that different verbosity levels work."""
        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            # Test various verbosity levels
            for verbose_level in [0, 1, 2, 3]:
                with pytest.raises(SystemExit) as exc_info:
                    document_command(
                        rules="skill_validation",
                        project=str(temp_dir),
                        verbose=verbose_level,
                    )

                assert exc_info.value.code == 0

    def test_document_rule_with_all_fields(self, temp_dir, capsys):
        """Test documenting a rule with all possible fields populated."""
        rule = RuleDefinition(
            description="Comprehensive test rule",
            scope="conversation_level",
            context="Full context example",
            requires_project_context=False,
            severity=SeverityLevel.WARNING,
            group_name="TestGroup",
            supported_clients=["claude-code", "other-client"],
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["test/*.md"],
                bundle_strategy=BundleStrategy.COLLECTION,
                resource_patterns=["**/*.py"],
            ),
            phases=[
                PhaseDefinition(
                    name="phase1",
                    type="prompt",
                    model="sonnet",
                    prompt="Test prompt content",
                    available_resources=["skill", "command"],
                ),
                PhaseDefinition(
                    name="phase2",
                    type="core:file_exists",
                    params={"file_path": "test.md"},
                ),
            ],
            draft_instructions="Custom draft instructions for {file_path}",
        )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="General",
            rule_definitions={"full_rule": rule},
        )

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="full_rule",
                    project=str(temp_dir),
                    format_type="markdown",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            # Check all sections are present
            assert "# full_rule" in captured.out
            assert "Comprehensive test rule" in captured.out
            assert "conversation_level" in captured.out
            assert "warning" in captured.out
            assert "TestGroup" in captured.out
            assert "claude-code, other-client" in captured.out
            assert "## Document Bundle" in captured.out
            assert "## Phases" in captured.out
            assert "Test prompt content" in captured.out
            assert "## Draft Instructions" in captured.out
            assert "Custom draft instructions" in captured.out

    def test_document_rule_with_minimal_fields(self, temp_dir, capsys):
        """Test documenting a rule with only required fields."""
        rule = RuleDefinition(
            description="Minimal test rule",
            scope="project_level",
            context="Minimal context",
            requires_project_context=True,
        )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="General",
            rule_definitions={"minimal_rule": rule},
        )

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="minimal_rule",
                    project=str(temp_dir),
                    format_type="markdown",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "# minimal_rule" in captured.out
            assert "Minimal test rule" in captured.out
            # Check default severity is shown
            assert "fail (default)" in captured.out
            # Check default group is shown
            assert "General" in captured.out

    def test_document_html_escaping(self, temp_dir, capsys):
        """Test that HTML format properly escapes special characters."""
        rule = RuleDefinition(
            description='Rule with <special> & "characters"',
            scope="project_level",
            context="Context with <html> & 'quotes'",
            requires_project_context=True,
        )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={"escape_test": rule},
        )

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="escape_test",
                    project=str(temp_dir),
                    format_type="html",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            # Special characters should be escaped
            assert "&lt;special&gt;" in captured.out
            assert "&amp;" in captured.out
            assert "&lt;html&gt;" in captured.out

    def test_document_multiple_rules_html_format(self, temp_dir, capsys):
        """Test documenting multiple rules in HTML format includes proper wrapper."""
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

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={
                "rule1": rule1,
                "rule2": rule2,
            },
        )

        with patch("drift.cli.commands.document.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                document_command(
                    rules="rule1,rule2",
                    project=str(temp_dir),
                    format_type="html",
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            # Check HTML document structure
            assert "<!DOCTYPE html>" in captured.out
            assert "<html>" in captured.out
            assert "<head>" in captured.out
            assert "<title>Drift Rules Documentation</title>" in captured.out
            assert "</head>" in captured.out
            assert "<body>" in captured.out
            assert "</body>" in captured.out
            assert "</html>" in captured.out
            assert "Documentation for 2 rules" in captured.out


class TestPrintFunctions:
    """Tests for print_error, print_warning, and print_success functions."""

    def test_print_error_message_to_stderr(self, capsys):
        """Test that print_error outputs to stderr with color."""
        print_error("Test error message")

        captured = capsys.readouterr()
        assert "Test error message" in captured.err
        assert captured.out == ""

    def test_print_warning_message_to_stderr(self, capsys):
        """Test that print_warning outputs to stderr with color."""
        print_warning("Test warning message")

        captured = capsys.readouterr()
        assert "Test warning message" in captured.err
        assert captured.out == ""

    def test_print_success_message_to_stdout(self, capsys):
        """Test that print_success outputs to stdout with color."""
        print_success("Test success message")

        captured = capsys.readouterr()
        assert "Test success message" in captured.out
        assert captured.err == ""


class TestFormatRuleMarkdown:
    """Tests for format_rule_markdown function."""

    @pytest.fixture
    def minimal_config(self):
        """Create minimal config for testing."""
        return DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="DefaultGroup",
            rule_definitions={},
        )

    def test_format_rule_markdown_minimal_rule(self, minimal_config):
        """Test formatting minimal rule to markdown."""
        rule = RuleDefinition(
            description="Simple test",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
        )

        output = format_rule_markdown("test_rule", rule, minimal_config)

        assert "# test_rule" in output
        assert "## Description" in output
        assert "Simple test" in output
        assert "## Metadata" in output
        assert "project_level" in output
        assert "True" in output
        assert "## Context" in output
        assert "Test context" in output
        assert "DefaultGroup" in output

    def test_format_rule_markdown_with_validation_rules(self, minimal_config):
        """Test formatting rule with validation rules."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                rules=[
                    ValidationRule(
                        rule_type="core:file_exists",
                        description="Check file exists",
                        params={"file_path": "test.md", "other_param": 123},
                    ),
                    ValidationRule(
                        rule_type="core:regex_match",
                        description="Check pattern",
                        params={"pattern": "test.*"},
                    ),
                ],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                ),
            ),
        )

        output = format_rule_markdown("validation_test", rule, minimal_config)

        assert "## Validation Rules" in output
        assert "### 1. core:file_exists" in output
        assert "Check file exists" in output
        assert "`file_path`: test.md" in output
        assert "`other_param`: 123" in output
        assert "### 2. core:regex_match" in output
        assert "Check pattern" in output

    def test_format_rule_markdown_with_phases_all_fields(self, minimal_config):
        """Test formatting rule with phases containing all fields."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            phases=[
                PhaseDefinition(
                    name="test_phase",
                    type="prompt",
                    provider="bedrock",
                    model="claude-v2",
                    prompt="This is a test prompt\nwith multiple lines",
                    params={"temperature": 0.7, "max_tokens": 1000},
                    available_resources=["skill", "agent", "command"],
                ),
            ],
        )

        output = format_rule_markdown("phase_test", rule, minimal_config)

        assert "## Phases" in output
        assert "### 1. test_phase" in output
        assert "- **Type**: prompt" in output
        assert "- **Provider**: bedrock" in output
        assert "- **Model**: claude-v2" in output
        assert "**Prompt**:" in output
        assert "This is a test prompt" in output
        assert "with multiple lines" in output
        assert "**Parameters**:" in output
        assert "`temperature`: 0.7" in output
        assert "`max_tokens`: 1000" in output
        assert "**Available Resources**: skill, agent, command" in output

    def test_format_rule_markdown_with_draft_instructions(self, minimal_config):
        """Test formatting rule with draft instructions."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            draft_instructions="Custom instructions for {file_path}\nwith placeholders",
        )

        output = format_rule_markdown("draft_test", rule, minimal_config)

        assert "## Draft Instructions" in output
        assert "Custom instructions for {file_path}" in output
        assert "with placeholders" in output

    def test_format_rule_markdown_severity_explicit(self, minimal_config):
        """Test formatting rule with explicit severity."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            severity=SeverityLevel.WARNING,
        )

        output = format_rule_markdown("severity_test", rule, minimal_config)

        assert "**Severity**: warning" in output
        assert "(default)" not in output

    def test_format_rule_markdown_severity_default_conversation(self, minimal_config):
        """Test formatting conversation-level rule uses default severity warning."""
        rule = RuleDefinition(
            description="Test",
            scope="conversation_level",
            context="Context",
            requires_project_context=False,
        )

        output = format_rule_markdown("conv_test", rule, minimal_config)

        assert "**Severity**: warning (default)" in output

    def test_format_rule_markdown_severity_default_project(self, minimal_config):
        """Test formatting project-level rule uses default severity fail."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
        )

        output = format_rule_markdown("proj_test", rule, minimal_config)

        assert "**Severity**: fail (default)" in output

    def test_format_rule_markdown_explicit_group_name(self, minimal_config):
        """Test formatting rule with explicit group name."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            group_name="CustomGroup",
        )

        output = format_rule_markdown("group_test", rule, minimal_config)

        assert "**Group**: CustomGroup" in output

    def test_format_rule_markdown_supported_clients_explicit(self, minimal_config):
        """Test formatting rule with explicit supported clients."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            supported_clients=["claude-code", "other-client"],
        )

        output = format_rule_markdown("clients_test", rule, minimal_config)

        assert "**Supported Clients**: claude-code, other-client" in output

    def test_format_rule_markdown_supported_clients_default(self, minimal_config):
        """Test formatting rule without supported clients shows all."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
        )

        output = format_rule_markdown("default_clients", rule, minimal_config)

        assert "**Supported Clients**: all" in output

    def test_format_rule_markdown_document_bundle_with_resources(self, minimal_config):
        """Test formatting rule with document bundle including resources."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.md", "**/*.txt"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
                resource_patterns=["**/*.py", "src/**/*.rs"],
            ),
        )

        output = format_rule_markdown("bundle_test", rule, minimal_config)

        assert "## Document Bundle" in output
        assert "- **Bundle Type**: test" in output
        assert "- **Bundle Strategy**: individual" in output
        assert "- **File Patterns**:" in output
        assert "  - `*.md`" in output
        assert "  - `**/*.txt`" in output
        assert "- **Resource Patterns**:" in output
        assert "  - `**/*.py`" in output
        assert "  - `src/**/*.rs`" in output


class TestFormatRuleHTML:
    """Tests for format_rule_html function."""

    @pytest.fixture
    def minimal_config(self):
        """Create minimal config for testing."""
        return DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            default_group_name="DefaultGroup",
            rule_definitions={},
        )

    def test_format_rule_html_minimal_rule(self, minimal_config):
        """Test formatting minimal rule to HTML."""
        rule = RuleDefinition(
            description="Simple test",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
        )

        output = format_rule_html("test_rule", rule, minimal_config)

        assert "<h1>test_rule</h1>" in output
        assert "<h2>Description</h2>" in output
        assert "<p>Simple test</p>" in output
        assert "<h2>Metadata</h2>" in output
        assert "<ul>" in output
        assert "project_level" in output
        assert "True" in output
        assert "<h2>Context</h2>" in output
        assert "Test context" in output

    def test_format_rule_html_escapes_special_characters(self, minimal_config):
        """Test that HTML format escapes special characters."""
        rule = RuleDefinition(
            description='Rule with <tags> & "quotes"',
            scope="project_level",
            context='Context with <script> & "data"',
            requires_project_context=True,
        )

        output = format_rule_html("escape_test", rule, minimal_config)

        # Check that special characters are escaped
        assert "&lt;tags&gt;" in output
        assert "&amp;" in output
        assert "&quot;" in output
        assert "&lt;script&gt;" in output
        # Should not contain raw special characters
        assert "<tags>" not in output
        assert "<script>" not in output

    def test_format_rule_html_with_validation_rules(self, minimal_config):
        """Test formatting rule with validation rules in HTML."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                rules=[
                    ValidationRule(
                        rule_type="core:file_exists",
                        description="Check file exists",
                        params={"file_path": "test.md", "count": 5},
                    ),
                ],
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                ),
            ),
        )

        output = format_rule_html("validation_test", rule, minimal_config)

        assert "<h2>Validation Rules</h2>" in output
        assert "<h3>1. core:file_exists</h3>" in output
        assert "Check file exists" in output
        assert "<code>file_path</code>" in output
        assert "test.md" in output
        assert "<code>count</code>" in output
        assert "5" in output

    def test_format_rule_html_with_phases_all_fields(self, minimal_config):
        """Test formatting rule with phases containing all fields in HTML."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            phases=[
                PhaseDefinition(
                    name="test_phase",
                    type="prompt",
                    provider="bedrock",
                    model="claude-v2",
                    prompt="Test prompt with <tags>",
                    params={"temperature": 0.7},
                    available_resources=["skill", "agent"],
                ),
            ],
        )

        output = format_rule_html("phase_test", rule, minimal_config)

        assert "<h2>Phases</h2>" in output
        assert "<h3>1. test_phase</h3>" in output
        assert "<strong>Type</strong>: prompt" in output
        assert "<strong>Provider</strong>: bedrock" in output
        assert "<strong>Model</strong>: claude-v2" in output
        assert "<p><strong>Prompt</strong>:</p>" in output
        assert "<pre><code>" in output
        assert "&lt;tags&gt;" in output  # Should be escaped
        assert "<strong>Parameters</strong>:" in output
        assert "<code>temperature</code>" in output
        assert "0.7" in output
        assert "<strong>Available Resources</strong>: skill, agent" in output

    def test_format_rule_html_with_draft_instructions(self, minimal_config):
        """Test formatting rule with draft instructions in HTML."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            draft_instructions="Custom <instructions> & {placeholders}",
        )

        output = format_rule_html("draft_test", rule, minimal_config)

        assert "<h2>Draft Instructions</h2>" in output
        assert "&lt;instructions&gt;" in output
        assert "{placeholders}" in output

    def test_format_rule_html_severity_explicit(self, minimal_config):
        """Test formatting rule with explicit severity in HTML."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            severity=SeverityLevel.FAIL,
        )

        output = format_rule_html("severity_test", rule, minimal_config)

        assert "<strong>Severity</strong>: fail" in output
        assert "(default)" not in output

    def test_format_rule_html_severity_default_conversation(self, minimal_config):
        """Test formatting conversation-level rule severity in HTML."""
        rule = RuleDefinition(
            description="Test",
            scope="conversation_level",
            context="Context",
            requires_project_context=False,
        )

        output = format_rule_html("conv_test", rule, minimal_config)

        assert "<strong>Severity</strong>: warning (default)" in output

    def test_format_rule_html_document_bundle_with_resources(self, minimal_config):
        """Test formatting rule with document bundle including resources in HTML."""
        rule = RuleDefinition(
            description="Test",
            scope="project_level",
            context="Context",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="test",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.COLLECTION,
                resource_patterns=["**/*.py"],
            ),
        )

        output = format_rule_html("bundle_test", rule, minimal_config)

        assert "<h2>Document Bundle</h2>" in output
        assert "<strong>Bundle Type</strong>: test" in output
        assert "<strong>Bundle Strategy</strong>: collection" in output
        assert "<strong>File Patterns</strong>:" in output
        assert "<code>*.md</code>" in output
        assert "<strong>Resource Patterns</strong>:" in output
        assert "<code>**/*.py</code>" in output
