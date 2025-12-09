"""Tests for default messages in real validators.

This module tests that all built-in validators properly implement and use
their default failure messages and expected behaviors when no custom messages
are provided in the validation rule.
"""

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import (
    CircularDependenciesValidator,
    DependencyDuplicateValidator,
    FileExistsValidator,
    FileSizeValidator,
    JsonSchemaValidator,
    ListMatchValidator,
    ListRegexMatchValidator,
    MarkdownLinkValidator,
    MaxDependencyDepthValidator,
    RegexMatchValidator,
    TokenCountValidator,
    YamlFrontmatterValidator,
    YamlSchemaValidator,
)


class TestFileExistsValidatorDefaults:
    """Test FileExistsValidator default messages."""

    def test_uses_default_when_file_not_exists(self, tmp_path):
        """Test that FileExistsValidator uses default message when file doesn't exist."""
        validator = FileExistsValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check file exists",
            params={"file_path": "missing.txt"},
            # No failure_message or expected_behavior - should use defaults
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert "does not exist" in result.observed_issue.lower()
        assert "should exist" in result.expected_quality.lower()

    def test_uses_custom_messages_when_provided(self, tmp_path):
        """Test that custom messages override defaults."""
        validator = FileExistsValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check file exists",
            params={"file_path": "missing.txt"},
            failure_message="CUSTOM: File {file_path} is missing!",
            expected_behavior="CUSTOM: File must be present",
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert result.observed_issue == "CUSTOM: File missing.txt is missing!"
        assert result.expected_quality == "CUSTOM: File must be present"


class TestFileSizeValidatorDefaults:
    """Test FileSizeValidator default messages."""

    def test_file_size_validator_has_default_messages(self):
        """Test that FileSizeValidator has default message properties."""
        validator = FileSizeValidator()

        # Verify default messages exist and are meaningful
        assert hasattr(validator, "default_failure_message")
        assert hasattr(validator, "default_expected_behavior")
        assert validator.default_failure_message != ""
        assert validator.default_expected_behavior != ""
        assert (
            "exceed" in validator.default_failure_message.lower()
            or "size" in validator.default_failure_message.lower()
        )
        assert (
            "exceed" in validator.default_expected_behavior.lower()
            or "size" in validator.default_expected_behavior.lower()
        )


class TestRegexMatchValidatorDefaults:
    """Test RegexMatchValidator default messages."""

    def test_uses_default_when_pattern_not_found(self, tmp_path):
        """Test RegexMatchValidator uses default when pattern not found."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world")

        validator = RegexMatchValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    file_path=str(test_file),
                    relative_path="test.txt",
                    content="Hello world",
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:regex_match",
            description="Check pattern",
            params={"pattern": r"MISSING_PATTERN"},
            # No custom messages
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert "pattern" in result.observed_issue.lower()
        assert "should match" in result.expected_quality.lower()


class TestListMatchValidatorDefaults:
    """Test ListMatchValidator default messages."""

    def test_uses_default_when_items_missing(self, tmp_path):
        """Test ListMatchValidator uses default when items missing."""
        validator = ListMatchValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:list_match",
            description="Check list items",
            params={
                "items": {"type": "string_list", "value": ["a", "b", "c"]},
                "target": {"type": "string_list", "value": ["a", "b"]},  # Missing 'c'
                "match_mode": "all_in",
            },
            # No custom messages
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert "validation failed" in result.observed_issue.lower()
        assert "should match" in result.expected_quality.lower()


class TestMarkdownLinkValidatorDefaults:
    """Test MarkdownLinkValidator default messages."""

    def test_uses_default_when_links_broken(self, tmp_path):
        """Test MarkdownLinkValidator uses default when links broken."""
        md_file = tmp_path / "test.md"
        md_file.write_text("[Link](missing.md)")

        validator = MarkdownLinkValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    file_path=str(md_file),
                    relative_path="test.md",
                    content="[Link](missing.md)",
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check markdown links",
            # No custom messages
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert "broken" in result.observed_issue.lower() or "link" in result.observed_issue.lower()


class TestJsonSchemaValidatorDefaults:
    """Test JsonSchemaValidator default messages."""

    def test_uses_default_when_schema_validation_fails(self, tmp_path):
        """Test JsonSchemaValidator uses default when validation fails."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"name": "test"}')

        validator = JsonSchemaValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    file_path=str(json_file),
                    relative_path="test.json",
                    content='{"name": "test"}',
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate JSON schema",
            params={
                "file_path": "test.json",
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
                    "required": ["name", "age"],  # Missing 'age'
                },
            },
            # No custom messages
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert (
            "schema" in result.observed_issue.lower()
            or "validation" in result.observed_issue.lower()
        )


class TestYamlSchemaValidatorDefaults:
    """Test YamlSchemaValidator default messages."""

    def test_uses_default_when_schema_validation_fails(self, tmp_path):
        """Test YamlSchemaValidator uses default when validation fails."""
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("name: test\n")

        validator = YamlSchemaValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    file_path=str(yaml_file),
                    relative_path="test.yaml",
                    content="name: test\n",
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate YAML schema",
            params={
                "file_path": "test.yaml",
                "schema": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}, "age": {"type": "number"}},
                    "required": ["name", "age"],  # Missing 'age'
                },
            },
            # No custom messages
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert (
            "schema" in result.observed_issue.lower()
            or "validation" in result.observed_issue.lower()
        )


class TestYamlFrontmatterValidatorDefaults:
    """Test YamlFrontmatterValidator default messages."""

    def test_uses_default_when_frontmatter_invalid(self, tmp_path):
        """Test YamlFrontmatterValidator uses default when frontmatter invalid."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            """---
title: Test
---
Content
"""
        )

        validator = YamlFrontmatterValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    file_path=str(md_file),
                    relative_path="test.md",
                    content="---\ntitle: Test\n---\nContent\n",
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter",
            params={
                "schema": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "author": {"type": "string"}},
                    "required": ["title", "author"],  # Missing 'author'
                }
            },
            # No custom messages
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert (
            "frontmatter" in result.observed_issue.lower()
            or "schema" in result.observed_issue.lower()
        )


class TestTokenCountValidatorDefaults:
    """Test TokenCountValidator default messages."""

    def test_token_count_default_properties_exist(self):
        """Test that TokenCountValidator has default message properties."""
        validator = TokenCountValidator()

        # Verify default messages exist
        assert hasattr(validator, "default_failure_message")
        assert hasattr(validator, "default_expected_behavior")
        assert "token" in validator.default_failure_message.lower()
        assert (
            "token" in validator.default_expected_behavior.lower()
            or "exceed" in validator.default_expected_behavior.lower()
        )


class TestDependencyValidatorDefaults:
    """Test dependency validator default messages."""

    def test_circular_dependencies_default_properties(self):
        """Test CircularDependenciesValidator has default message properties."""
        validator = CircularDependenciesValidator()

        assert hasattr(validator, "default_failure_message")
        assert hasattr(validator, "default_expected_behavior")
        assert (
            "circular" in validator.default_failure_message.lower()
            or "{circular_path}" in validator.default_failure_message
        )
        assert (
            "circular" in validator.default_expected_behavior.lower()
            or "no" in validator.default_expected_behavior.lower()
        )

    def test_dependency_duplicate_default_properties(self):
        """Test DependencyDuplicateValidator has default message properties."""
        validator = DependencyDuplicateValidator()

        assert hasattr(validator, "default_failure_message")
        assert hasattr(validator, "default_expected_behavior")
        assert "duplicate" in validator.default_failure_message.lower()
        assert (
            "duplicate" in validator.default_expected_behavior.lower()
            or "no" in validator.default_expected_behavior.lower()
        )

    def test_max_dependency_depth_default_properties(self):
        """Test MaxDependencyDepthValidator has default message properties."""
        validator = MaxDependencyDepthValidator()

        assert hasattr(validator, "default_failure_message")
        assert hasattr(validator, "default_expected_behavior")
        assert (
            "depth" in validator.default_failure_message.lower()
            or "{actual_depth}" in validator.default_failure_message
        )
        assert (
            "depth" in validator.default_expected_behavior.lower()
            or "maximum" in validator.default_expected_behavior.lower()
        )


class TestListValidatorDefaults:
    """Test list validator default messages."""

    def test_list_match_default_properties(self):
        """Test ListMatchValidator has default message properties."""
        validator = ListMatchValidator()

        assert hasattr(validator, "default_failure_message")
        assert hasattr(validator, "default_expected_behavior")
        assert validator.default_failure_message != ""
        assert validator.default_expected_behavior != ""

    def test_list_regex_match_validator_exists(self):
        """Test ListRegexMatchValidator exists and has computation type."""
        validator = ListRegexMatchValidator()
        assert validator.computation_type == "programmatic"
