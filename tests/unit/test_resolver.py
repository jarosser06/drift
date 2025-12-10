"""Unit tests for file pattern resolver."""


from drift.draft.resolver import FilePatternResolver


class TestFilePatternResolver:
    """Tests for FilePatternResolver class."""

    def test_resolve_pattern_without_wildcard(self, temp_dir):
        """Test resolving a simple pattern without wildcards."""
        resolver = FilePatternResolver(temp_dir)
        pattern = "README.md"

        result = resolver.resolve(pattern)

        assert len(result) == 1
        assert result[0] == temp_dir / "README.md"

    def test_resolve_pattern_with_wildcard_returns_empty(self, temp_dir):
        """Test resolving pattern with wildcard returns empty list."""
        resolver = FilePatternResolver(temp_dir)
        pattern = ".claude/skills/*/SKILL.md"

        result = resolver.resolve(pattern)

        # Pattern has wildcard, should return empty list
        assert result == []

    def test_resolve_pattern_with_asterisk_wildcard(self, temp_dir):
        """Test resolving pattern with * wildcard returns empty list."""
        # Create directory structure (shouldn't matter)
        skills_dir = temp_dir / ".claude" / "skills"
        (skills_dir / "testing").mkdir(parents=True)
        (skills_dir / "linting").mkdir(parents=True)

        resolver = FilePatternResolver(temp_dir)
        pattern = ".claude/skills/*/SKILL.md"

        result = resolver.resolve(pattern)

        # Pattern has wildcard, should return empty list regardless of filesystem
        assert result == []

    def test_resolve_pattern_with_question_mark_wildcard(self, temp_dir):
        """Test resolving pattern with ? wildcard returns empty list."""
        # Create directory structure
        skills_dir = temp_dir / ".claude" / "skills"
        (skills_dir / "test1").mkdir(parents=True)
        (skills_dir / "test2").mkdir(parents=True)

        resolver = FilePatternResolver(temp_dir)
        pattern = ".claude/skills/test?/SKILL.md"

        result = resolver.resolve(pattern)

        # Pattern has ? wildcard, should return empty list
        assert result == []

    def test_resolve_pattern_wildcard_at_end(self, temp_dir):
        """Test resolving pattern with wildcard at the end (e.g., *.md)."""
        # Create directory with markdown files
        docs_dir = temp_dir / "docs"
        docs_dir.mkdir()
        (docs_dir / "README.md").touch()
        (docs_dir / "GUIDE.md").touch()

        resolver = FilePatternResolver(temp_dir)
        pattern = "docs/*.md"

        result = resolver.resolve(pattern)

        # Pattern has wildcard, should return empty list
        assert result == []

    def test_resolve_pattern_wildcard_at_start(self, temp_dir):
        """Test resolving pattern that starts with wildcard."""
        # Create some directories in root
        (temp_dir / "dir1").mkdir()
        (temp_dir / "dir2").mkdir()

        resolver = FilePatternResolver(temp_dir)
        pattern = "*/config.yaml"

        result = resolver.resolve(pattern)

        # Pattern has wildcard, should return empty list
        assert result == []

    def test_resolve_pattern_no_wildcard_returns_absolute_path(self, temp_dir):
        """Test that paths without wildcards are resolved to absolute paths."""
        resolver = FilePatternResolver(temp_dir)
        pattern = ".claude/skills/testing/SKILL.md"

        result = resolver.resolve(pattern)

        # Result should contain single absolute path
        assert len(result) == 1
        assert result[0] == temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"

    def test_resolve_pattern_multiple_wildcards_returns_empty(self, temp_dir):
        """Test that patterns with multiple wildcards return empty list."""
        # Create directory structure
        base_dir = temp_dir / ".claude" / "skills" / "testing" / "examples"
        base_dir.mkdir(parents=True)

        resolver = FilePatternResolver(temp_dir)
        # Pattern with multiple wildcards
        pattern = ".claude/skills/*/examples/*.md"

        result = resolver.resolve(pattern)

        # Pattern has wildcards, should return empty list
        assert result == []
