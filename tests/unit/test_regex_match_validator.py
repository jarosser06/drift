"""Tests for RegexMatchValidator."""

import re

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.regex_validators import RegexMatchValidator


class TestRegexMatchValidator:
    """Tests for RegexMatchValidator."""

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
        test_file.write_text("# Header\n\nSome content\n## Prerequisites\n\nMore content")

        return DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content="# Header\n\nSome content\n## Prerequisites\n\nMore content",
                    file_path=str(test_file),
                )
            ],
        )

    def test_regex_match_passes(self, validator, bundle_with_file):
        """Test that validation passes when pattern matches."""
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Check for Prerequisites section",
            file_path="test.md",
            pattern=r"## Prerequisites",
            failure_message="Missing Prerequisites section",
            expected_behavior="Should have Prerequisites section",
        )

        result = validator.validate(rule, bundle_with_file)
        assert result is None

    def test_regex_match_fails(self, validator, bundle_with_file):
        """Test that validation fails when pattern doesn't match."""
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Check for Installation section",
            file_path="test.md",
            pattern=r"## Installation",
            failure_message="Missing Installation section",
            expected_behavior="Should have Installation section",
        )

        result = validator.validate(rule, bundle_with_file)
        assert result is not None
        assert "test.md" in result.file_paths
        assert "Pattern '## Installation' not found" in result.context

    def test_regex_match_with_flags(self, validator, tmp_path):
        """Test regex matching with flags (e.g., MULTILINE)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("First line\nSecond line\nThird line")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.txt",
                    content="First line\nSecond line\nThird line",
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Match line start",
            file_path="test.txt",
            pattern=r"^Second",
            flags=re.MULTILINE,
            failure_message="Pattern not found",
            expected_behavior="Should match",
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_regex_match_file_not_found(self, validator, bundle_with_file):
        """Test validation when file doesn't exist."""
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Check nonexistent file",
            file_path="nonexistent.md",
            pattern=r"test",
            failure_message="File not found",
            expected_behavior="File should exist",
        )

        result = validator.validate(rule, bundle_with_file)
        assert result is not None
        assert "File not found" in result.context
        assert "nonexistent.md" in result.file_paths

    def test_regex_match_without_file_path_validates_bundle(self, validator, bundle_with_file):
        """Test that validator validates all files in bundle when file_path is not specified."""
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Check all files in bundle",
            pattern=r"## Prerequisites",
            failure_message="Missing Prerequisites section",
            expected_behavior="Should have Prerequisites section",
        )

        # Should validate the file in the bundle and pass
        result = validator.validate(rule, bundle_with_file)
        assert result is None

    def test_regex_match_without_file_path_fails_on_empty_bundle(self, validator, tmp_path):
        """Test that validator passes on empty bundle when file_path is not specified."""
        empty_bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Check empty bundle",
            pattern=r"test",
            failure_message="Pattern not found",
            expected_behavior="Should match",
        )

        # Empty bundle should pass (no files to validate)
        result = validator.validate(rule, empty_bundle)
        assert result is None

    def test_regex_match_without_file_path_validates_multiple_files(self, validator, tmp_path):
        """Test that validator validates all files in bundle."""
        file1 = tmp_path / "file1.md"
        file1.write_text("# Header\n## Prerequisites\n")
        file2 = tmp_path / "file2.md"
        file2.write_text("# Another Header\nNo prerequisites here")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="file1.md",
                    content="# Header\n## Prerequisites\n",
                    file_path=str(file1),
                ),
                DocumentFile(
                    relative_path="file2.md",
                    content="# Another Header\nNo prerequisites here",
                    file_path=str(file2),
                ),
            ],
        )

        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Check for Prerequisites in all files",
            pattern=r"## Prerequisites",
            failure_message="Missing Prerequisites section",
            expected_behavior="All files should have Prerequisites section",
        )

        # Should fail because file2 doesn't match
        result = validator.validate(rule, bundle)
        assert result is not None
        assert "file2.md" in result.file_paths
        assert "1 file(s)" in result.context

    def test_regex_match_missing_pattern(self, validator, bundle_with_file):
        """Test that validator raises error when pattern is missing."""
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="No pattern",
            file_path="test.md",
            failure_message="Error",
            expected_behavior="Should error",
        )

        with pytest.raises(ValueError, match="requires rule.pattern"):
            validator.validate(rule, bundle_with_file)

    def test_regex_match_invalid_pattern(self, validator, bundle_with_file):
        """Test that ValidationRule catches invalid regex pattern."""
        # The ValidationRule model should catch this during creation
        from pydantic import ValidationError

        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            ValidationRule(
                rule_type=ValidationType.REGEX_MATCH,
                description="Invalid regex",
                file_path="test.md",
                pattern=r"[invalid(regex",  # Unclosed bracket
                failure_message="Invalid pattern",
                expected_behavior="Should have valid pattern",
            )

    def test_regex_match_read_error(self, validator, tmp_path):
        """Test validation when file cannot be read."""
        # Create a file then make it unreadable
        test_file = tmp_path / "test.md"
        test_file.write_text("content")
        test_file.chmod(0o000)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
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
            rule_type=ValidationType.REGEX_MATCH,
            description="Read protected file",
            file_path="test.md",
            pattern=r"test",
            failure_message="Cannot read",
            expected_behavior="Should be readable",
        )

        try:
            result = validator.validate(rule, bundle)
            # Should return error about failed read
            assert result is not None
            assert "Failed to read file" in result.context
        finally:
            # Restore permissions for cleanup
            test_file.chmod(0o644)

    def test_computation_type(self, validator):
        """Test that computation_type is programmatic."""
        assert validator.computation_type == "programmatic"

    def test_regex_match_case_sensitive(self, validator, tmp_path):
        """Test that regex matching is case-sensitive by default."""
        test_file = tmp_path / "test.md"
        test_file.write_text("HELLO world")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content="HELLO world",
                    file_path=str(test_file),
                )
            ],
        )

        # Should not match (case-sensitive)
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Case-sensitive match",
            file_path="test.md",
            pattern=r"hello",
            failure_message="Pattern not found",
            expected_behavior="Should match",
        )

        result = validator.validate(rule, bundle)
        assert result is not None

    def test_regex_match_case_insensitive(self, validator, tmp_path):
        """Test regex matching with IGNORECASE flag."""
        test_file = tmp_path / "test.md"
        test_file.write_text("HELLO world")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="test.md",
                    content="HELLO world",
                    file_path=str(test_file),
                )
            ],
        )

        # Should match with IGNORECASE
        rule = ValidationRule(
            rule_type=ValidationType.REGEX_MATCH,
            description="Case-insensitive match",
            file_path="test.md",
            pattern=r"hello",
            flags=re.IGNORECASE,
            failure_message="Pattern not found",
            expected_behavior="Should match",
        )

        result = validator.validate(rule, bundle)
        assert result is None
