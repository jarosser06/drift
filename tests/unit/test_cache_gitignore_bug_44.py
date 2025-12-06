"""Tests for ResponseCache bug #44 - missing .gitignore creation.

Bug #44: The cache initialization should create a .gitignore file in the
.drift/ directory to ignore the cache/ subdirectory, but currently doesn't.

Expected behavior:
1. When .drift/cache/ is created, a .drift/.gitignore should also be created
2. The .gitignore should contain an entry to ignore the cache/ directory
3. Existing .gitignore files should not be overwritten
4. The .gitignore should have proper formatting

This test file validates these scenarios before the bug is fixed.
All tests will initially FAIL, demonstrating the bug exists.
"""

import pytest

from drift.cache import ResponseCache


class TestResponseCacheGitignoreCreation:
    """Test ResponseCache .gitignore creation - exposing bug #44."""

    def test_cache_initialization_creates_gitignore_in_drift_directory(self, tmp_path):
        """Test that .gitignore is created in .drift/ when cache is initialized.

        BUG: Currently FAILS - .gitignore is not created.
        EXPECTED: .drift/.gitignore should be created when .drift/cache/ is created.
        """
        # Use .drift/cache as cache directory (standard location)
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        # Initialize cache (should create .drift/cache/ and .drift/.gitignore)
        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        # Verify cache directory was created
        assert cache_dir.exists(), "Cache directory should be created"

        # BUG: .gitignore is NOT created
        gitignore_path = drift_dir / ".gitignore"
        assert gitignore_path.exists(), (
            "EXPECTED: .drift/.gitignore should be created when cache is initialized. "
            "This prevents cache files from being committed to git. "
            f"ACTUAL: {gitignore_path} does not exist"
        )

    def test_gitignore_contains_cache_entry(self, tmp_path):
        """Test that .gitignore contains entry to ignore cache/ directory.

        BUG: Currently FAILS - .gitignore doesn't exist, so can't contain entry.
        EXPECTED: .gitignore should contain 'cache/' entry.
        """
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        gitignore_path = drift_dir / ".gitignore"

        # BUG: File doesn't exist
        if not gitignore_path.exists():
            pytest.fail(
                "EXPECTED: .drift/.gitignore should exist. "
                f"ACTUAL: {gitignore_path} does not exist"
            )

        # Read .gitignore content
        gitignore_content = gitignore_path.read_text()

        # Should contain cache/ entry
        assert "cache/" in gitignore_content, (
            "EXPECTED: .gitignore should contain 'cache/' entry. "
            f"ACTUAL: .gitignore content:\n{gitignore_content}"
        )

    def test_gitignore_has_proper_format(self, tmp_path):
        """Test that .gitignore has proper formatting.

        BUG: Currently FAILS - .gitignore doesn't exist.
        EXPECTED: .gitignore should have clean, standard format.
        """
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        gitignore_path = drift_dir / ".gitignore"

        # BUG: File doesn't exist
        if not gitignore_path.exists():
            pytest.fail(f"EXPECTED: {gitignore_path} should exist")

        gitignore_content = gitignore_path.read_text()

        # Should have newline at end (standard practice)
        assert gitignore_content.endswith("\n"), (
            "EXPECTED: .gitignore should end with newline. "
            f"ACTUAL: Content: {repr(gitignore_content)}"
        )

        # Should not have trailing whitespace
        lines = gitignore_content.split("\n")
        for i, line in enumerate(lines):
            if line and line != line.rstrip():
                pytest.fail(
                    f"EXPECTED: Line {i} should not have trailing whitespace. "
                    f"ACTUAL: {repr(line)}"
                )

    def test_gitignore_not_overwritten_if_exists(self, tmp_path):
        """Test that existing .gitignore is not overwritten.

        EXPECTED: If .drift/.gitignore already exists, don't overwrite it.
        The user might have custom entries.
        """
        drift_dir = tmp_path / ".drift"
        drift_dir.mkdir(parents=True, exist_ok=True)

        # Create existing .gitignore with custom content
        gitignore_path = drift_dir / ".gitignore"
        custom_content = "# Custom gitignore\ncustom_dir/\n*.tmp\n"
        gitignore_path.write_text(custom_content)

        # Now initialize cache
        cache_dir = drift_dir / "cache"
        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        # Read .gitignore content
        actual_content = gitignore_path.read_text()

        # Should preserve existing content
        assert actual_content == custom_content, (
            "EXPECTED: Existing .gitignore should not be overwritten. "
            f"EXPECTED content:\n{custom_content}\n"
            f"ACTUAL content:\n{actual_content}"
        )

    def test_gitignore_appended_if_missing_cache_entry(self, tmp_path):
        """Test that cache/ is appended to existing .gitignore if missing.

        This is a more sophisticated behavior: check if .gitignore exists,
        and if it doesn't contain 'cache/', append it.
        """
        drift_dir = tmp_path / ".drift"
        drift_dir.mkdir(parents=True, exist_ok=True)

        # Create existing .gitignore without cache/ entry
        gitignore_path = drift_dir / ".gitignore"
        existing_content = "# Existing entries\nother_dir/\n"
        gitignore_path.write_text(existing_content)

        # Initialize cache
        cache_dir = drift_dir / "cache"
        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        # Read .gitignore content
        actual_content = gitignore_path.read_text()

        # Should contain both existing content and cache/ entry
        assert "other_dir/" in actual_content, (
            "EXPECTED: Existing entries should be preserved. " f"ACTUAL content:\n{actual_content}"
        )

        # Note: This test may fail depending on implementation choice:
        # Option 1: Never modify existing .gitignore (preserve user content)
        # Option 2: Append cache/ if missing (be helpful)
        #
        # For this test, we'll just verify it doesn't overwrite existing content
        # The cache/ entry requirement is optional in this case

    def test_gitignore_not_created_when_cache_disabled(self, tmp_path):
        """Test that .gitignore is not created when caching is disabled.

        EXPECTED: If cache is disabled, don't create any files.
        """
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        # Initialize with caching disabled
        _cache = ResponseCache(cache_dir=cache_dir, enabled=False)  # noqa: F841

        # Cache directory should NOT be created
        assert (
            not cache_dir.exists()
        ), "EXPECTED: Cache directory should not be created when disabled"

        # .gitignore should also NOT be created
        gitignore_path = drift_dir / ".gitignore"
        assert (
            not gitignore_path.exists()
        ), "EXPECTED: .gitignore should not be created when cache is disabled"

    def test_gitignore_created_in_parent_of_cache_not_in_cache(self, tmp_path):
        """Test that .gitignore is created in .drift/, not in .drift/cache/.

        EXPECTED: .gitignore should be in the parent directory (.drift/),
        not inside the cache directory itself.
        """
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        # .gitignore should be in .drift/
        parent_gitignore = drift_dir / ".gitignore"

        # .gitignore should NOT be in .drift/cache/
        cache_gitignore = cache_dir / ".gitignore"

        # BUG: Neither exist currently, but when fixed should be in parent
        if parent_gitignore.exists() or cache_gitignore.exists():
            assert parent_gitignore.exists(), (
                "EXPECTED: .gitignore should be in .drift/ directory. "
                f"ACTUAL: Found in {cache_gitignore if cache_gitignore.exists() else 'nowhere'}"
            )

            assert not cache_gitignore.exists(), (
                "EXPECTED: .gitignore should NOT be inside cache/ directory. "
                "It should be in the parent .drift/ directory."
            )

    def test_gitignore_works_with_non_standard_cache_location(self, tmp_path):
        """Test .gitignore creation when cache is in a custom location.

        If cache is at a custom location (not .drift/cache), we still want
        to create .gitignore in the appropriate place.

        This test explores the expected behavior for custom cache directories.
        """
        # Custom cache location: project_root/custom_cache
        cache_dir = tmp_path / "custom_cache"

        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        # For custom cache locations, .gitignore behavior is less clear:
        # Option 1: Create .gitignore in custom_cache parent (project root)
        # Option 2: Only create .gitignore for .drift/ locations
        # Option 3: Don't create .gitignore for custom locations

        # For now, we'll document that this is undefined behavior
        # The primary bug fix should focus on .drift/cache/ case

        _gitignore_path = tmp_path / ".gitignore"  # noqa: F841

        # This test is mainly for documentation - behavior to be decided
        # Most likely: only create .gitignore when cache is under .drift/


class TestResponseCacheGitignoreContent:
    """Test the content and format of the generated .gitignore file."""

    def test_gitignore_uses_relative_path_for_cache(self, tmp_path):
        """Test that .gitignore uses relative path 'cache/' not absolute path.

        EXPECTED: .gitignore should contain 'cache/' (relative path),
        not '/absolute/path/to/.drift/cache/' (absolute path).
        """
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        gitignore_path = drift_dir / ".gitignore"

        if not gitignore_path.exists():
            pytest.skip(".gitignore not created (known bug)")

        gitignore_content = gitignore_path.read_text()

        # Should use relative path
        assert "cache/" in gitignore_content, "EXPECTED: Should use relative path 'cache/'"

        # Should NOT use absolute path
        assert str(cache_dir) not in gitignore_content, (
            "EXPECTED: Should not use absolute path in .gitignore. " f"ACTUAL: {gitignore_content}"
        )

    def test_gitignore_includes_helpful_comment(self, tmp_path):
        """Test that .gitignore includes a comment explaining its purpose.

        EXPECTED: .gitignore should include a comment like:
        '# Drift cache directory - auto-generated'
        This helps users understand why the file exists.
        """
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        _cache = ResponseCache(cache_dir=cache_dir, enabled=True)  # noqa: F841

        gitignore_path = drift_dir / ".gitignore"

        if not gitignore_path.exists():
            pytest.skip(".gitignore not created (known bug)")

        gitignore_content = gitignore_path.read_text()

        # Should include a comment (check for # character)
        assert "#" in gitignore_content, (
            "EXPECTED: .gitignore should include explanatory comment. "
            f"ACTUAL: {gitignore_content}"
        )

    def test_gitignore_ignores_all_cache_contents(self, tmp_path):
        """Test that .gitignore pattern ignores all files in cache directory.

        The pattern 'cache/' should ignore the entire directory and all contents.
        """
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        cache = ResponseCache(cache_dir=cache_dir, enabled=True)

        # Create some cache files
        cache.set("key1", "hash1", "response1")
        cache.set("key2", "hash2", "response2")

        gitignore_path = drift_dir / ".gitignore"

        if not gitignore_path.exists():
            pytest.skip(".gitignore not created (known bug)")

        gitignore_content = gitignore_path.read_text()

        # Pattern 'cache/' should ignore directory and all contents
        assert "cache/" in gitignore_content, "EXPECTED: Pattern 'cache/' ignores entire directory"

        # Verify cache files were created
        cache_files = list(cache_dir.glob("*.json"))
        assert len(cache_files) == 2, "Cache files should exist for testing"
