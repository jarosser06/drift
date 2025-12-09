"""Tests for BlockLineCountValidator."""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.block_validators import BlockLineCountValidator


class TestBlockLineCountValidator:
    """Tests for BlockLineCountValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return BlockLineCountValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_code_blocks(self, tmp_path):
        """Create bundle with markdown file containing code blocks."""
        content = """# README

Some intro text.

```python
print("Hello")
```

More text.

```python
def foo():
    pass
```

Even more text.

```
x = 1
y = 2
z = 3
```

End.
"""
        test_file = tmp_path / "README.md"
        test_file.write_text(content)

        return DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="README.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

    def test_validation_type(self, validator):
        """Test validation_type property."""
        assert validator.validation_type == "core:block_line_count"

    def test_computation_type(self, validator):
        """Test computation_type property."""
        assert validator.computation_type == "programmatic"

    def test_min_lines_pass(self, validator, bundle_with_code_blocks):
        """Test that validation passes when all blocks meet minimum line count."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Code blocks should have at least 1 line",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                "files": ["README.md"],
            },
        )

        result = validator.validate(rule, bundle_with_code_blocks)
        assert result is None

    def test_min_lines_fail(self, validator, bundle_with_code_blocks):
        """Test that validation fails when blocks don't meet minimum."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Code blocks should have at least 3 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 3,
                "files": ["README.md"],
            },
        )

        result = validator.validate(rule, bundle_with_code_blocks)
        assert result is not None
        assert "README.md" in result.file_paths
        assert "Found 3 total blocks, 2 in violation" in result.observed_issue
        assert "expected at least 3" in result.observed_issue

    def test_max_lines_pass(self, validator, bundle_with_code_blocks):
        """Test that validation passes when all blocks are under maximum."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Code blocks should not exceed 10 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "max_lines": 10,
                "files": ["README.md"],
            },
        )

        result = validator.validate(rule, bundle_with_code_blocks)
        assert result is None

    def test_max_lines_fail(self, validator, bundle_with_code_blocks):
        """Test that validation fails when blocks exceed maximum."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Code blocks should not exceed 2 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "max_lines": 2,
                "files": ["README.md"],
            },
        )

        result = validator.validate(rule, bundle_with_code_blocks)
        assert result is not None
        assert "README.md" in result.file_paths
        assert "Found 3 total blocks, 1 in violation" in result.observed_issue
        assert "expected at most 2" in result.observed_issue

    def test_exact_lines_pass(self, validator, tmp_path):
        """Test that validation passes when blocks have exact line count."""
        content = """# Test

```
line1
line2
```

```
line1
line2
```
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
            rule_type="core:block_line_count",
            description="Code blocks should have exactly 2 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "exact_lines": 2,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_exact_lines_fail(self, validator, bundle_with_code_blocks):
        """Test that validation fails when blocks don't have exact line count."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Code blocks should have exactly 2 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "exact_lines": 2,
                "files": ["README.md"],
            },
        )

        result = validator.validate(rule, bundle_with_code_blocks)
        assert result is not None
        assert "README.md" in result.file_paths
        assert "Found 3 total blocks, 2 in violation" in result.observed_issue
        assert "expected exactly 2" in result.observed_issue

    def test_empty_blocks(self, validator, tmp_path):
        """Test handling of empty blocks (0 lines between delimiters)."""
        content = """# Test

```
```

```
content
```
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
            rule_type="core:block_line_count",
            description="Code blocks should have at least 1 line",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Found 2 total blocks, 1 in violation" in result.observed_issue
        assert "0 lines (expected at least 1)" in result.observed_issue

    def test_unpaired_delimiters_too_many_opens(self, validator, tmp_path):
        """Test error handling for unpaired delimiters (more opens than closes)."""
        content = """# Test

```
content
```

```
orphaned
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
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Unpaired delimiters" in result.observed_issue
        assert "test.md" in result.file_paths

    def test_unpaired_delimiters_too_many_closes(self, validator, tmp_path):
        """Test error handling for unpaired delimiters (more closes than opens)."""
        content = """# Test

```
content
```

```
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
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Unpaired delimiters" in result.observed_issue

    def test_multiple_files(self, validator, tmp_path):
        """Test validation across multiple files."""
        content1 = """```
line1
line2
```"""
        content2 = """```
x
```"""

        file1 = tmp_path / "file1.md"
        file1.write_text(content1)
        file2 = tmp_path / "file2.md"
        file2.write_text(content2)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="file1.md",
                    content=content1,
                    file_path=str(file1),
                ),
                DocumentFile(
                    relative_path="file2.md",
                    content=content2,
                    file_path=str(file2),
                ),
            ],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Code blocks should have at least 2 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 2,
                "files": ["*.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Found 2 total blocks, 1 in violation" in result.observed_issue
        assert "file2.md" in result.observed_issue

    def test_yaml_blocks(self, validator, tmp_path):
        """Test validation of YAML code blocks."""
        content = """# Config

```yaml
key: value
another: value
third: value
```

```yaml
short: value
```
"""
        test_file = tmp_path / "config.md"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="config.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="YAML blocks should not exceed 2 lines",
            params={
                "pattern_start": "^```yaml",
                "pattern_end": "^```",
                "max_lines": 2,
                "files": ["config.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Found 2 total blocks, 1 in violation" in result.observed_issue
        assert "expected at most 2" in result.observed_issue

    def test_no_files_match_pattern(self, validator, tmp_path):
        """Test that validation passes when no files match the pattern."""
        content = "No code blocks here"
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
                "min_lines": 1,
                "files": ["nonexistent.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_no_blocks_in_file(self, validator, tmp_path):
        """Test that validation passes when file has no matching blocks."""
        content = "Just plain text, no code blocks"
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
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_missing_pattern_start(self, validator, tmp_path):
        """Test that validator raises error when pattern_start is missing."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Missing pattern_start",
            params={
                "pattern_end": "^```",
                "min_lines": 1,
            },
        )

        with pytest.raises(ValueError, match="requires params.pattern_start"):
            validator.validate(rule, bundle)

    def test_missing_pattern_end(self, validator, tmp_path):
        """Test that validator raises error when pattern_end is missing."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Missing pattern_end",
            params={
                "pattern_start": "^```",
                "min_lines": 1,
            },
        )

        with pytest.raises(ValueError, match="requires params.pattern_end"):
            validator.validate(rule, bundle)

    def test_missing_threshold(self, validator, tmp_path):
        """Test that validator raises error when no threshold is specified."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="No threshold",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
            },
        )

        with pytest.raises(
            ValueError, match="requires at least one of: params.min_lines, params.max_lines"
        ):
            validator.validate(rule, bundle)

    def test_invalid_regex_pattern(self, validator, tmp_path):
        """Test that validator raises error for invalid regex patterns."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Invalid regex",
            params={
                "pattern_start": "[invalid(regex",
                "pattern_end": "^```",
                "min_lines": 1,
            },
        )

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            validator.validate(rule, bundle)

    def test_file_read_error(self, validator, tmp_path):
        """Test handling of file read errors."""
        test_file = tmp_path / "test.md"
        test_file.write_text("content")
        test_file.chmod(0o000)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content="",
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
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        try:
            result = validator.validate(rule, bundle)
            assert result is not None
            assert "Failed to read file" in result.observed_issue
        finally:
            test_file.chmod(0o644)

    def test_combined_min_max_thresholds(self, validator, tmp_path):
        """Test validation with both min and max thresholds."""
        content = """```
line1
```

```
line1
line2
line3
```

```
line1
line2
```
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
            rule_type="core:block_line_count",
            description="Code blocks should have 2-3 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 2,
                "max_lines": 3,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Found 3 total blocks, 1 in violation" in result.observed_issue
        assert "1 lines (expected at least 2)" in result.observed_issue

    def test_line_range_in_violation_message(self, validator, tmp_path):
        """Test that violation messages include correct line ranges."""
        content = """Line 1
Line 2
```
Line 4
```
Line 6
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
            rule_type="core:block_line_count",
            description="Code blocks should have at least 2 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 2,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "test.md:3-5" in result.observed_issue
        assert "1 lines" in result.observed_issue

    def test_failure_details_populated(self, validator, bundle_with_code_blocks):
        """Test that failure_details is properly populated for failures."""
        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Code blocks should have at least 3 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 3,
                "files": ["README.md"],
            },
        )

        result = validator.validate(rule, bundle_with_code_blocks)
        assert result is not None
        assert result.failure_details is not None
        assert "total_blocks" in result.failure_details
        assert result.failure_details["total_blocks"] == 3
        assert "violations" in result.failure_details
        assert len(result.failure_details["violations"]) == 2
        assert "threshold" in result.failure_details

    def test_no_file_patterns_validates_all_bundle_files(self, validator, tmp_path):
        """Test that when no file patterns are specified, all bundle files are validated."""
        content = """```
line1
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
            description="Code blocks should have at least 2 lines",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 2,
                # No files parameter - should validate all files in bundle
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "test.md" in result.observed_issue

    def test_different_start_end_delimiters(self, validator, tmp_path):
        """Test validation with different start and end delimiters."""
        content = """# Test

<block>
line1
line2
</block>

<block>
x
</block>
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
            rule_type="core:block_line_count",
            description="Blocks should have at least 2 lines",
            params={
                "pattern_start": "^<block>",
                "pattern_end": "^</block>",
                "min_lines": 2,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Found 2 total blocks, 1 in violation" in result.observed_issue

    def test_different_delimiters_end_before_start(self, validator, tmp_path):
        """Test error handling when end delimiter comes before start."""
        content = """</block>
<block>
content
</block>
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
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^<block>",
                "pattern_end": "^</block>",
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Unpaired delimiters" in result.observed_issue

    def test_file_not_exist_in_pattern_list(self, validator, tmp_path):
        """Test that non-existent files in glob patterns are skipped gracefully."""
        content = """```
content
```"""
        test_file = tmp_path / "exists.md"
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="exists.md",
                    content=content,
                    file_path=str(test_file),
                ),
                DocumentFile(
                    relative_path="missing.md",
                    content="",
                    file_path=str(tmp_path / "missing.md"),
                ),
            ],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                "files": ["*.md"],
            },
        )

        # Should validate only the existing file
        result = validator.validate(rule, bundle)
        assert result is None  # exists.md has 1 line which meets min_lines

    def test_file_exists_but_is_directory(self, validator, tmp_path):
        """Test that directories in bundle files are skipped gracefully."""
        content = """```
content
```"""
        test_file = tmp_path / "test.md"
        test_file.write_text(content)

        # Create a directory with same name as potential file
        dir_path = tmp_path / "subdir"
        dir_path.mkdir()

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
                ),
                DocumentFile(
                    relative_path="subdir",
                    content="",
                    file_path=str(dir_path),
                ),
            ],
        )

        rule = ValidationRule(
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^```",
                "pattern_end": "^```",
                "min_lines": 1,
                # No files parameter - will use all files in bundle including the directory
            },
        )

        # Should validate only the file, skip the directory
        result = validator.validate(rule, bundle)
        assert result is None

    def test_different_delimiters_interleaved_wrong_order(self, validator, tmp_path):
        """Test when delimiters are interleaved in wrong order (end before corresponding start)."""
        # Create content where we have equal numbers but ends come before starts
        # Line 0: </end>     -> end_indices = [0]
        # Line 1: <start>    -> start_indices = [1]
        # When zipped: (1, 0) means start at line 1, end at line 0
        # This triggers end_idx <= start_idx check at line 268
        content = """</end>
<start>
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
            rule_type="core:block_line_count",
            description="Check blocks",
            params={
                "pattern_start": "^<start>",
                "pattern_end": "^</end>",
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        # Should detect unpaired delimiters (end comes before start)
        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Unpaired delimiters" in result.observed_issue

    def test_same_delimiters_end_before_start(self, validator, tmp_path):
        """Test error when end_line <= start_line for same delimiters."""
        # This is a special case where we manually create a scenario
        # where end_line could be <= start_line (line 242)
        # For same delimiters, this can only happen if delimiters are on same line
        # which is impossible with our pairing logic. However, we can test
        # the edge case by ensuring consecutive delimiters work properly.
        content = """```
```
```
content
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
                "min_lines": 1,
                "files": ["test.md"],
            },
        )

        # Should validate the empty block and the block with content
        result = validator.validate(rule, bundle)
        assert result is not None
        assert "0 lines" in result.observed_issue

    def test_default_failure_message(self, validator):
        """Test default_failure_message property."""
        assert validator.default_failure_message == "Block line count validation failed"

    def test_unicode_decode_error(self, validator, tmp_path):
        """Test handling of files with encoding errors."""
        # Create a file with invalid UTF-8
        test_file = tmp_path / "binary.md"
        test_file.write_bytes(b"\x80\x81\x82\x83")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="documentation",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="binary.md",
                    content="",
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
                "min_lines": 1,
                "files": ["binary.md"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Failed to read file" in result.observed_issue
        assert "UnicodeDecodeError" in result.observed_issue
