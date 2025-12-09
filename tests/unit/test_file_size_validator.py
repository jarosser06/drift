"""Tests for FileSizeValidator."""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.file_validators import FileSizeValidator


class TestFileSizeValidator:
    """Tests for FileSizeValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return FileSizeValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    @pytest.fixture
    def bundle_with_file(self, tmp_path):
        """Create bundle with a test file."""
        test_file = tmp_path / "test.md"
        content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        test_file.write_text(content)

        return DocumentBundle(
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

    def test_line_count_under_max(self, validator, tmp_path):
        """Test that validation passes when line count is under max."""
        test_file = tmp_path / "CLAUDE.md"
        # Create file with 50 lines
        content = "\n".join([f"Line {i}" for i in range(50)])
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="CLAUDE.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check CLAUDE.md line count",
            params={"file_path": "CLAUDE.md", "max_count": 300},
            failure_message="CLAUDE.md exceeds 300 lines",
            expected_behavior="CLAUDE.md should be under 300 lines",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_line_count_exceeds_max(self, validator, tmp_path):
        """Test that validation fails when line count exceeds max."""
        test_file = tmp_path / "CLAUDE.md"
        # Create file with 350 lines
        content = "\n".join([f"Line {i}" for i in range(350)])
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="CLAUDE.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check CLAUDE.md line count",
            params={"file_path": "CLAUDE.md", "max_count": 300},
            failure_message="CLAUDE.md exceeds 300 lines",
            expected_behavior="CLAUDE.md should be under 300 lines",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "CLAUDE.md" in result.file_paths
        assert "350 lines" in result.observed_issue
        assert "exceeds max 300" in result.observed_issue

    def test_line_count_exactly_at_max(self, validator, tmp_path):
        """Test that validation passes when line count equals max."""
        test_file = tmp_path / "test.md"
        # Create file with exactly 300 lines
        content = "\n".join([f"Line {i}" for i in range(300)])
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
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
            params={"file_path": "test.md", "max_count": 300},
            failure_message="File too large",
            expected_behavior="File should be under 300 lines",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_line_count_below_min(self, validator, tmp_path):
        """Test that validation fails when line count is below min."""
        test_file = tmp_path / "test.md"
        # Create file with 5 lines
        content = "\n".join([f"Line {i}" for i in range(5)])
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
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
            description="Check minimum line count",
            params={"file_path": "test.md", "min_count": 10},
            failure_message="File too small",
            expected_behavior="File should have at least 10 lines",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "5 lines" in result.observed_issue
        assert "below min 10" in result.observed_issue

    def test_byte_size_exceeds_max(self, validator, tmp_path):
        """Test that validation fails when byte size exceeds max."""
        test_file = tmp_path / "test.txt"
        # Create file with 2000 bytes
        content = "a" * 2000
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
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
            failure_message="File too large",
            expected_behavior="File should be under 1000 bytes",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "2000 bytes" in result.observed_issue
        assert "exceeds max 1000" in result.observed_issue

    def test_byte_size_under_max(self, validator, tmp_path):
        """Test that validation passes when byte size is under max."""
        test_file = tmp_path / "test.txt"
        # Create file with 500 bytes
        content = "a" * 500
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
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
            failure_message="File too large",
            expected_behavior="File should be under 1000 bytes",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_file_not_found(self, validator, bundle_with_file):
        """Test validation when file doesn't exist."""
        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check nonexistent file",
            params={"file_path": "nonexistent.md", "max_count": 100},
            failure_message="File not found",
            expected_behavior="File should exist",
        )

        result = validator.validate(rule, bundle_with_file)
        assert result is not None
        assert "does not exist" in result.observed_issue
        assert "nonexistent.md" in result.file_paths

    def test_missing_file_path(self, validator, bundle_with_file):
        """Test that validator raises error when file_path is missing."""
        rule = ValidationRule(
            rule_type="core:file_size",
            description="No file path",
            max_count=100,
            failure_message="Error",
            expected_behavior="Should error",
        )

        with pytest.raises(ValueError, match="requires params"):
            validator.validate(rule, bundle_with_file)

    def test_no_constraints(self, validator, bundle_with_file):
        """Test that validation passes when no constraints are specified."""
        rule = ValidationRule(
            rule_type="core:file_size",
            description="No constraints",
            params={"file_path": "test.md"},
            failure_message="Error",
            expected_behavior="Should pass",
        )

        result = validator.validate(rule, bundle_with_file)
        assert result is None

    def test_both_line_and_byte_constraints(self, validator, tmp_path):
        """Test validation with both line count and byte size constraints."""
        test_file = tmp_path / "test.md"
        # Create file with 50 lines and ~500 bytes
        content = "\n".join([f"Line {i}" for i in range(50)])
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
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
            description="Check both constraints",
            params={"file_path": "test.md", "max_count": 100},
            max_size=1000,
            failure_message="File violates constraints",
            expected_behavior="File should meet all constraints",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_computation_type(self, validator):
        """Test that computation_type is programmatic."""
        assert validator.computation_type == "programmatic"

    def test_empty_file(self, validator, tmp_path):
        """Test validation with empty file."""
        test_file = tmp_path / "empty.md"
        test_file.write_text("")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="empty.md",
                    content="",
                    file_path=str(test_file),
                )
            ],
        )

        # Empty file should pass max constraints
        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check empty file",
            params={"file_path": "empty.md", "max_count": 100},
            max_size=1000,
            failure_message="File too large",
            expected_behavior="File should be small",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_single_line_file(self, validator, tmp_path):
        """Test validation with single-line file."""
        test_file = tmp_path / "single.md"
        test_file.write_text("Single line")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="mixed",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="single.md",
                    content="Single line",
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check single line",
            params={"file_path": "single.md", "max_count": 10},
            failure_message="File too large",
            expected_behavior="File should be under 10 lines",
        )

        result = validator.validate(rule, bundle)
        assert result is None
