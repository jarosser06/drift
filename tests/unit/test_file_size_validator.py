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
        """Test that validator works with bundle files when file_path is not provided."""
        rule = ValidationRule(
            rule_type="core:file_size",
            description="No file path",
            params={"max_count": 100},
            failure_message="Error",
            expected_behavior="Should pass",
        )

        # Should validate files in bundle when file_path not provided
        result = validator.validate(rule, bundle_with_file)
        assert result is None  # Should pass since bundle file is under 100 lines

    def test_no_constraints(self, validator, bundle_with_file):
        """Test that validator raises error when no constraints are specified."""
        rule = ValidationRule(
            rule_type="core:file_size",
            description="No constraints",
            params={"file_path": "test.md"},
            failure_message="Error",
            expected_behavior="Should error",
        )

        with pytest.raises(ValueError, match="requires at least one constraint"):
            validator.validate(rule, bundle_with_file)

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

    def test_bundle_mode_validates_all_files(self, validator, tmp_path):
        """Test that validator iterates over bundle.files when file_path not provided."""
        # Create test files
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"
        file3 = tmp_path / "file3.md"

        file1.write_text("\n".join([f"Line {i}" for i in range(100)]))  # 100 lines
        file2.write_text("\n".join([f"Line {i}" for i in range(200)]))  # 200 lines (exceeds)
        file3.write_text("\n".join([f"Line {i}" for i in range(50)]))  # 50 lines

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="file1.md",
                    content=file1.read_text(),
                    file_path=str(file1),
                ),
                DocumentFile(
                    relative_path="file2.md",
                    content=file2.read_text(),
                    file_path=str(file2),
                ),
                DocumentFile(
                    relative_path="file3.md",
                    content=file3.read_text(),
                    file_path=str(file3),
                ),
            ],
        )

        # Validate without file_path - should check all files in bundle
        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check line count",
            params={"max_count": 150},  # file2 exceeds this
            failure_message="File exceeds max lines",
            expected_behavior="Files should be under 150 lines",
        )

        result = validator.validate(rule, bundle)

        # Should fail because file2.md exceeds 150 lines
        assert result is not None
        assert "file2.md" in result.observed_issue
        assert "200 lines" in result.observed_issue
        assert "exceeds max 150" in result.observed_issue

        # file1 and file3 should NOT be in failures
        assert "file1.md" not in result.observed_issue
        assert "file3.md" not in result.observed_issue

    def test_bundle_mode_all_files_pass(self, validator, tmp_path):
        """Test that bundle mode returns None when all files pass."""
        file1 = tmp_path / "file1.md"
        file2 = tmp_path / "file2.md"

        file1.write_text("\n".join([f"Line {i}" for i in range(50)]))
        file2.write_text("\n".join([f"Line {i}" for i in range(30)]))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="file1.md",
                    content=file1.read_text(),
                    file_path=str(file1),
                ),
                DocumentFile(
                    relative_path="file2.md",
                    content=file2.read_text(),
                    file_path=str(file2),
                ),
            ],
        )

        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check line count",
            params={"max_count": 100},
            failure_message="File too large",
            expected_behavior="Files should be under 100 lines",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # All files pass

    def test_bundle_mode_vs_file_path_mode(self, validator, tmp_path):
        """Test that file_path param validates specific file, not bundle files."""
        # Create files
        bundle_file = tmp_path / "bundle_file.md"
        specific_file = tmp_path / "specific.md"

        bundle_file.write_text("\n".join([f"Line {i}" for i in range(50)]))  # OK
        specific_file.write_text("\n".join([f"Line {i}" for i in range(200)]))  # Too large

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="bundle_file.md",
                    content=bundle_file.read_text(),
                    file_path=str(bundle_file),
                ),
            ],
        )

        # When file_path provided, should validate that specific file (not bundle files)
        rule = ValidationRule(
            rule_type="core:file_size",
            description="Check specific file",
            params={
                "file_path": "specific.md",  # Not in bundle
                "max_count": 100,
            },
            failure_message="File too large",
            expected_behavior="File should be under 100 lines",
        )

        result = validator.validate(rule, bundle)

        # Should fail on specific.md, not bundle_file.md
        assert result is not None
        assert "specific.md" in result.file_paths
        assert "200 lines" in result.observed_issue
        assert "exceeds max 100" in result.observed_issue
