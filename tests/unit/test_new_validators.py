"""Tests for new validators (ListMatch and ListRegexMatch)."""

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle
from drift.documents.loader import DocumentLoader
from drift.validation.validators import (
    ListMatchValidator,
    ListRegexMatchValidator,
    ValidatorRegistry,
)


class TestListMatchValidator:
    """Tests for ListMatchValidator."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create temporary project structure."""
        # Create skills
        skill_dir1 = tmp_path / ".claude" / "skills" / "skill-one"
        skill_dir1.mkdir(parents=True)
        (skill_dir1 / "SKILL.md").write_text("# Skill One")

        skill_dir2 = tmp_path / ".claude" / "skills" / "skill-two"
        skill_dir2.mkdir(parents=True)
        (skill_dir2 / "SKILL.md").write_text("# Skill Two")

        # Create commands
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "cmd-one.md").write_text("# Command One")
        (cmd_dir / "cmd-two.md").write_text("# Command Two")

        return tmp_path

    @pytest.fixture
    def bundle(self, project_root):
        """Create test bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            files=[],
            project_path=project_root,
        )

    @pytest.fixture
    def loader(self, project_root):
        """Create document loader."""
        return DocumentLoader(project_root)

    def test_list_match_all_in_passes(self, bundle, loader):
        """Test LIST_MATCH with all_in mode passes when all items found."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Check skills match",
            params={
                "items": {"type": "string_list", "value": ["skill-one", "skill-two"]},
                "target": {"type": "resource_list", "value": "skill"},
                "match_mode": "all_in",
            },
            failure_message="Skills not found",
            expected_behavior="All skills should exist",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Validation passes

    def test_list_match_all_in_fails(self, bundle, loader):
        """Test LIST_MATCH with all_in mode fails when items missing."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Check skills match",
            params={
                "items": {"type": "string_list", "value": ["skill-one", "skill-missing"]},
                "target": {"type": "resource_list", "value": "skill"},
                "match_mode": "all_in",
            },
            failure_message="Skills not found",
            expected_behavior="All skills should exist",
        )

        result = validator.validate(rule, bundle)
        assert result is not None  # Validation fails
        assert "skill-missing" in result.context

    def test_list_match_none_in_passes(self, bundle, loader):
        """Test LIST_MATCH with none_in mode passes when no items found."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Check no forbidden skills",
            params={
                "items": {"type": "string_list", "value": ["forbidden-skill"]},
                "target": {"type": "resource_list", "value": "skill"},
                "match_mode": "none_in",
            },
            failure_message="Forbidden skill found",
            expected_behavior="No forbidden skills should exist",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Validation passes

    def test_list_match_none_in_fails(self, bundle, loader):
        """Test LIST_MATCH with none_in mode fails when items found."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Check no forbidden skills",
            params={
                "items": {"type": "string_list", "value": ["skill-one"]},
                "target": {"type": "resource_list", "value": "skill"},
                "match_mode": "none_in",
            },
            failure_message="Forbidden skill found",
            expected_behavior="No forbidden skills should exist",
        )

        result = validator.validate(rule, bundle)
        assert result is not None  # Validation fails
        assert "skill-one" in result.context

    def test_list_match_exact_passes(self, bundle, loader):
        """Test LIST_MATCH with exact mode passes when lists match."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Check exact skill match",
            params={
                "items": {"type": "string_list", "value": ["skill-one", "skill-two"]},
                "target": {"type": "resource_list", "value": "skill"},
                "match_mode": "exact",
            },
            failure_message="Skills don't match exactly",
            expected_behavior="Skills should match exactly",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Validation passes

    def test_list_match_exact_fails(self, bundle, loader):
        """Test LIST_MATCH with exact mode fails when lists differ."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Check exact skill match",
            params={
                "items": {"type": "string_list", "value": ["skill-one"]},
                "target": {"type": "resource_list", "value": "skill"},
                "match_mode": "exact",
            },
            failure_message="Skills don't match exactly",
            expected_behavior="Skills should match exactly",
        )

        result = validator.validate(rule, bundle)
        assert result is not None  # Validation fails

    def test_list_match_default_mode(self, bundle, loader):
        """Test LIST_MATCH uses all_in as default mode."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Check skills",
            params={
                "items": {"type": "string_list", "value": ["skill-one"]},
                "target": {"type": "resource_list", "value": "skill"},
            },
            failure_message="Skill not found",
            expected_behavior="Skill should exist",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Validation passes with default all_in mode

    def test_list_match_missing_params(self, bundle, loader):
        """Test LIST_MATCH raises error when params missing."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Invalid rule",
            params={},
            failure_message="Error",
            expected_behavior="Behavior",
        )

        with pytest.raises(ValueError, match="requires 'items' and 'target' params"):
            validator.validate(rule, bundle)

    def test_list_match_unknown_mode(self, bundle, loader):
        """Test LIST_MATCH raises error with unknown match_mode."""
        validator = ListMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Invalid mode",
            params={
                "items": {"type": "string_list", "value": ["skill-one"]},
                "target": {"type": "resource_list", "value": "skill"},
                "match_mode": "unknown_mode",
            },
            failure_message="Error",
            expected_behavior="Behavior",
        )

        with pytest.raises(ValueError, match="Unknown match_mode"):
            validator.validate(rule, bundle)


class TestListRegexMatchValidator:
    """Tests for ListRegexMatchValidator."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create temporary project structure."""
        # Create skills
        skill_dir1 = tmp_path / ".claude" / "skills" / "api-skill"
        skill_dir1.mkdir(parents=True)
        (skill_dir1 / "SKILL.md").write_text("# API Skill")

        skill_dir2 = tmp_path / ".claude" / "skills" / "test-skill"
        skill_dir2.mkdir(parents=True)
        (skill_dir2 / "SKILL.md").write_text("# Test Skill")

        # Create settings file
        (tmp_path / "settings.json").write_text(
            "{\n" '  "authorized": [\n' '    "/api-skill",\n' '    "/test-skill"\n' "  ]\n" "}"
        )

        return tmp_path

    @pytest.fixture
    def bundle(self, project_root):
        """Create test bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            files=[],
            project_path=project_root,
        )

    @pytest.fixture
    def loader(self, project_root):
        """Create document loader."""
        return DocumentLoader(project_root)

    def test_list_regex_match_all_in_passes(self, bundle, loader):
        """Test LIST_REGEX_MATCH with all_in mode passes when all found."""
        validator = ListRegexMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_REGEX_MATCH,
            description="Check skills authorized",
            params={
                "items": {"type": "resource_list", "value": "skill"},
                "file_path": {"type": "file_content", "value": "settings.json"},
                "pattern": {"type": "regex_pattern", "value": r'"/([^"]+)"'},
                "match_mode": "all_in",
            },
            failure_message="Skills not authorized",
            expected_behavior="All skills should be authorized",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Validation passes

    def test_list_regex_match_all_in_fails(self, bundle, loader, project_root):
        """Test LIST_REGEX_MATCH with all_in mode fails when missing."""
        # Add another skill that's not in settings
        skill_dir3 = project_root / ".claude" / "skills" / "new-skill"
        skill_dir3.mkdir(parents=True)
        (skill_dir3 / "SKILL.md").write_text("# New Skill")

        validator = ListRegexMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_REGEX_MATCH,
            description="Check skills authorized",
            params={
                "items": {"type": "resource_list", "value": "skill"},
                "file_path": {"type": "file_content", "value": "settings.json"},
                "pattern": {"type": "regex_pattern", "value": r'"/([^"]+)"'},
                "match_mode": "all_in",
            },
            failure_message="Skills not authorized",
            expected_behavior="All skills should be authorized",
        )

        result = validator.validate(rule, bundle)
        assert result is not None  # Validation fails
        assert "new-skill" in result.context

    def test_list_regex_match_none_in_passes(self, bundle, loader):
        """Test LIST_REGEX_MATCH with none_in mode passes when not found."""
        validator = ListRegexMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_REGEX_MATCH,
            description="Check no forbidden skills",
            params={
                "items": {"type": "string_list", "value": ["forbidden-skill"]},
                "file_path": {"type": "file_content", "value": "settings.json"},
                "pattern": {"type": "regex_pattern", "value": r'"/([^"]+)"'},
                "match_mode": "none_in",
            },
            failure_message="Forbidden skill found",
            expected_behavior="No forbidden skills",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Validation passes

    def test_list_regex_match_none_in_fails(self, bundle, loader):
        """Test LIST_REGEX_MATCH with none_in mode fails when found."""
        validator = ListRegexMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_REGEX_MATCH,
            description="Check no forbidden skills",
            params={
                "items": {"type": "string_list", "value": ["api-skill"]},
                "file_path": {"type": "file_content", "value": "settings.json"},
                "pattern": {"type": "regex_pattern", "value": r'"/([^"]+)"'},
                "match_mode": "none_in",
            },
            failure_message="Forbidden skill found",
            expected_behavior="No forbidden skills",
        )

        result = validator.validate(rule, bundle)
        assert result is not None  # Validation fails
        assert "api-skill" in result.context

    def test_list_regex_match_missing_params(self, bundle, loader):
        """Test LIST_REGEX_MATCH raises error when params missing."""
        validator = ListRegexMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_REGEX_MATCH,
            description="Invalid rule",
            params={},
            failure_message="Error",
            expected_behavior="Behavior",
        )

        with pytest.raises(ValueError, match="requires 'items', 'file_path', and 'pattern' params"):
            validator.validate(rule, bundle)

    def test_list_regex_match_unknown_mode(self, bundle, loader):
        """Test LIST_REGEX_MATCH raises error with unknown match_mode."""
        validator = ListRegexMatchValidator(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_REGEX_MATCH,
            description="Invalid mode",
            params={
                "items": {"type": "string_list", "value": ["api-skill"]},
                "file_path": {"type": "file_content", "value": "settings.json"},
                "pattern": {"type": "regex_pattern", "value": r'"/([^"]+)"'},
                "match_mode": "unknown_mode",
            },
            failure_message="Error",
            expected_behavior="Behavior",
        )

        with pytest.raises(ValueError, match="Unknown match_mode"):
            validator.validate(rule, bundle)


class TestValidatorRegistryWithNewValidators:
    """Test ValidatorRegistry with new validators."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create temporary project structure."""
        skill_dir = tmp_path / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test")
        return tmp_path

    @pytest.fixture
    def bundle(self, project_root):
        """Create test bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            files=[],
            project_path=project_root,
        )

    @pytest.fixture
    def loader(self, project_root):
        """Create document loader."""
        return DocumentLoader(project_root)

    def test_registry_includes_list_match(self, loader):
        """Test registry includes LIST_MATCH validator."""
        registry = ValidatorRegistry(loader)
        assert ValidationType.LIST_MATCH in registry._validators

    def test_registry_includes_list_regex_match(self, loader):
        """Test registry includes LIST_REGEX_MATCH validator."""
        registry = ValidatorRegistry(loader)
        assert ValidationType.LIST_REGEX_MATCH in registry._validators

    def test_registry_execute_list_match_rule(self, bundle, loader):
        """Test registry can execute LIST_MATCH rules."""
        registry = ValidatorRegistry(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_MATCH,
            description="Test",
            params={
                "items": {"type": "string_list", "value": ["test-skill"]},
                "target": {"type": "resource_list", "value": "skill"},
            },
            failure_message="Fail",
            expected_behavior="Pass",
        )

        result = registry.execute_rule(rule, bundle)
        assert result is None  # Should pass

    def test_registry_execute_list_regex_match_rule(self, bundle, loader, project_root):
        """Test registry can execute LIST_REGEX_MATCH rules."""
        # Create test file
        (project_root / "test.txt").write_text("test-skill")

        registry = ValidatorRegistry(loader)
        rule = ValidationRule(
            rule_type=ValidationType.LIST_REGEX_MATCH,
            description="Test",
            params={
                "items": {"type": "string_list", "value": ["test-skill"]},
                "file_path": {"type": "file_content", "value": "test.txt"},
                "pattern": {"type": "regex_pattern", "value": r"(\w+-\w+)"},
            },
            failure_message="Fail",
            expected_behavior="Pass",
        )

        result = registry.execute_rule(rule, bundle)
        assert result is None  # Should pass
