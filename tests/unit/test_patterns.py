"""Unit tests for pattern matching utilities."""

import pytest

from drift.validation.patterns import (
    is_regex_pattern,
    match_glob_pattern,
    match_literal_path,
    match_pattern,
    match_regex_pattern,
    should_ignore_path,
)


class TestIsRegexPattern:
    """Tests for is_regex_pattern function."""

    @pytest.mark.parametrize(
        "pattern,expected",
        [
            (r"\(test\)", True),
            (r"\[abc\]", True),
            (r"\{1,3\}", True),
            (r"\^start", True),
            (r"end\$", True),
            (r"one\+more", True),
            (r"file\.txt", True),
            (r"a\|b", True),
            (r"\)", True),
            ("*.py", False),
            ("**/*.md", False),
            ("simple_file.txt", False),
            ("path/to/file", False),
            ("test", False),
            ("", False),
        ],
    )
    def test_regex_pattern_detection(self, pattern, expected):
        """Test detection of regex patterns vs glob patterns."""
        assert is_regex_pattern(pattern) == expected

    def test_multiple_indicators(self):
        """Test pattern with multiple regex indicators."""
        pattern = r"\(test\)\.\+\$"
        assert is_regex_pattern(pattern) is True


class TestMatchGlobPattern:
    """Tests for match_glob_pattern function."""

    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("test.py", "*.py", True),
            ("test.md", "*.py", False),
            ("src/test.py", "**/*.py", True),
            ("src/nested/test.py", "**/*.py", True),
            ("src/test.py", "src/*.py", True),
            ("src/nested/test.py", "src/*.py", False),
            (".git/config", ".git/**", True),
            ("README.md", "README.md", True),
            ("temp_file.tmp", "*.tmp", True),
            ("cache/temp.tmp", "**/*.tmp", True),
        ],
    )
    def test_glob_pattern_matching(self, path, pattern, expected):
        """Test glob pattern matching with various patterns."""
        assert match_glob_pattern(path, pattern) == expected

    def test_character_class_patterns(self):
        """Test glob patterns with character classes."""
        assert match_glob_pattern("test1.py", "test[0-9].py") is True
        assert match_glob_pattern("testa.py", "test[0-9].py") is False

    def test_question_mark_wildcard(self):
        """Test glob patterns with ? wildcard."""
        assert match_glob_pattern("test.py", "test.??") is True
        assert match_glob_pattern("test.python", "test.??") is False

    def test_case_sensitivity(self):
        """Test that glob matching is case-sensitive on most systems."""
        result = match_glob_pattern("Test.py", "test.py")
        assert result is False

    def test_invalid_patterns(self):
        """Test handling of invalid patterns."""
        assert match_glob_pattern("test.py", None) is False
        assert match_glob_pattern(None, "*.py") is False


class TestMatchRegexPattern:
    """Tests for match_regex_pattern function."""

    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("test.py", r"test\.py", True),
            ("test.md", r"test\.py", False),
            ("src/test.py", r"^src/.*\.py$", True),
            ("test.py", r"^src/.*\.py$", False),
            ("file123.txt", r"file\d+\.txt", True),
            ("fileABC.txt", r"file\d+\.txt", False),
            ("README.md", r"^README\.md$", True),
            ("docs/README.md", r".*README\.md$", True),
            ("test", r"^test$", True),
            ("testing", r"^test$", False),
        ],
    )
    def test_regex_pattern_matching(self, path, pattern, expected):
        """Test regex pattern matching."""
        assert match_regex_pattern(path, pattern) == expected

    def test_groups_and_alternation(self):
        """Test regex patterns with groups and alternation."""
        pattern = r"(test|spec)_.*\.py"
        assert match_regex_pattern("test_foo.py", pattern) is True
        assert match_regex_pattern("spec_bar.py", pattern) is True
        assert match_regex_pattern("other_baz.py", pattern) is False

    def test_anchors(self):
        """Test regex anchors."""
        assert match_regex_pattern("test.py", r"^test") is True
        assert match_regex_pattern("my_test.py", r"^test") is False
        assert match_regex_pattern("test.py", r".*\.py$") is True
        assert match_regex_pattern("test.py.bak", r".*\.py$") is False

    def test_character_classes(self):
        """Test regex character classes."""
        assert match_regex_pattern("test1.py", r"test[0-9]\.py") is True
        assert match_regex_pattern("testa.py", r"test[0-9]\.py") is False
        assert match_regex_pattern("TEST.py", r"[A-Z]+\.py") is True

    def test_invalid_regex(self):
        """Test that invalid regex patterns raise ValueError."""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            match_regex_pattern("test.py", r"(unclosed")

        with pytest.raises(ValueError, match="Invalid regex pattern"):
            match_regex_pattern("test.py", r"[unclosed")


class TestMatchLiteralPath:
    """Tests for match_literal_path function."""

    def test_exact_match(self):
        """Test exact path matching."""
        assert match_literal_path("test.py", "test.py") is True
        assert match_literal_path("test.md", "test.py") is False

    def test_path_normalization(self):
        """Test that paths are normalized for comparison."""
        assert match_literal_path("src/test.py", "src/test.py") is True

    def test_suffix_matching(self):
        """Test matching when path ends with literal."""
        assert match_literal_path("/abs/path/to/file.py", "to/file.py") is True
        assert match_literal_path("/abs/path/to/file.py", "file.py") is True
        assert match_literal_path("/abs/path/to/file.py", "other.py") is False

    def test_leading_slash_handling(self):
        """Test handling of leading slashes."""
        assert match_literal_path("/abs/path/file.py", "path/file.py") is True

    def test_case_sensitivity(self):
        """Test case sensitivity in literal matching."""
        result = match_literal_path("Test.py", "test.py")
        assert result is False


class TestMatchPattern:
    """Tests for match_pattern auto-detection wrapper."""

    def test_auto_detect_glob(self):
        """Test auto-detection of glob patterns."""
        assert match_pattern("test.py", "*.py") is True
        assert match_pattern("src/test.py", "**/*.py") is True

    def test_auto_detect_regex(self):
        """Test auto-detection of regex patterns."""
        assert match_pattern("test.py", r"test\.py") is True
        assert match_pattern("test123.py", r"test\d+\.py") is True

    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("test.py", "*.py", True),
            ("test.py", r"test\.py", True),
            ("src/test.py", "**/*.py", True),
            ("test123.py", r"test\d+\.py", True),
            ("wrong.md", "*.py", False),
            ("wrong.md", r"test\.py", False),
        ],
    )
    def test_mixed_patterns(self, path, pattern, expected):
        """Test matching with mixed glob and regex patterns."""
        assert match_pattern(path, pattern) == expected

    def test_invalid_regex_in_auto_detect(self):
        """Test that invalid regex raises ValueError."""
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            match_pattern("test.py", r"(unclosed\)")


class TestShouldIgnorePath:
    """Tests for should_ignore_path function."""

    def test_empty_patterns(self):
        """Test with empty pattern list."""
        assert should_ignore_path("test.py", []) is False

    def test_none_patterns(self):
        """Test with None pattern list."""
        assert should_ignore_path("test.py", None) is False

    def test_single_matching_pattern(self):
        """Test with single matching pattern."""
        assert should_ignore_path("test.tmp", ["*.tmp"]) is True

    def test_single_non_matching_pattern(self):
        """Test with single non-matching pattern."""
        assert should_ignore_path("test.py", ["*.tmp"]) is False

    def test_multiple_patterns_first_matches(self):
        """Test with multiple patterns where first matches."""
        patterns = ["*.tmp", "*.bak", "*.log"]
        assert should_ignore_path("file.tmp", patterns) is True

    def test_multiple_patterns_last_matches(self):
        """Test with multiple patterns where last matches."""
        patterns = ["*.tmp", "*.bak", "*.log"]
        assert should_ignore_path("file.log", patterns) is True

    def test_multiple_patterns_none_match(self):
        """Test with multiple patterns where none match."""
        patterns = ["*.tmp", "*.bak", "*.log"]
        assert should_ignore_path("file.py", patterns) is False

    @pytest.mark.parametrize(
        "path,patterns,expected",
        [
            ("cache/temp.tmp", ["**/*.tmp"], True),
            (".git/config", [".git/**"], True),
            ("build/output.txt", ["build/**", "dist/**"], True),
            ("src/test.py", ["*.tmp", "*.log"], False),
            ("important.txt", ["**/*.tmp", "cache/**"], False),
        ],
    )
    def test_glob_patterns(self, path, patterns, expected):
        """Test with glob patterns."""
        assert should_ignore_path(path, patterns) == expected

    @pytest.mark.parametrize(
        "path,patterns,expected",
        [
            ("test123.py", [r"test\d+\.py"], True),
            ("test.py", [r"^test\.py$"], True),
            ("src/test.py", [r"src/.*\.py"], True),
            ("other.py", [r"test\d+\.py"], False),
        ],
    )
    def test_regex_patterns(self, path, patterns, expected):
        """Test with regex patterns."""
        assert should_ignore_path(path, patterns) == expected

    def test_mixed_glob_and_regex_patterns(self):
        """Test with mixed glob and regex patterns."""
        patterns = ["*.tmp", r"test\d+\.py", "**/*.log"]
        assert should_ignore_path("file.tmp", patterns) is True
        assert should_ignore_path("test123.py", patterns) is True
        assert should_ignore_path("logs/app.log", patterns) is True
        assert should_ignore_path("src/main.py", patterns) is False

    def test_invalid_regex_in_patterns(self):
        """Test that invalid regex in pattern list raises ValueError."""
        patterns = ["*.tmp", r"(unclosed\)"]
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            should_ignore_path("test.py", patterns)

    def test_early_termination(self):
        """Test that function returns True on first match."""
        patterns = ["*.py", "*.md", "*.txt"]
        assert should_ignore_path("test.py", patterns) is True

    def test_complex_real_world_patterns(self):
        """Test with complex real-world ignore patterns."""
        patterns = [
            "**/__pycache__/**",
            "*.pyc",
            "**/*.pyc",
            ".git/**",
            ".env",
            "*.log",
            r"^test_.*\.py",
            "dist/**",
            "build/**",
        ]

        assert should_ignore_path("src/__pycache__/module.pyc", patterns) is True
        assert should_ignore_path("app.pyc", patterns) is True
        assert should_ignore_path(".git/HEAD", patterns) is True
        assert should_ignore_path(".env", patterns) is True
        assert should_ignore_path("debug.log", patterns) is True
        assert should_ignore_path("test_foo.py", patterns) is True

        assert should_ignore_path("src/main.py", patterns) is False
        assert should_ignore_path("README.md", patterns) is False
        assert should_ignore_path("integration_test.py", patterns) is False
