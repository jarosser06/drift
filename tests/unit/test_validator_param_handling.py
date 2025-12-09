"""Tests for validator parameter handling.

This test suite ensures validators consistently use rule.params dict,
catching regressions if implementation changes.

REQUIRED PATTERN:
- Core rule fields: type, description, failure_message, expected_behavior
- Validator-specific parameters: EVERYTHING ELSE under params:

Example:
    rule = ValidationRule(
        rule_type="core:regex_match",
        description="Check pattern",
        params={
            "pattern": r"## Prerequisites",
            "flags": re.MULTILINE,
            "file_path": "README.md"
        }
    )
"""

import re

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.block_validators import BlockLineCountValidator
from drift.validation.validators.core.file_validators import FileExistsValidator, FileSizeValidator
from drift.validation.validators.core.format_validators import (
    JsonSchemaValidator,
    YamlFrontmatterValidator,
    YamlSchemaValidator,
)
from drift.validation.validators.core.markdown_validators import MarkdownLinkValidator
from drift.validation.validators.core.regex_validators import RegexMatchValidator


class TestRegexMatchValidatorParams:
    """Tests for RegexMatchValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return RegexMatchValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_file(self, tmp_path):
        """Create bundle with a test file."""
        test_file = tmp_path / "test.md"
        test_file.write_text("# Header\n## Prerequisites\nContent")

        return DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content="# Header\n## Prerequisites\nContent",
                    file_path=str(test_file),
                )
            ],
        )

    def test_missing_pattern_raises_error(self, validator, bundle_with_file):
        """Test that validator raises clear error when pattern is missing."""
        rule = ValidationRule(
            rule_type="core:regex_match",
            description="Check pattern",
            params={"file_path": "test.md"},  # Has params, but missing pattern
        )

        with pytest.raises(ValueError, match="requires.*pattern"):
            validator.validate(rule, bundle_with_file)

    def test_pattern_from_params(self, validator, bundle_with_file):
        """Test that validator reads pattern from params."""
        rule = ValidationRule(
            rule_type="core:regex_match",
            description="Check for Prerequisites",
            params={
                "pattern": r"## Prerequisites",
                "file_path": "test.md",
            },
        )

        result = validator.validate(rule, bundle_with_file)
        assert result is None

    def test_flags_from_params(self, validator, tmp_path):
        """Test that validator reads flags from params."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("First line\nSecond line")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.txt",
                    content="First line\nSecond line",
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:regex_match",
            description="Match line start",
            params={
                "pattern": r"^Second",
                "flags": re.MULTILINE,
                "file_path": "test.txt",
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_invalid_regex_pattern_caught_by_model(self, validator, bundle_with_file):
        """Test that ValidationRule model catches invalid regex patterns."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            ValidationRule(
                rule_type="core:regex_match",
                description="Invalid regex",
                pattern=r"[invalid(regex",
            )


class TestFileExistsValidatorParams:
    """Tests for FileExistsValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return FileExistsValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create basic bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

    def test_missing_file_path_param_raises_error(self, validator, bundle):
        """Test that validator raises clear error when file_path is missing."""
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check file exists",
            params={},  # Empty params, no file_path
        )

        with pytest.raises(ValueError, match="requires params"):
            validator.validate(rule, bundle)

    def test_file_path_from_params(self, validator, tmp_path):
        """Test that validator reads from params.file_path."""
        test_file = tmp_path / "test.md"
        test_file.write_text("content")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check file exists",
            params={"file_path": "test.md"},
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_glob_pattern_in_file_path(self, validator, tmp_path):
        """Test file_path with glob patterns."""
        skills_dir = tmp_path / ".claude" / "skills" / "testing"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Testing Skill")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check skill files exist",
            params={"file_path": ".claude/skills/*/SKILL.md"},
        )

        result = validator.validate(rule, bundle)
        assert result is None


class TestFileSizeValidatorParams:
    """Tests for FileSizeValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return FileSizeValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create basic bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

    def test_missing_file_path_param_raises_error(self, validator, bundle):
        """Test that validator raises clear error when file_path is missing."""
        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check file size",
            params={},  # Empty params, no file_path
        )

        with pytest.raises(ValueError, match="requires params"):
            validator.validate(rule, bundle)

    def test_max_count_from_params(self, validator, tmp_path):
        """Test that validator reads max_count from params."""
        test_file = tmp_path / "test.md"
        content = "\n".join([f"Line {i}" for i in range(50)])
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check line count",
            params={"file_path": "test.md", "max_count": 100},
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_min_count_from_params(self, validator, tmp_path):
        """Test that validator reads min_count from params."""
        test_file = tmp_path / "test.md"
        content = "\n".join([f"Line {i}" for i in range(5)])
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check minimum lines",
            params={"file_path": "test.md", "min_count": 10},
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "below min 10" in result.observed_issue

    def test_max_size_from_params(self, validator, tmp_path):
        """Test that validator reads max_size from params."""
        test_file = tmp_path / "test.txt"
        content = "a" * 500
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.txt",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check byte size",
            params={"file_path": "test.txt", "max_size": 1000},
        )

        result = validator.validate(rule, bundle)
        assert result is None


class TestBlockLineCountValidatorParams:
    """Tests for BlockLineCountValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return BlockLineCountValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_blocks(self, tmp_path):
        """Create bundle with code blocks."""
        content = """```python
print("hello")
```

```
x = 1
y = 2
```"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        return DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

    def test_missing_pattern_start_raises_error(self, validator, tmp_path):
        """Test that validator raises error when params.pattern_start is missing."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                # Missing pattern_start!
                "pattern_end": "^```",
                "min_lines": 1,
            },
        )

        with pytest.raises(ValueError, match="requires params.pattern_start"):
            validator.validate(rule, bundle)

    def test_missing_pattern_end_raises_error(self, validator, tmp_path):
        """Test that validator raises error when params.pattern_end is missing."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                # Missing pattern_end!
                "min_lines": 1,
            },
        )

        with pytest.raises(ValueError, match="requires params.pattern_end"):
            validator.validate(rule, bundle)

    def test_missing_threshold_raises_error(self, validator, tmp_path):
        """Test that validator raises error when no threshold specified."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
            },
        )

        with pytest.raises(
            ValueError, match="requires at least one of: params.min_lines, params.max_lines"
        ):
            validator.validate(rule, bundle)

    def test_pattern_start_from_params(self, validator, bundle_with_blocks):
        """Test that validator reads pattern_start from params."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle_with_blocks)
        assert result is None

    def test_min_lines_from_params(self, validator, bundle_with_blocks):
        """Test that validator reads min_lines from params."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 5,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle_with_blocks)
        assert result is not None
        assert "violation" in result.observed_issue.lower()

    def test_max_lines_from_params(self, validator, bundle_with_blocks):
        """Test that validator reads max_lines from params."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "max_lines": 10,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle_with_blocks)
        assert result is None

    def test_exact_lines_from_params(self, validator, tmp_path):
        """Test that validator reads exact_lines from params."""
        content = """```
line1
line2
```"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "exact_lines": 2,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_files_from_params(self, validator, bundle_with_blocks):
        """Test that validator reads files from params."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle_with_blocks)
        assert result is None


class TestMarkdownLinkValidatorParams:
    """Tests for MarkdownLinkValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return MarkdownLinkValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_links(self, tmp_path):
        """Create bundle with markdown file containing links."""
        content = """# Test
[Local](./local.md)
[External](https://example.com)
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        return DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

    def test_check_local_files_from_params(self, validator, bundle_with_links):
        """Test that validator reads check_local_files from params."""
        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            params={
                "check_local_files": True,
                "check_external_urls": False,
            },
        )

        result = validator.validate(rule, bundle_with_links)
        assert result is not None
        assert "local.md" in result.observed_issue

    def test_check_external_urls_from_params(self, validator, tmp_path):
        """Test that validator reads check_external_urls from params."""
        local_file = tmp_path / "local.md"
        local_file.write_text("content")

        content = """# Test
[Local](./local.md)
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            params={
                "check_local_files": True,
                "check_external_urls": False,
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_skip_example_domains_from_params(self, validator, tmp_path):
        """Test that validator reads skip_example_domains from params."""
        content = """# Test
[Example](https://example.com)
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            params={
                "check_local_files": False,
                "check_external_urls": True,
                "skip_example_domains": True,
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None


class TestYamlFrontmatterValidatorParams:
    """Tests for YamlFrontmatterValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return YamlFrontmatterValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_frontmatter(self, tmp_path):
        """Create bundle with file containing YAML frontmatter."""
        content = """---
title: Test
author: John
---

# Content
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        return DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

    def test_required_fields_from_params(self, validator, bundle_with_frontmatter):
        """Test that validator reads required_fields from params."""
        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Check frontmatter",
            params={
                "required_fields": ["title", "author"],
            },
        )

        result = validator.validate(rule, bundle_with_frontmatter)
        assert result is None

    def test_schema_from_params(self, validator, tmp_path):
        """Test that validator reads schema from params."""
        content = """---
title: Test
count: 42
---

# Content
"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:yaml_frontmatter",
            description="Check frontmatter schema",
            params={
                "schema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "count": {"type": "number"},
                    },
                    "required": ["title", "count"],
                }
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None


class TestJsonSchemaValidatorParams:
    """Tests for JsonSchemaValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return JsonSchemaValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    def test_missing_schema_returns_error(self, validator, tmp_path):
        """Test that validator returns error when schema is missing from params."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"key": "value"}')

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="config",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate JSON",
            params={"file_path": "test.json"},  # Has file_path but no schema
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "schema" in result.observed_issue.lower()

    def test_schema_from_params(self, validator, tmp_path):
        """Test that validator reads schema from params."""
        test_file = tmp_path / "test.json"
        test_file.write_text('{"name": "test", "count": 42}')

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="config",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:json_schema",
            description="Validate JSON",
            params={
                "file_path": "test.json",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "count": {"type": "number"},
                    },
                    "required": ["name", "count"],
                },
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None


class TestYamlSchemaValidatorParams:
    """Tests for YamlSchemaValidator parameter handling."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return YamlSchemaValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    def test_missing_schema_returns_error(self, validator, tmp_path):
        """Test that validator returns error when schema is missing from params."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("key: value\n")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="config",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate YAML",
            params={"file_path": "test.yaml"},  # Has file_path but no schema
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "schema" in result.observed_issue.lower()

    def test_schema_from_params(self, validator, tmp_path):
        """Test that validator reads schema from params."""
        test_file = tmp_path / "test.yaml"
        test_file.write_text("name: test\ncount: 42\n")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="config",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:yaml_schema",
            description="Validate YAML",
            params={
                "file_path": "test.yaml",
                "schema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "count": {"type": "number"},
                    },
                    "required": ["name", "count"],
                },
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None
