"""LLM response caching system for Drift.

This module provides file-based caching for LLM responses with content hash
validation and TTL support to reduce redundant API calls.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ResponseCache:
    """File-based cache for LLM responses with hash validation and TTL.

    Stores LLM response content along with content hashes to enable automatic
    cache invalidation when input content changes. Supports TTL for cache expiration.

    -- cache_dir: Directory to store cache files
    -- default_ttl: Default time-to-live in seconds (default: 86400 = 24 hours)
    -- enabled: Whether caching is enabled (default: True)
    """

    def __init__(
        self,
        cache_dir: Path,
        default_ttl: int = 86400,
        enabled: bool = True,
    ):
        """Initialize response cache.

        -- cache_dir: Directory to store cache files
        -- default_ttl: Default TTL in seconds (default: 86400 = 24 hours)
        -- enabled: Whether caching is enabled (default: True)
        """
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.enabled = enabled

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self._create_gitignore()

    def get(
        self,
        cache_key: str,
        content_hash: str,
        prompt_hash: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> Optional[str]:
        """Get cached response if valid.

        Checks if cache exists for the key, validates content and prompt hashes match,
        and verifies TTL hasn't expired.

        -- cache_key: Arbitrary cache key string (e.g., file name)
        -- content_hash: SHA-256 hash of the content being analyzed
        -- prompt_hash: Optional SHA-256 hash of the prompt (for invalidation on prompt changes)
        -- ttl: Optional TTL override in seconds

        Returns cached response content if valid, None otherwise.
        """
        if not self.enabled:
            return None

        cache_file = self._get_cache_file_path(cache_key)
        if not cache_file.exists():
            logger.debug(f"Cache miss: {cache_key} (file not found)")
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached_data = json.load(f)

            # Validate content hash
            if cached_data.get("content_hash") != content_hash:
                logger.debug(
                    f"Cache invalidated: {cache_key} (content hash mismatch: "
                    f"{cached_data.get('content_hash')[:8]}... != {content_hash[:8]}...)"
                )
                self.invalidate(cache_key)
                return None

            # Validate prompt hash if provided
            if prompt_hash is not None:
                cached_prompt_hash = cached_data.get("prompt_hash")
                if cached_prompt_hash != prompt_hash:
                    logger.debug(
                        f"Cache invalidated: {cache_key} (prompt hash mismatch: "
                        f"{cached_prompt_hash[:8] if cached_prompt_hash else 'none'}... != "
                        f"{prompt_hash[:8]}...)"
                    )
                    self.invalidate(cache_key)
                    return None

            # Check TTL
            effective_ttl = ttl if ttl is not None else self.default_ttl
            if self._is_expired(cached_data, effective_ttl):
                logger.debug(f"Cache expired: {cache_key}")
                self.invalidate(cache_key)
                return None

            logger.debug(f"Cache hit: {cache_key}")
            response_content: Optional[str] = cached_data.get("response_content")
            return response_content

        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Failed to read cache for {cache_key}: {e}")
            self.invalidate(cache_key)
            return None

    def set(
        self,
        cache_key: str,
        content_hash: str,
        response_content: str,
        prompt_hash: Optional[str] = None,
        drift_type: Optional[str] = None,
        ttl: Optional[int] = None,
    ) -> None:
        """Store response in cache.

        -- cache_key: Arbitrary cache key string (e.g., file name)
        -- content_hash: SHA-256 hash of the content being analyzed
        -- response_content: LLM response content to cache
        -- prompt_hash: Optional SHA-256 hash of the prompt (for invalidation on prompt changes)
        -- drift_type: Optional drift type for debugging
        -- ttl: Optional TTL override in seconds
        """
        if not self.enabled:
            return

        cache_file = self._get_cache_file_path(cache_key)

        cache_data = {
            "content_hash": content_hash,
            "response_content": response_content,
            "drift_type": drift_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "ttl": ttl if ttl is not None else self.default_ttl,
        }

        # Add prompt_hash if provided
        if prompt_hash is not None:
            cache_data["prompt_hash"] = prompt_hash

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
            logger.debug(f"Cached response for: {cache_key}")
        except OSError as e:
            logger.warning(f"Failed to write cache for {cache_key}: {e}")

    def invalidate(self, cache_key: str) -> None:
        """Remove cache entry.

        -- cache_key: Cache key to invalidate
        """
        if not self.enabled:
            return

        cache_file = self._get_cache_file_path(cache_key)
        try:
            if cache_file.exists():
                cache_file.unlink()
                logger.debug(f"Invalidated cache: {cache_key}")
        except OSError as e:
            logger.warning(f"Failed to invalidate cache for {cache_key}: {e}")

    def clear_all(self) -> int:
        """Clear all cache entries.

        Returns number of cache entries removed.
        """
        if not self.enabled:
            return 0

        count = 0
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    cache_file.unlink()
                    count += 1
                except OSError as e:
                    logger.warning(f"Failed to delete {cache_file}: {e}")
            logger.info(f"Cleared {count} cache entries")
        except OSError as e:
            logger.warning(f"Failed to clear cache directory: {e}")

        return count

    def _get_cache_file_path(self, cache_key: str) -> Path:
        """Get cache file path for a key.

        Sanitizes the cache key to create a safe filename.

        -- cache_key: Cache key string

        Returns path to cache file.
        """
        # Sanitize cache key for safe filename
        # Replace path separators and special characters
        safe_key = re.sub(r'[/\\:*?"<>|]', "_", cache_key)
        return self.cache_dir / f"{safe_key}.json"

    def _is_expired(self, cached_data: Dict[str, Any], ttl: int) -> bool:
        """Check if cached data is expired.

        -- cached_data: Cached data dictionary
        -- ttl: Time-to-live in seconds

        Returns True if expired, False otherwise.
        """
        try:
            timestamp_str = cached_data.get("timestamp")
            if not timestamp_str:
                return True

            timestamp = datetime.fromisoformat(timestamp_str)
            # Ensure timestamp is timezone-aware
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            age_seconds = (datetime.now(timezone.utc) - timestamp).total_seconds()
            return age_seconds > ttl

        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse cache timestamp: {e}")
            return True

    def _create_gitignore(self) -> None:
        """Create .gitignore in parent directory to exclude cache.

        Only creates the file if it doesn't already exist (preserves user customizations).
        Creates it in the .drift/ directory (parent of cache/), not in cache/ itself.
        """
        # Get parent directory (.drift/ if cache is .drift/cache/)
        drift_dir = self.cache_dir.parent

        # Only create .gitignore if this is a .drift directory structure
        if drift_dir.name == ".drift":
            gitignore_path = drift_dir / ".gitignore"

            # Don't overwrite existing .gitignore (preserve user customizations)
            if not gitignore_path.exists():
                gitignore_content = "# Drift cache directory\ncache/\n"
                try:
                    gitignore_path.write_text(gitignore_content, encoding="utf-8")
                    logger.debug(f"Created .gitignore in {drift_dir}")
                except OSError as e:
                    logger.warning(f"Failed to create .gitignore in {drift_dir}: {e}")

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """Compute SHA-256 hash of content.

        -- content: Content string to hash

        Returns SHA-256 hash as hex string.
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
