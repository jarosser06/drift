"""Tests for LLM response caching."""

import json
import time

from drift.cache import ResponseCache


class TestResponseCache:
    """Test ResponseCache functionality."""

    def test_cache_disabled(self, tmp_path):
        """Test that caching is disabled when enabled=False."""
        cache_dir = tmp_path / "cache"
        cache = ResponseCache(cache_dir=cache_dir, enabled=False)

        # Should not create cache directory
        assert not cache_dir.exists()

        # Get should always return None
        assert cache.get("key", "hash") is None

        # Set should not create files
        cache.set("key", "hash", "response")
        # Cache directory should still not exist
        assert not cache_dir.exists()

    def test_cache_miss_file_not_found(self, tmp_path):
        """Test cache miss when file doesn't exist."""
        cache = ResponseCache(cache_dir=tmp_path)

        result = cache.get("nonexistent", "somehash")
        assert result is None

    def test_cache_hit_valid(self, tmp_path):
        """Test successful cache hit with valid content."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Store in cache
        cache.set("test_key", "hash123", "test response", drift_type="test_type")

        # Retrieve from cache
        result = cache.get("test_key", "hash123")
        assert result == "test response"

    def test_cache_invalidation_hash_mismatch(self, tmp_path):
        """Test cache invalidation when content hash changes."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Store with hash1
        cache.set("test_key", "hash1", "old response")

        # Try to retrieve with different hash
        result = cache.get("test_key", "hash2")
        assert result is None

        # Cache file should be deleted
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 0

    def test_cache_expiration_ttl(self, tmp_path):
        """Test cache expiration based on TTL."""
        cache = ResponseCache(cache_dir=tmp_path, default_ttl=1)

        # Store in cache
        cache.set("test_key", "hash123", "test response")

        # Should be valid immediately
        assert cache.get("test_key", "hash123") == "test response"

        # Wait for TTL to expire
        time.sleep(2)

        # Should be expired now
        result = cache.get("test_key", "hash123")
        assert result is None

    def test_cache_ttl_override(self, tmp_path):
        """Test TTL can be overridden per-call."""
        cache = ResponseCache(cache_dir=tmp_path, default_ttl=100)

        # Store with short TTL override
        cache.set("test_key", "hash123", "test response", ttl=1)

        # Wait for short TTL to expire
        time.sleep(2)

        # Should be expired
        assert cache.get("test_key", "hash123", ttl=1) is None

    def test_invalidate_removes_file(self, tmp_path):
        """Test that invalidate removes the cache file."""
        cache = ResponseCache(cache_dir=tmp_path)

        cache.set("test_key", "hash123", "test response")
        cache_file = tmp_path / "test_key.json"
        assert cache_file.exists()

        cache.invalidate("test_key")
        assert not cache_file.exists()

    def test_clear_all_removes_all_files(self, tmp_path):
        """Test that clear_all removes all cache files."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create multiple cache entries
        cache.set("key1", "hash1", "response1")
        cache.set("key2", "hash2", "response2")
        cache.set("key3", "hash3", "response3")

        assert len(list(tmp_path.glob("*.json"))) == 3

        count = cache.clear_all()
        assert count == 3
        assert len(list(tmp_path.glob("*.json"))) == 0

    def test_cache_file_path_sanitization(self, tmp_path):
        """Test that cache keys with special characters are sanitized."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Key with path separators and special chars
        cache.set("path/to/file:test<>?", "hash", "response")

        # Should create file with sanitized name
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 1
        assert "/" not in cache_files[0].name
        assert ":" not in cache_files[0].name

    def test_cache_stores_metadata(self, tmp_path):
        """Test that cache stores all metadata correctly."""
        cache = ResponseCache(cache_dir=tmp_path, default_ttl=3600)

        cache.set("test_key", "hash123", "test response", drift_type="incomplete_work")

        # Read cache file directly
        cache_file = tmp_path / "test_key.json"
        with open(cache_file, "r") as f:
            data = json.load(f)

        assert data["content_hash"] == "hash123"
        assert data["response_content"] == "test response"
        assert data["drift_type"] == "incomplete_work"
        assert data["ttl"] == 3600
        assert "timestamp" in data

    def test_compute_content_hash(self):
        """Test content hash computation."""
        hash1 = ResponseCache.compute_content_hash("test content")
        hash2 = ResponseCache.compute_content_hash("test content")
        hash3 = ResponseCache.compute_content_hash("different content")

        # Same content should produce same hash
        assert hash1 == hash2

        # Different content should produce different hash
        assert hash1 != hash3

        # Should be SHA-256 hex string
        assert len(hash1) == 64
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_cache_with_unicode_content(self, tmp_path):
        """Test caching with unicode content."""
        cache = ResponseCache(cache_dir=tmp_path)

        unicode_content = "Test with émojis 🎉 and spëcial çhars"
        hash_val = ResponseCache.compute_content_hash(unicode_content)

        cache.set("unicode_key", hash_val, unicode_content)
        result = cache.get("unicode_key", hash_val)

        assert result == unicode_content

    def test_malformed_cache_file_handling(self, tmp_path):
        """Test that malformed cache files are handled gracefully."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create malformed cache file
        cache_file = tmp_path / "test_key.json"
        cache_file.write_text("invalid json {")

        # Should return None and invalidate
        result = cache.get("test_key", "somehash")
        assert result is None
        assert not cache_file.exists()

    def test_cache_without_timestamp(self, tmp_path):
        """Test handling of cache entries without timestamp."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create cache file without timestamp
        cache_file = tmp_path / "test_key.json"
        data = {
            "content_hash": "hash123",
            "response_content": "test response",
        }
        with open(cache_file, "w") as f:
            json.dump(data, f)

        # Should treat as expired
        result = cache.get("test_key", "hash123")
        assert result is None

    def test_cache_file_read_error(self, tmp_path):
        """Test handling of file read errors."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create cache file
        cache.set("test_key", "hash123", "response")

        # Make file unreadable by deleting it and creating a directory with same name
        cache_file = tmp_path / "test_key.json"
        cache_file.unlink()
        cache_file.mkdir()

        # Should handle error gracefully
        result = cache.get("test_key", "hash123")
        assert result is None

    def test_cache_file_write_error(self, tmp_path):
        """Test handling of file write errors."""
        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()
        cache = ResponseCache(cache_dir=cache_dir)

        # Make directory read-only to cause write error
        cache_dir.chmod(0o444)

        # Should handle error gracefully (just log warning)
        try:
            cache.set("test_key", "hash123", "response")
            # Should not raise exception
        finally:
            # Restore permissions for cleanup
            cache_dir.chmod(0o755)

    def test_invalidate_nonexistent_file(self, tmp_path):
        """Test invalidating a cache key that doesn't exist."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Should not raise error
        cache.invalidate("nonexistent_key")

    def test_invalidate_error_handling(self, tmp_path):
        """Test error handling during invalidation."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create cache file
        cache.set("test_key", "hash123", "response")

        # Make directory read-only to cause permission error
        tmp_path.chmod(0o444)

        try:
            # Should handle error gracefully
            cache.invalidate("test_key")
        finally:
            # Restore permissions
            tmp_path.chmod(0o755)

    def test_clear_all_with_errors(self, tmp_path):
        """Test clear_all handling of file deletion errors."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create some cache files
        cache.set("key1", "hash1", "response1")
        cache.set("key2", "hash2", "response2")

        # Make one file undeletable
        cache_file = tmp_path / "key1.json"
        cache_file.chmod(0o444)
        tmp_path.chmod(0o555)  # Make directory read-only

        try:
            # Should still try to delete files even if some fail
            count = cache.clear_all()
            # Count may be less than total due to permission error
            assert count >= 0
        finally:
            # Restore permissions
            tmp_path.chmod(0o755)
            cache_file.chmod(0o644)

    def test_cache_with_invalid_timestamp_format(self, tmp_path):
        """Test handling of invalid timestamp format."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Create cache with invalid timestamp
        cache_file = tmp_path / "test_key.json"
        data = {
            "content_hash": "hash123",
            "response_content": "test response",
            "timestamp": "not-a-valid-timestamp",
            "ttl": 3600,
        }
        with open(cache_file, "w") as f:
            json.dump(data, f)

        # Should treat as expired due to invalid timestamp
        result = cache.get("test_key", "hash123")
        assert result is None

    def test_cache_invalidation_prompt_hash_mismatch(self, tmp_path):
        """Test cache invalidation when prompt hash changes."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Store with prompt_hash1
        cache.set("test_key", "content_hash", "old response", prompt_hash="prompt_hash1")

        # Try to retrieve with different prompt hash
        result = cache.get("test_key", "content_hash", prompt_hash="prompt_hash2")
        assert result is None

        # Cache file should be deleted
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 0

    def test_cache_hit_with_matching_prompt_hash(self, tmp_path):
        """Test cache hit when prompt hash matches."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Store with prompt hash
        cache.set("test_key", "content_hash", "test response", prompt_hash="prompt_hash1")

        # Retrieve with same prompt hash
        result = cache.get("test_key", "content_hash", prompt_hash="prompt_hash1")
        assert result == "test response"

    def test_cache_backward_compatible_no_prompt_hash(self, tmp_path):
        """Test cache works without prompt_hash for backward compatibility."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Store without prompt hash (old behavior)
        cache.set("test_key", "content_hash", "test response")

        # Retrieve without prompt hash
        result = cache.get("test_key", "content_hash")
        assert result == "test response"

        # Retrieve with prompt hash when cache has none should still work
        result = cache.get("test_key", "content_hash", prompt_hash=None)
        assert result == "test response"

    def test_cache_stores_prompt_hash_metadata(self, tmp_path):
        """Test that cache stores prompt_hash in metadata."""
        cache = ResponseCache(cache_dir=tmp_path)

        cache.set("test_key", "content_hash", "test response", prompt_hash="prompt_hash1")

        # Read cache file directly
        cache_file = tmp_path / "test_key.json"
        with open(cache_file, "r") as f:
            data = json.load(f)

        assert data["content_hash"] == "content_hash"
        assert data["prompt_hash"] == "prompt_hash1"
        assert data["response_content"] == "test response"

    def test_cache_invalidation_content_hash_mismatch_with_prompt_hash(self, tmp_path):
        """Test cache invalidates on content hash mismatch even with matching prompt hash."""
        cache = ResponseCache(cache_dir=tmp_path)

        # Store with both hashes
        cache.set("test_key", "content_hash1", "response", prompt_hash="prompt_hash1")

        # Try to retrieve with different content hash but same prompt hash
        result = cache.get("test_key", "content_hash2", prompt_hash="prompt_hash1")
        assert result is None

        # Cache file should be deleted
        cache_files = list(tmp_path.glob("*.json"))
        assert len(cache_files) == 0

    def test_cache_old_entry_accessed_with_new_prompt_hash(self, tmp_path):
        """Test old cache entry invalidated when accessed with prompt_hash.

        Verifies that cache entries without prompt_hash (old format) are
        invalidated when accessed with a new prompt_hash parameter.
        """
        cache = ResponseCache(cache_dir=tmp_path)

        # Store without prompt hash (simulate old cache entry)
        cache.set("test_key", "content_hash1", "old response")

        # Verify cache file exists and has no prompt_hash
        cache_file = tmp_path / "test_key.json"
        with open(cache_file, "r") as f:
            data = json.load(f)
        assert "prompt_hash" not in data

        # Try to retrieve with prompt_hash=None - should work
        result = cache.get("test_key", "content_hash1", prompt_hash=None)
        assert result == "old response"

        # Store again without prompt_hash
        cache.set("test_key", "content_hash1", "old response")

        # Try to retrieve with an actual prompt_hash - should invalidate
        # because old cache entries without prompt_hash don't match new prompt_hash
        result = cache.get("test_key", "content_hash1", prompt_hash="some_prompt_hash")
        assert result is None

    def test_cache_gitignore_creation(self, tmp_path):
        """Test that .gitignore is created in .drift directory."""
        drift_dir = tmp_path / ".drift"
        cache_dir = drift_dir / "cache"

        # Create cache (should trigger gitignore creation)
        ResponseCache(cache_dir=cache_dir, enabled=True)

        # Verify .gitignore exists in .drift directory
        gitignore_path = drift_dir / ".gitignore"
        assert gitignore_path.exists()

        # Verify content
        content = gitignore_path.read_text()
        assert "cache/" in content

    def test_cache_gitignore_not_overwritten(self, tmp_path):
        """Test that existing .gitignore is not overwritten."""
        drift_dir = tmp_path / ".drift"
        drift_dir.mkdir()
        cache_dir = drift_dir / "cache"

        # Create custom .gitignore
        gitignore_path = drift_dir / ".gitignore"
        custom_content = "# Custom content\nmy_files/\n"
        gitignore_path.write_text(custom_content)

        # Create cache (should NOT overwrite .gitignore)
        ResponseCache(cache_dir=cache_dir, enabled=True)

        # Verify .gitignore still has custom content
        content = gitignore_path.read_text()
        assert content == custom_content

    def test_cache_gitignore_not_created_outside_drift_dir(self, tmp_path):
        """Test that .gitignore is not created if cache dir is not in .drift."""
        cache_dir = tmp_path / "some_other_cache"

        # Create cache in non-.drift directory
        ResponseCache(cache_dir=cache_dir, enabled=True)

        # Verify no .gitignore was created in parent
        gitignore_path = tmp_path / ".gitignore"
        assert not gitignore_path.exists()
