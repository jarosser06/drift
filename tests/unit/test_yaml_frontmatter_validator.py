"""Tests for YamlFrontmatterValidator."""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle
from drift.validation.validators.core.format_validators import YamlFrontmatterValidator


class TestYamlFrontmatterValidator:
    """Tests for YamlFrontmatterValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return YamlFrontmatterValidator(loader=None)

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create test bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

    def test_valid_frontmatter_with_required_fields(self, validator, bundle, tmp_path):
        """Test that validation passes with valid frontmatter and required fields."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
description: A test skill for validation
tags: [testing, validation]
---

# Test Skill

This is the content of the skill.
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate skill frontmatter",
            file_path="SKILL.md",
            params={"required_fields": ["title", "description"]},
            failure_message="Missing required frontmatter fields",
            expected_behavior="Should have title and description",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_missing_required_fields(self, validator, bundle, tmp_path):
        """Test that validation fails when required fields are missing."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
---

# Test Skill
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate skill frontmatter",
            file_path="SKILL.md",
            params={"required_fields": ["title", "description", "tags"]},
            failure_message="Missing required frontmatter fields",
            expected_behavior="Should have title, description, and tags",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Missing required frontmatter fields" in result.observed_issue
        assert "description" in result.observed_issue
        assert "tags" in result.observed_issue

    def test_no_frontmatter(self, validator, bundle, tmp_path):
        """Test that validation fails when file has no frontmatter."""
        test_file = tmp_path / "README.md"
        content = """# README

This file has no frontmatter.
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter",
            file_path="README.md",
            params={"required_fields": ["title"]},
            failure_message="No frontmatter found",
            expected_behavior="Should have frontmatter",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "No YAML frontmatter found" in result.observed_issue

    def test_unclosed_frontmatter(self, validator, bundle, tmp_path):
        """Test that validation fails when frontmatter is not properly closed."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
description: A test skill

# Missing closing ---
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter",
            file_path="SKILL.md",
            params={"required_fields": ["title"]},
            failure_message="Invalid frontmatter",
            expected_behavior="Should have valid frontmatter",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "not properly closed" in result.observed_issue

    def test_invalid_yaml_in_frontmatter(self, validator, bundle, tmp_path):
        """Test that validation fails when frontmatter has invalid YAML."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
description: [unclosed array
---

# Content
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter",
            file_path="SKILL.md",
            params={"required_fields": ["title"]},
            failure_message="Invalid YAML in frontmatter",
            expected_behavior="Should have valid YAML",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Invalid YAML in frontmatter" in result.observed_issue

    def test_empty_frontmatter(self, validator, bundle, tmp_path):
        """Test that validation fails when frontmatter is empty."""
        test_file = tmp_path / "SKILL.md"
        content = """---
---

# Content
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter",
            file_path="SKILL.md",
            params={"required_fields": ["title"]},
            failure_message="Empty frontmatter",
            expected_behavior="Should have non-empty frontmatter",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "YAML frontmatter is empty" in result.observed_issue

    def test_frontmatter_with_schema_validation(self, validator, bundle, tmp_path):
        """Test frontmatter validation with JSON schema."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
description: A test skill
version: 1.0.0
---

# Test Skill
"""
        test_file.write_text(content)

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            },
            "required": ["title", "description", "version"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter schema",
            file_path="SKILL.md",
            params={"required_fields": ["title", "description"], "schema": schema},
            failure_message="Frontmatter doesn't match schema",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_frontmatter_schema_validation_failure(self, validator, bundle, tmp_path):
        """Test that schema validation fails for invalid frontmatter."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
description: A test skill
version: invalid-version
---

# Test Skill
"""
        test_file.write_text(content)

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
            },
            "required": ["title", "description", "version"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter schema",
            file_path="SKILL.md",
            params={"schema": schema},
            failure_message="Frontmatter doesn't match schema",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Frontmatter schema validation failed" in result.observed_issue

    def test_file_not_found(self, validator, bundle):
        """Test error when file doesn't exist."""
        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Test rule",
            file_path="nonexistent.md",
            params={"required_fields": ["title"]},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "does not exist" in result.observed_issue

    def test_missing_file_path(self, validator, bundle):
        """Test that validation passes when file_path is missing (bundle mode with empty files)."""
        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Test rule",
            params={"required_fields": ["title"]},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        # With no file_path, validator operates in bundle mode
        # Empty bundle.files means no files to validate, so should pass
        result = validator.validate(rule, bundle)
        assert result is None  # No failures for empty bundle

    def test_validation_without_required_fields(self, validator, bundle, tmp_path):
        """Test that validation passes when no required fields specified."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
---

# Test Skill
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter exists",
            file_path="SKILL.md",
            failure_message="No frontmatter",
            expected_behavior="Should have frontmatter",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_missing_yaml_package(self, validator, bundle, tmp_path, monkeypatch):
        """Test error when pyyaml package is not installed."""
        import sys

        monkeypatch.setitem(sys.modules, "yaml", None)

        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test
---

# Content
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Test rule",
            file_path="SKILL.md",
            params={"required_fields": ["title"]},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "requires 'pyyaml' package" in result.observed_issue

    def test_complex_frontmatter_structure(self, validator, bundle, tmp_path):
        """Test validation with complex nested frontmatter."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Advanced Skill
description: Complex skill with nested data
metadata:
  author: Test Author
  created: 2025-01-01
  tags:
    - advanced
    - testing
dependencies:
  - skill-a
  - skill-b
---

# Advanced Skill
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate complex frontmatter",
            file_path="SKILL.md",
            params={"required_fields": ["title", "description", "metadata", "dependencies"]},
            failure_message="Missing required fields",
            expected_behavior="Should have all nested fields",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_computation_type(self, validator):
        """Test that validator reports correct computation type."""
        assert validator.computation_type == "programmatic"

    def test_file_read_generic_exception(self, validator, bundle, tmp_path, monkeypatch):
        """Test generic exception during file reading."""
        test_file = tmp_path / "SKILL.md"
        test_file.write_text("---\ntitle: Test\n---\n\n# Content")

        # Mock open to raise exception
        import builtins

        original_open = builtins.open

        def mock_open(path, *args, **kwargs):
            if "SKILL.md" in str(path):
                file_obj = original_open(path, *args, **kwargs)

                def failing_read(*args, **kwargs):
                    raise Exception("Read error")

                file_obj.read = failing_read
                return file_obj
            return original_open(path, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", mock_open)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Test rule",
            file_path="SKILL.md",
            params={"required_fields": ["title"]},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Failed to read file" in result.observed_issue

    def test_missing_jsonschema_for_schema_validation(
        self, validator, bundle, tmp_path, monkeypatch
    ):
        """Test missing jsonschema package during schema validation."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test
version: 1.0.0
---

# Content
"""
        test_file.write_text(content)

        # Mock import to fail for jsonschema
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "jsonschema":
                raise ImportError("No module named 'jsonschema'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "version": {"type": "string"},
            },
            "required": ["title", "version"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Test rule",
            file_path="SKILL.md",
            params={"schema": schema},
            failure_message="Failure",
            expected_behavior="Expected",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "requires 'jsonschema' package" in result.observed_issue

    def test_validation_with_complex_schema_coverage(self, validator, bundle, tmp_path):
        """Test validation with complex schema for code coverage."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
description: A comprehensive test skill
version: 1.0.0
tags:
  - testing
  - validation
---

# Test Skill
"""
        test_file.write_text(content)

        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string", "minLength": 1},
                "description": {"type": "string", "minLength": 10},
                "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "description"],
        }

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter",
            file_path="SKILL.md",
            params={"schema": schema},
            failure_message="Invalid frontmatter",
            expected_behavior="Should validate against schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Should pass

    def test_validation_with_forbidden_fields(self, validator, bundle, tmp_path):
        """Test validation with forbidden fields."""
        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test
skills: [one, two]
description: A test file
---
Content
"""
        test_file.write_text(content)

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Test rule",
            file_path="SKILL.md",
            params={
                "forbidden_fields": ["skills", "other_forbidden"],
                "required_fields": ["title"],
            },
            failure_message="Forbidden fields found",
            expected_behavior="Should fail",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Frontmatter contains forbidden fields: skills" in result.observed_issue

        test_file = tmp_path / "SKILL.md"
        content = """---
title: Test Skill
description: A test skill
---

# Test Skill
"""
        test_file.write_text(content)

        # Schema with invalid type for "type" field (should be string or array, not number)
        schema = {
            "type": 123,  # Invalid - type should be string not number
            "properties": {"title": {"type": "string"}},
        }

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Validate frontmatter",
            file_path="SKILL.md",
            params={"schema": schema},
            failure_message="Invalid schema",
            expected_behavior="Should catch schema error",
        )

        result = validator.validate(rule, bundle)
        # Should catch SchemaError and return failure
        assert result is not None
        assert "Invalid schema" in result.observed_issue
