"""Tests for FileExistsValidator bug #43 - glob pattern validation issues.

Bug #43: FileExistsValidator incorrectly fails when glob pattern matches no files.

The FileExistsValidator should PASS when:
- The directory to search doesn't exist (no matches is valid)
- The directory exists but is empty (no matches is valid)
- Glob pattern matches files with correct names

The FileExistsValidator should FAIL when:
- Glob pattern matches files with incorrect names (e.g., skill.md instead of SKILL.md)

This test file validates these scenarios before the bug is fixed.
All tests that should pass will initially FAIL, demonstrating the bug.
"""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle
from drift.validation.validators import FileExistsValidator


class TestFileExistsValidatorGlobPatterns:
    """Test FileExistsValidator with glob patterns - exposing bug #43."""

    @pytest.fixture
    def validator(self):
        """Create a FileExistsValidator instance."""
        return FileExistsValidator()

    @pytest.fixture
    def base_bundle(self, tmp_path):
        """Create a base document bundle for testing."""
        return DocumentBundle(
            bundle_id="test-bundle",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=tmp_path,
        )

    def test_file_exists_validator_missing_skills_directory_should_pass(
        self, validator, base_bundle
    ):
        """Test that missing .claude/skills/ directory passes validation.

        BUG: Currently FAILS - validator incorrectly treats no matches as failure.
        EXPECTED: Should PASS - missing directory means no skill dirs to validate.
        """
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check skill filename consistency",
            params={"file_path": ".claude/skills/*/SKILL.md"},
            failure_message="Skill files should be named SKILL.md (uppercase), not skill.md",
            expected_behavior="All skill files should use SKILL.md naming convention",
        )

        # Directory doesn't exist at all
        result = validator.validate(rule, base_bundle)

        # BUG: result is NOT None (failure) when it should be None (pass)
        # The validator should pass when the pattern matches no files
        # because there are no skill directories to validate
        assert result is None, (
            "EXPECTED: Validation should pass when .claude/skills/ doesn't exist. "
            "No skill directories means nothing to validate. "
            f"ACTUAL: Validation failed with: {result.observed_issue if result else None}"
        )

    def test_file_exists_validator_empty_skills_directory_should_pass(
        self, validator, base_bundle, tmp_path
    ):
        """Test that empty .claude/skills/ directory passes validation.

        BUG: Currently FAILS - validator incorrectly treats no matches as failure.
        EXPECTED: Should PASS - empty directory means no skill dirs to validate.
        """
        # Create empty .claude/skills/ directory
        skills_dir = tmp_path / ".claude" / "skills"
        skills_dir.mkdir(parents=True, exist_ok=True)

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check skill filename consistency",
            params={"file_path": ".claude/skills/*/SKILL.md"},
            failure_message="Skill files should be named SKILL.md (uppercase), not skill.md",
            expected_behavior="All skill files should use SKILL.md naming convention",
        )

        result = validator.validate(rule, base_bundle)

        # BUG: result is NOT None (failure) when it should be None (pass)
        # The validator should pass when the pattern matches no files
        # because there are no skill subdirectories
        assert result is None, (
            "EXPECTED: Validation should pass when .claude/skills/ is empty. "
            "No skill subdirectories means nothing to validate. "
            f"ACTUAL: Validation failed with: {result.observed_issue if result else None}"
        )

    def test_file_exists_validator_correct_skill_files_should_pass(
        self, validator, base_bundle, tmp_path
    ):
        """Test that correct SKILL.md files pass validation.

        This test should PASS both before and after the bug fix.
        """
        # Create skill directories with correct SKILL.md files
        skill1_dir = tmp_path / ".claude" / "skills" / "testing"
        skill1_dir.mkdir(parents=True, exist_ok=True)
        (skill1_dir / "SKILL.md").write_text("# Testing Skill")

        skill2_dir = tmp_path / ".claude" / "skills" / "linting"
        skill2_dir.mkdir(parents=True, exist_ok=True)
        (skill2_dir / "SKILL.md").write_text("# Linting Skill")

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check skill filename consistency",
            params={"file_path": ".claude/skills/*/SKILL.md"},
            failure_message="Skill files should be named SKILL.md (uppercase), not skill.md",
            expected_behavior="All skill files should use SKILL.md naming convention",
        )

        result = validator.validate(rule, base_bundle)

        # This should pass - correct filenames
        assert result is None, (
            "EXPECTED: Validation should pass when skill files are named SKILL.md. "
            f"ACTUAL: Validation failed with: {result.observed_issue if result else None}"
        )

    def test_file_exists_validator_incorrect_skill_files_should_fail(
        self, validator, base_bundle, tmp_path
    ):
        """Test that skill directories without SKILL.md files fail validation.

        This test verifies that when skill subdirectories exist but don't contain
        the expected SKILL.md file, validation fails.

        Note: Cannot test case-sensitivity (SKILL.md vs skill.md) on macOS
        because the filesystem is case-insensitive. Instead test with completely
        different filename.
        """
        # Create skill directory with wrong filename (not SKILL.md)
        skill_dir = tmp_path / ".claude" / "skills" / "testing"
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "readme.md").write_text("# Testing Skill")  # Wrong filename

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check skill filename consistency",
            params={"file_path": ".claude/skills/*/SKILL.md"},
            failure_message="Skill files should be named SKILL.md",
            expected_behavior="All skill files should use SKILL.md naming convention",
        )

        result = validator.validate(rule, base_bundle)

        # Should fail - skill directory exists but no SKILL.md file
        assert result is not None, (
            "EXPECTED: Validation should fail when skill directories exist "
            "but don't contain SKILL.md files"
        )
        assert "SKILL.md" in result.observed_issue

    def test_file_exists_validator_mixed_correct_and_incorrect_files(
        self, validator, base_bundle, tmp_path
    ):
        """Test with mix of correct and incorrect skill files.

        This demonstrates a limitation of the current glob-based approach:
        it only checks if ANY files match the pattern, not if ALL files
        match the pattern.
        """
        # Create skill1 with correct SKILL.md
        skill1_dir = tmp_path / ".claude" / "skills" / "testing"
        skill1_dir.mkdir(parents=True, exist_ok=True)
        (skill1_dir / "SKILL.md").write_text("# Testing Skill")

        # Create skill2 with incorrect skill.md
        skill2_dir = tmp_path / ".claude" / "skills" / "linting"
        skill2_dir.mkdir(parents=True, exist_ok=True)
        (skill2_dir / "skill.md").write_text("# Linting Skill")

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check skill filename consistency",
            params={"file_path": ".claude/skills/*/SKILL.md"},
            failure_message="Skill files should be named SKILL.md (uppercase), not skill.md",
            expected_behavior="All skill files should use SKILL.md naming convention",
        )

        result = validator.validate(rule, base_bundle)

        # Current implementation: PASSES because at least one SKILL.md exists
        # Ideally: Should FAIL because not ALL skill dirs have SKILL.md
        assert result is None, (
            "CURRENT BEHAVIOR: Validation passes if ANY files match the pattern. "
            "This means mixed correct/incorrect files will pass. "
            "LIMITATION: The validator doesn't detect inconsistent naming across directories."
        )

    def test_file_exists_validator_glob_with_question_mark_wildcard(
        self, validator, base_bundle, tmp_path
    ):
        """Test glob pattern with ? wildcard character."""
        # Create test file that matches pattern
        (tmp_path / "test1.md").write_text("# Test 1")
        (tmp_path / "test2.md").write_text("# Test 2")

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check files with single char wildcard",
            params={"file_path": "test?.md"},
            failure_message="No test files found",
            expected_behavior="Test files should exist",
        )

        result = validator.validate(rule, base_bundle)

        # Should pass - files match the pattern
        assert result is None

    def test_file_exists_validator_glob_no_matches_in_existing_directory(
        self, validator, base_bundle, tmp_path
    ):
        """Test glob pattern that doesn't match any files in existing directory.

        BUG: Currently FAILS when it should FAIL (correct behavior in this case).
        This test confirms the validator correctly fails when the pattern
        doesn't match any files AND we expect files to exist.
        """
        # Create directory structure but no matching files
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "other.txt").write_text("Other file")

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check for markdown files",
            params={"file_path": "docs/*.md"},
            failure_message="No markdown files found in docs/",
            expected_behavior="Markdown files should exist in docs/",
        )

        result = validator.validate(rule, base_bundle)

        # Should fail - no .md files in docs/
        assert result is not None
        assert "No markdown files found" in result.observed_issue

    def test_file_exists_validator_nested_glob_patterns(self, validator, base_bundle, tmp_path):
        """Test deeply nested glob patterns."""
        # Create nested structure
        nested_file = tmp_path / "a" / "b" / "c" / "test.md"
        nested_file.parent.mkdir(parents=True, exist_ok=True)
        nested_file.write_text("# Nested")

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check nested pattern",
            params={"file_path": "a/b/c/*.md"},
            failure_message="No nested files found",
            expected_behavior="Nested files should exist",
        )

        result = validator.validate(rule, base_bundle)

        # Should pass - nested file exists
        assert result is None

    def test_file_exists_validator_glob_with_multiple_wildcards(
        self, validator, base_bundle, tmp_path
    ):
        """Test glob pattern with multiple wildcard segments."""
        # Create matching structure
        file1 = tmp_path / ".claude" / "agents" / "developer.md"
        file1.parent.mkdir(parents=True, exist_ok=True)
        file1.write_text("# Developer")

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check multiple wildcards",
            params={"file_path": ".claude/*/*.md"},
            failure_message="No claude config files found",
            expected_behavior="Claude config files should exist",
        )

        result = validator.validate(rule, base_bundle)

        # Should pass - files match pattern
        assert result is None


class TestFileExistsValidatorEdgeCases:
    """Additional edge case tests for FileExistsValidator."""

    @pytest.fixture
    def validator(self):
        """Create a FileExistsValidator instance."""
        return FileExistsValidator()

    @pytest.fixture
    def base_bundle(self, tmp_path):
        """Create a base document bundle for testing."""
        return DocumentBundle(
            bundle_id="test-bundle",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=tmp_path,
        )

    def test_file_exists_validator_empty_pattern_matching_directories(
        self, validator, base_bundle, tmp_path
    ):
        """Test that glob pattern only matches files, not directories.

        The validator should filter out directories from glob matches.
        """
        # Create structure with directories that match pattern
        skills_base = tmp_path / ".claude" / "skills"
        skills_base.mkdir(parents=True, exist_ok=True)

        # Create skill directory (not a file)
        skill_dir = skills_base / "testing"
        skill_dir.mkdir(parents=True, exist_ok=True)
        # Don't create SKILL.md - just the directory

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check for skill dirs",
            params={"file_path": ".claude/skills/*"},
            failure_message="No skills found",
            expected_behavior="Skills should exist",
        )

        result = validator.validate(rule, base_bundle)

        # Should fail - pattern matches directory but validator only counts files
        assert result is not None, (
            "EXPECTED: Validation should fail when glob matches only directories. "
            "The validator filters matches to only include files. "
            f"ACTUAL: {result.observed_issue if result else 'Passed unexpectedly'}"
        )

    def test_file_exists_validator_symlink_handling(self, validator, base_bundle, tmp_path):
        """Test that symlinks to files are treated as files."""
        # Create a real file
        real_file = tmp_path / "real.md"
        real_file.write_text("# Real")

        # Create a symlink
        link_file = tmp_path / "link.md"
        try:
            link_file.symlink_to(real_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check symlink file",
            params={"file_path": "link.md"},
            failure_message="Symlink not found",
            expected_behavior="Symlink should exist",
        )

        result = validator.validate(rule, base_bundle)

        # Should pass - symlink is treated as a file
        assert result is None

    def test_file_exists_validator_absolute_vs_relative_path(
        self, validator, base_bundle, tmp_path
    ):
        """Test that file_path is always treated as relative to project_path."""
        # Create a file
        (tmp_path / "README.md").write_text("# README")

        # Use relative path (standard)
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check README",
            params={"file_path": "README.md"},
            failure_message="README not found",
            expected_behavior="README should exist",
        )

        result = validator.validate(rule, base_bundle)

        # Should pass
        assert result is None
