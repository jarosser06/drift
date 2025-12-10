"""Unit tests for draft command."""

from unittest.mock import patch

import pytest

from drift.cli.commands.draft import draft_command
from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    DriftConfig,
    ModelConfig,
    PhaseDefinition,
    ProviderConfig,
    ProviderType,
    RuleDefinition,
)


class TestDraftCommand:
    """Tests for draft_command function."""

    @pytest.fixture
    def sample_eligible_rule(self):
        """Create a sample eligible rule for testing."""
        return RuleDefinition(
            description="Test skill validation",
            scope="project_level",
            context="Skills need documentation",
            requires_project_context=True,
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
    def sample_config(self, sample_eligible_rule):
        """Create a sample config with eligible rule."""
        return DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={"skill_validation": sample_eligible_rule},
        )

    def test_draft_rule_not_found(self, temp_dir, sample_config):
        """Test error when rule doesn't exist in configuration."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="nonexistent_rule",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_rule_not_eligible_no_document_bundle(self, temp_dir):
        """Test error when rule is not eligible (no document_bundle)."""
        ineligible_rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=None,  # No document bundle
        )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={"test_rule": ineligible_rule},
        )

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="test_rule",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_rule_not_eligible_collection_strategy(self, temp_dir):
        """Test error when rule uses collection strategy."""
        ineligible_rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.COLLECTION,  # Collection, not individual
            ),
        )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={"test_rule": ineligible_rule},
        )

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="test_rule",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_rule_not_eligible_conversation_level(self, temp_dir):
        """Test error when rule has conversation_level scope."""
        ineligible_rule = RuleDefinition(
            description="Test rule",
            scope="conversation_level",  # Not project_level
            context="Test",
            requires_project_context=False,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={"test_rule": ineligible_rule},
        )

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="test_rule",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_wildcard_pattern_without_target_file(self, temp_dir, sample_config):
        """Test error when wildcard pattern used without --target-file."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            # Rule has wildcard pattern, no --target-file provided
            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_wildcard_pattern_error_message(self, temp_dir, sample_config, capsys):
        """Test error message for wildcard pattern without --target-file."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "wildcard pattern" in captured.err
            assert "--target-file" in captured.err

    def test_draft_files_exist_without_force(self, temp_dir, sample_config):
        """Test that command refuses to generate prompt when file exists without --force."""
        # Create directory structure and file
        skill_dir = temp_dir / ".claude" / "skills" / "testing"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Existing skill")

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    target_file=".claude/skills/testing/SKILL.md",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_files_exist_with_force(self, temp_dir, sample_config):
        """Test that command generates prompt when file exists with --force."""
        # Create directory structure and file
        skill_dir = temp_dir / ".claude" / "skills" / "testing"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Existing skill")

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            # Should exit with 0 (success)
            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    target_file=".claude/skills/testing/SKILL.md",
                    project=str(temp_dir),
                    force=True,  # Force generation
                    verbose=0,
                )

            assert exc_info.value.code == 0

    def test_draft_success_prints_to_stdout(self, temp_dir, sample_config, capsys):
        """Test successful generation prints prompt to stdout."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    target_file=".claude/skills/testing/SKILL.md",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            assert "# Draft Prompt: skill_validation" in captured.out
            assert "Test skill validation" in captured.out
            assert ".claude/skills/testing/SKILL.md" in captured.out

    def test_draft_success_writes_to_file(self, temp_dir, sample_config):
        """Test successful generation writes prompt to output file."""
        output_file = temp_dir / "draft_instructions.md"

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    target_file=".claude/skills/testing/SKILL.md",
                    project=str(temp_dir),
                    output=str(output_file),
                    verbose=0,
                )

            assert exc_info.value.code == 0

        # Check file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert "# Draft Prompt: skill_validation" in content
        assert "Test skill validation" in content

    def test_draft_output_file_write_error(self, temp_dir, sample_config):
        """Test error handling when output file can't be written."""
        # Use invalid path for output
        output_file = "/invalid/path/to/file.md"

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    target_file=".claude/skills/testing/SKILL.md",
                    project=str(temp_dir),
                    output=output_file,
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_config_load_error(self, temp_dir):
        """Test error handling when config loading fails."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = ValueError("Invalid config")

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_project_path_not_exists(self):
        """Test error when project path doesn't exist."""
        with pytest.raises(SystemExit) as exc_info:
            draft_command(
                rule="skill_validation",
                project="/nonexistent/path",
                verbose=0,
            )

        assert exc_info.value.code == 1

    def test_draft_uses_current_dir_when_no_project(self, temp_dir, sample_config):
        """Test that bootstrap uses current directory when project not specified."""
        import os

        # Change to temp_dir so Path.cwd() returns a valid path
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)

            with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
                mock_load.return_value = sample_config

                # Will fail because rule pattern doesn't match, but proves cwd was used
                with pytest.raises(SystemExit):
                    draft_command(
                        rule="skill_validation",
                        verbose=0,
                    )

                # Check that load_config was called with current directory (temp_dir)
                mock_load.assert_called_once()
                # Resolve both paths to handle macOS /var -> /private/var symlink
                assert mock_load.call_args[0][0].resolve() == temp_dir.resolve()
        finally:
            os.chdir(original_cwd)

    def test_draft_with_custom_draft_instructions(self, temp_dir):
        """Test generation with custom draft_instructions in rule."""
        rule = RuleDefinition(
            description="Test skill validation",
            scope="project_level",
            context="Skills need documentation",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            draft_instructions="Custom prompt for {file_path}",
        )

        config = DriftConfig(
            providers={"bedrock": ProviderConfig(provider=ProviderType.BEDROCK, params={})},
            models={"haiku": ModelConfig(provider="bedrock", model_id="test-model", params={})},
            default_model="haiku",
            rule_definitions={"skill_validation": rule},
        )

        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    target_file=".claude/skills/testing/SKILL.md",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

    def test_draft_with_target_file_shows_correct_path(self, temp_dir, sample_config, capsys):
        """Test that generated prompt shows the specific target file path."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    target_file=".claude/skills/testing/SKILL.md",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 0

            captured = capsys.readouterr()
            # Should show the specific target file, not the wildcard pattern
            assert ".claude/skills/testing/SKILL.md" in captured.out
            # Should NOT show wildcard pattern in File Existence section
            assert "File must exist at: `.claude/skills/testing/SKILL.md`" in captured.out

    def test_draft_keyboard_interrupt(self, temp_dir, sample_config):
        """Test handling of keyboard interrupt."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = KeyboardInterrupt()

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_unexpected_error(self, temp_dir, sample_config):
        """Test handling of unexpected errors."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(SystemExit) as exc_info:
                draft_command(
                    rule="skill_validation",
                    project=str(temp_dir),
                    verbose=0,
                )

            assert exc_info.value.code == 1

    def test_draft_verbosity_levels(self, temp_dir, sample_config):
        """Test that different verbosity levels work."""
        with patch("drift.cli.commands.draft.ConfigLoader.load_config") as mock_load:
            mock_load.return_value = sample_config

            # Test various verbosity levels
            for verbose_level in [0, 1, 2, 3]:
                with pytest.raises(SystemExit) as exc_info:
                    draft_command(
                        rule="skill_validation",
                        target_file=".claude/skills/testing/SKILL.md",
                        project=str(temp_dir),
                        verbose=verbose_level,
                    )

                assert exc_info.value.code == 0
