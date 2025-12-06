"""Tests for ClaudeSettingsDuplicatesValidator."""

import json

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle
from drift.validation.validators.client.claude import ClaudeSettingsDuplicatesValidator


class TestClaudeSettingsDuplicatesValidator:
    """Tests for ClaudeSettingsDuplicatesValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ClaudeSettingsDuplicatesValidator()

    @pytest.fixture
    def validation_rule(self):
        """Create validation rule for testing."""
        return ValidationRule(
            rule_type="core:claude_settings_duplicates",
            description="Check for duplicate permissions",
            failure_message="Duplicate permissions found",
            expected_behavior="No duplicate permissions",
        )

    def test_no_settings_file_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when settings.json doesn't exist."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_empty_settings_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when settings.json is empty."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_no_permissions_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when no permissions exist."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {"permissions": {}}
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_empty_allow_list_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when allow list is empty."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {"permissions": {"allow": []}}
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_unique_permissions_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when all permissions are unique."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "Skill(testing)",
                    "Skill(linting)",
                    "mcp__github",
                    "mcp__serena",
                    "Bash(ls:*)",
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_duplicate_skill_permissions_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails when duplicate skill permissions exist."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "Skill(testing)",
                    "Skill(linting)",
                    "Skill(testing)",  # Duplicate
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "Skill(testing)" in result.context
        assert "Duplicate permission entries found" in result.context

    def test_duplicate_mcp_permissions_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails when duplicate MCP permissions exist."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "mcp__github",
                    "mcp__serena",
                    "mcp__github",  # Duplicate
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "mcp__github" in result.context
        assert "Duplicate permission entries found" in result.context

    def test_multiple_duplicates_all_reported(self, validator, validation_rule, tmp_path):
        """Test validation reports all duplicate entries."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "Skill(testing)",
                    "Skill(linting)",
                    "Skill(testing)",  # Duplicate
                    "mcp__github",
                    "mcp__github",  # Duplicate
                    "Bash(ls:*)",
                    "Bash(ls:*)",  # Duplicate
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "Skill(testing)" in result.context
        assert "mcp__github" in result.context
        assert "Bash(ls:*)" in result.context

    def test_invalid_json_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails with invalid JSON."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text("{ invalid json")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "Invalid JSON" in result.context

    def test_computation_type_is_programmatic(self, validator):
        """Test validator is programmatic."""
        assert validator.computation_type == "programmatic"

    def test_supported_clients_is_claude(self, validator):
        """Test validator only supports Claude."""
        from drift.config.models import ClientType

        clients = validator.supported_clients
        assert len(clients) == 1
        assert ClientType.CLAUDE in clients
