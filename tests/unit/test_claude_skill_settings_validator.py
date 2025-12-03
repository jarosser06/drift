"""Unit tests for ClaudeSkillSettingsValidator."""

import json

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle
from drift.validation.validators import ClaudeSkillSettingsValidator


class TestClaudeSkillSettingsValidator:
    """Tests for ClaudeSkillSettingsValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ClaudeSkillSettingsValidator()

    @pytest.fixture
    def rule(self):
        """Create validation rule."""
        return ValidationRule(
            rule_type=ValidationType.CLAUDE_SKILL_SETTINGS,
            description="Check that all skills have permissions",
            failure_message="Skills missing from settings.json permissions",
            expected_behavior="All skills should have Skill() entries in permissions.allow",
        )

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create document bundle with temporary project path."""
        return DocumentBundle(
            bundle_id="test-bundle",
            bundle_type="project",
            bundle_strategy="individual",
            files=[],
            project_path=tmp_path,
        )

    def test_validation_passes_with_all_skills_permitted(self, validator, rule, bundle, tmp_path):
        """Test that validation passes when all skills have permissions."""
        # Create skills directory with skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()
        (skills_dir / "linting").mkdir()
        (skills_dir / "python-docs").mkdir()

        # Create settings.json with all skills
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "Skill(testing)",
                    "Skill(linting)",
                    "Skill(python-docs)",
                    "Bash(ls:*)",
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        # Validate
        result = validator.validate(rule, bundle)
        assert result is None

    def test_validation_fails_with_missing_skill_permissions(
        self, validator, rule, bundle, tmp_path
    ):
        """Test that validation fails when skills are missing permissions."""
        # Create skills directory with skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()
        (skills_dir / "linting").mkdir()
        (skills_dir / "python-docs").mkdir()

        # Create settings.json with only some skills
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {"permissions": {"allow": ["Skill(testing)", "Bash(ls:*)"]}}
        settings_file.write_text(json.dumps(settings))

        # Validate
        result = validator.validate(rule, bundle)
        assert result is not None
        assert "linting" in result.context
        assert "python-docs" in result.context
        assert "Skills missing from permissions.allow" in result.context

    def test_validation_passes_with_no_skills_directory(self, validator, rule, bundle, tmp_path):
        """Test that validation passes when there's no skills directory."""
        # Don't create skills directory
        result = validator.validate(rule, bundle)
        assert result is None

    def test_validation_passes_with_empty_skills_directory(self, validator, rule, bundle, tmp_path):
        """Test that validation passes when skills directory is empty."""
        # Create empty skills directory
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)

        # Create settings.json
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {"permissions": {"allow": []}}
        settings_file.write_text(json.dumps(settings))

        result = validator.validate(rule, bundle)
        assert result is None

    def test_validation_fails_when_settings_json_missing(self, validator, rule, bundle, tmp_path):
        """Test that validation fails when settings.json doesn't exist."""
        # Create skills directory with skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()

        # Don't create settings.json
        result = validator.validate(rule, bundle)
        assert result is not None
        assert "settings.json not found" in result.context

    def test_validation_fails_with_invalid_json(self, validator, rule, bundle, tmp_path):
        """Test that validation fails when settings.json has invalid JSON."""
        # Create skills directory with skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()

        # Create settings.json with invalid JSON
        settings_file = tmp_path / ".claude" / "settings.json"
        settings_file.write_text("{ invalid json }")

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Invalid JSON" in result.context

    def test_validation_ignores_hidden_directories(self, validator, rule, bundle, tmp_path):
        """Test that validation ignores hidden directories (starting with .)."""
        # Create skills directory with visible and hidden directories
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()
        (skills_dir / ".hidden").mkdir()

        # Create settings.json with only visible skill
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {"permissions": {"allow": ["Skill(testing)"]}}
        settings_file.write_text(json.dumps(settings))

        # Validate - should pass (hidden dir ignored)
        result = validator.validate(rule, bundle)
        assert result is None

    def test_validation_handles_missing_permissions_key(self, validator, rule, bundle, tmp_path):
        """Test that validation handles settings.json without permissions key."""
        # Create skills directory with skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()

        # Create settings.json without permissions key
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {"other_config": "value"}
        settings_file.write_text(json.dumps(settings))

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "testing" in result.context

    def test_validation_handles_missing_allow_key(self, validator, rule, bundle, tmp_path):
        """Test that validation handles permissions without allow key."""
        # Create skills directory with skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()

        # Create settings.json with permissions but no allow
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {"permissions": {"deny": []}}
        settings_file.write_text(json.dumps(settings))

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "testing" in result.context

    def test_regex_pattern_matches_skill_entries(self, validator, rule, bundle, tmp_path):
        """Test that regex correctly extracts skill names from Skill() entries."""
        # Create skills directory with skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "my-skill").mkdir()
        (skills_dir / "another_skill").mkdir()

        # Create settings.json with various permission formats
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "Skill(my-skill)",
                    "Skill(another_skill)",
                    "Bash(ls:*)",
                    "mcp__github",
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        result = validator.validate(rule, bundle)
        assert result is None

    def test_validation_provides_helpful_error_message(self, validator, rule, bundle, tmp_path):
        """Test that validation error provides helpful suggestion."""
        # Create skills directory with missing permission
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "new-skill").mkdir()

        # Create settings.json without the skill
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {"permissions": {"allow": []}}
        settings_file.write_text(json.dumps(settings))

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "new-skill" in result.context
        assert "Add entries like 'Skill(new-skill)'" in result.context

    def test_validation_with_multiple_missing_skills(self, validator, rule, bundle, tmp_path):
        """Test that validation reports all missing skills."""
        # Create skills directory with multiple skills
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "skill1").mkdir()
        (skills_dir / "skill2").mkdir()
        (skills_dir / "skill3").mkdir()

        # Create settings.json with only one skill
        settings_file = tmp_path / ".claude" / "settings.json"
        settings = {"permissions": {"allow": ["Skill(skill1)"]}}
        settings_file.write_text(json.dumps(settings))

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "skill2" in result.context
        assert "skill3" in result.context

    def test_validation_file_paths_in_result(self, validator, rule, bundle, tmp_path):
        """Test that validation result includes correct file path."""
        # Create skills directory with skill
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing").mkdir()

        # Don't create settings.json
        result = validator.validate(rule, bundle)
        assert result is not None
        assert ".claude/settings.json" in result.file_paths
