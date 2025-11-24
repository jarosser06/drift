"""Unit tests for validation system."""

import re

import pytest
from pydantic import ValidationError

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    ValidationRule,
    ValidationRulesConfig,
    ValidationType,
)
from drift.core.types import DocumentBundle
from drift.validation.validators import FileExistsValidator, ValidatorRegistry


class TestValidationRule:
    """Tests for ValidationRule model."""

    def test_valid_file_exists_rule(self):
        """Test creating a valid file existence rule."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Check CLAUDE.md exists",
            file_path="CLAUDE.md",
            failure_message="CLAUDE.md not found",
            expected_behavior="CLAUDE.md should exist",
        )
        assert rule.rule_type == ValidationType.FILE_EXISTS
        assert rule.file_path == "CLAUDE.md"
        assert rule.pattern is None

    def test_valid_regex_rule(self):
        """Test creating a valid regex matching rule."""
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Check for Prerequisites section",
            pattern=r"^## Prerequisites",
            flags=re.MULTILINE,
            failure_message="Missing Prerequisites section",
            expected_behavior="Should have Prerequisites section",
        )
        assert rule.rule_type == ValidationType.REGEX_MATCH
        assert rule.pattern == r"^## Prerequisites"
        assert rule.flags == re.MULTILINE

    def test_valid_file_count_rule(self):
        """Test creating a valid file count rule."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_COUNT,
            description="Limit number of commands",
            file_path=".claude/commands/*.md",
            max_count=20,
            failure_message="Too many commands",
            expected_behavior="Should have <= 20 commands",
        )
        assert rule.rule_type == ValidationType.FILE_COUNT
        assert rule.max_count == 20
        assert rule.min_count is None

    def test_valid_cross_file_reference_rule(self):
        """Test creating a valid cross-file reference rule."""
        rule = ValidationRule(
            rule_type=ValidationType.CROSS_FILE_REFERENCE,
            description="Check skill references",
            source_pattern=".claude/commands/*.md",
            reference_pattern=r"\[([^\]]+)\]\(.*?/skills/([^/]+)/SKILL\.md\)",
            target_pattern=".claude/skills/*/SKILL.md",
            failure_message="Broken skill reference",
            expected_behavior="All references should be valid",
        )
        assert rule.rule_type == ValidationType.CROSS_FILE_REFERENCE
        assert rule.source_pattern == ".claude/commands/*.md"
        assert rule.reference_pattern is not None

    def test_invalid_regex_pattern(self):
        """Test that invalid regex pattern raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationRule(
                rule_type=ValidationType.REGEX_MATCH,
                description="Invalid regex",
                pattern=r"[invalid(regex",  # Unclosed bracket
                failure_message="Test",
                expected_behavior="Test",
            )
        assert "Invalid regex pattern" in str(exc_info.value)

    def test_invalid_reference_pattern(self):
        """Test that invalid reference pattern raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ValidationRule(
                rule_type=ValidationType.CROSS_FILE_REFERENCE,
                description="Invalid reference pattern",
                reference_pattern=r"[invalid(regex",  # Unclosed bracket
                failure_message="Test",
                expected_behavior="Test",
            )
        assert "Invalid reference regex pattern" in str(exc_info.value)


class TestValidationRulesConfig:
    """Tests for ValidationRulesConfig model."""

    def test_valid_validation_rules_config(self):
        """Test creating a valid validation rules configuration."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Test rule",
            file_path="test.md",
            failure_message="Test failure",
            expected_behavior="Test expected",
        )

        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.COLLECTION,
        )

        config = ValidationRulesConfig(
            rules=[rule],
            scope="project_level",
            document_bundle=bundle_config,
        )

        assert len(config.rules) == 1
        assert config.scope == "project_level"
        assert config.document_bundle.bundle_type == "test"

    def test_default_scope(self):
        """Test default scope is document_level."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Test",
            file_path="test.md",
            failure_message="Test",
            expected_behavior="Test",
        )

        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.COLLECTION,
        )

        config = ValidationRulesConfig(
            rules=[rule],
            document_bundle=bundle_config,
        )

        assert config.scope == "document_level"

    def test_multiple_rules(self):
        """Test validation config with multiple rules."""
        rules = [
            ValidationRule(
                rule_type=ValidationType.FILE_EXISTS,
                description="Rule 1",
                file_path="test1.md",
                failure_message="Test 1",
                expected_behavior="Test 1",
            ),
            ValidationRule(
                rule_type=ValidationType.FILE_EXISTS,
                description="Rule 2",
                file_path="test2.md",
                failure_message="Test 2",
                expected_behavior="Test 2",
            ),
        ]

        bundle_config = DocumentBundleConfig(
            bundle_type="test",
            file_patterns=["*.md"],
            bundle_strategy=BundleStrategy.COLLECTION,
        )

        config = ValidationRulesConfig(
            rules=rules,
            document_bundle=bundle_config,
        )

        assert len(config.rules) == 2


class TestFileExistsValidator:
    """Tests for FileExistsValidator."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        # Create some test files
        (tmp_path / "README.md").write_text("# Test Project")
        (tmp_path / "CLAUDE.md").write_text("# Claude Docs")

        # Create nested structure
        skills_dir = tmp_path / ".claude" / "skills" / "test-skill"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Test Skill")

        return tmp_path

    @pytest.fixture
    def sample_bundle(self, temp_project):
        """Create a sample document bundle."""
        return DocumentBundle(
            bundle_id="test-bundle",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=temp_project,
        )

    def test_file_exists_passes(self, sample_bundle):
        """Test that validation passes when file exists."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Check README exists",
            file_path="README.md",
            failure_message="README not found",
            expected_behavior="README should exist",
        )

        validator = FileExistsValidator()
        result = validator.validate(rule, sample_bundle)

        assert result is None  # None means validation passed

    def test_file_exists_fails(self, sample_bundle):
        """Test that validation fails when file doesn't exist."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Check missing file",
            file_path="MISSING.md",
            failure_message="MISSING.md not found",
            expected_behavior="MISSING.md should exist",
        )

        validator = FileExistsValidator()
        result = validator.validate(rule, sample_bundle)

        assert result is not None  # Non-None means validation failed
        assert result.observed_issue == "MISSING.md not found"
        assert result.expected_quality == "MISSING.md should exist"
        assert "MISSING.md" in result.file_paths

    def test_glob_pattern_with_matches_passes(self, sample_bundle):
        """Test that glob pattern validation passes when files match."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Check skill files exist",
            file_path=".claude/skills/*/SKILL.md",
            failure_message="No skill files found",
            expected_behavior="Skill files should exist",
        )

        validator = FileExistsValidator()
        result = validator.validate(rule, sample_bundle)

        assert result is None  # Validation passed

    def test_glob_pattern_no_matches_fails(self, sample_bundle):
        """Test that glob pattern validation fails when no files match."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Check missing pattern",
            file_path=".claude/commands/*.md",
            failure_message="No command files found",
            expected_behavior="Command files should exist",
        )

        validator = FileExistsValidator()
        result = validator.validate(rule, sample_bundle)

        assert result is not None  # Validation failed
        assert result.observed_issue == "No command files found"

    def test_missing_file_path_raises_error(self, sample_bundle):
        """Test that validator raises error when file_path is None."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Missing file path",
            failure_message="Test",
            expected_behavior="Test",
        )

        validator = FileExistsValidator()
        with pytest.raises(ValueError) as exc_info:
            validator.validate(rule, sample_bundle)

        assert "requires rule.file_path" in str(exc_info.value)


class TestValidatorRegistry:
    """Tests for ValidatorRegistry."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        (tmp_path / "EXISTS.md").write_text("# Exists")
        return tmp_path

    @pytest.fixture
    def sample_bundle(self, temp_project):
        """Create a sample document bundle."""
        return DocumentBundle(
            bundle_id="test-bundle",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=temp_project,
        )

    def test_registry_initialization(self):
        """Test that registry initializes with validators."""
        registry = ValidatorRegistry()

        assert ValidationType.FILE_EXISTS in registry._validators
        assert ValidationType.FILE_NOT_EXISTS in registry._validators

    def test_execute_file_exists_rule(self, sample_bundle):
        """Test executing FILE_EXISTS rule through registry."""
        rule = ValidationRule(
            rule_type=ValidationType.FILE_EXISTS,
            description="Check file exists",
            file_path="EXISTS.md",
            failure_message="File not found",
            expected_behavior="File should exist",
        )

        registry = ValidatorRegistry()
        result = registry.execute_rule(rule, sample_bundle)

        assert result is None  # File exists, validation passes

    def test_execute_file_not_exists_rule_inverted(self, sample_bundle):
        """Test that FILE_NOT_EXISTS inverts the result correctly."""
        # File EXISTS.md exists, so FILE_NOT_EXISTS should fail
        rule = ValidationRule(
            rule_type=ValidationType.FILE_NOT_EXISTS,
            description="File should not exist",
            file_path="EXISTS.md",
            failure_message="File should not exist",
            expected_behavior="File should be absent",
        )

        registry = ValidatorRegistry()
        result = registry.execute_rule(rule, sample_bundle)

        assert result is not None  # File exists but shouldn't, validation fails
        assert result.observed_issue == "File should not exist"

    def test_execute_file_not_exists_passes_when_missing(self, sample_bundle):
        """Test that FILE_NOT_EXISTS passes when file is missing."""
        # MISSING.md doesn't exist, so FILE_NOT_EXISTS should pass
        rule = ValidationRule(
            rule_type=ValidationType.FILE_NOT_EXISTS,
            description="File should not exist",
            file_path="MISSING.md",
            failure_message="File should not exist",
            expected_behavior="File should be absent",
        )

        registry = ValidatorRegistry()
        result = registry.execute_rule(rule, sample_bundle)

        assert result is None  # File doesn't exist as desired, validation passes

    def test_unsupported_rule_type_raises_error(self, sample_bundle):
        """Test that unsupported rule types raise ValueError."""
        # Create a rule with REGEX_MATCH which we haven't implemented yet
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Test regex",
            pattern="test",
            failure_message="Test",
            expected_behavior="Test",
        )

        registry = ValidatorRegistry()
        with pytest.raises(ValueError) as exc_info:
            registry.execute_rule(rule, sample_bundle)

        assert "Unsupported validation rule type" in str(exc_info.value)
