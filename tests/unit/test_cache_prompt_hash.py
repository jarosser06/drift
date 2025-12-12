"""Integration tests for cache prompt hash validation."""

from drift.cache import ResponseCache
from drift.config.models import ModelConfig, ProviderConfig, ProviderType
from drift.providers.base import Provider


class MockProvider(Provider):
    """Mock provider for testing cache behavior."""

    def __init__(self, provider_config, model_config, cache=None):
        """Initialize mock provider."""
        super().__init__(provider_config, model_config, cache)
        self.call_count = 0
        self.responses = []

    def _generate_impl(self, prompt, system_prompt=None):
        """Generate mock responses and track calls."""
        self.call_count += 1
        response = f"Response {self.call_count}: {prompt[:20]}..."
        self.responses.append(response)
        return response

    def is_available(self):
        """Check if provider is available (always True for testing)."""
        return True


class TestCachePromptHashIntegration:
    """Integration tests for cache with prompt hash validation."""

    def test_cache_invalidates_on_prompt_change(self, tmp_path):
        """Test that cache invalidates when prompt changes but content stays same."""
        cache_dir = tmp_path / "cache"
        cache = ResponseCache(cache_dir=cache_dir)

        provider_config = ProviderConfig(provider=ProviderType.ANTHROPIC)
        model_config = ModelConfig(model_id="test-model", provider=ProviderType.ANTHROPIC)
        provider = MockProvider(provider_config, model_config, cache)

        # First call with original prompt
        prompt1 = "Analyze this code for issues"
        content = "def foo(): pass"
        content_hash = ResponseCache.compute_content_hash(content)
        prompt_hash1 = ResponseCache.compute_content_hash(prompt1)

        response1 = provider.generate(
            prompt1,
            cache_key="test_file.py",
            content_hash=content_hash,
            prompt_hash=prompt_hash1,
        )

        assert provider.call_count == 1
        assert response1.startswith("Response 1:")

        # Second call with same prompt and content - should hit cache
        response2 = provider.generate(
            prompt1,
            cache_key="test_file.py",
            content_hash=content_hash,
            prompt_hash=prompt_hash1,
        )

        assert provider.call_count == 1  # No new call
        assert response2 == response1  # Same cached response

        # Third call with DIFFERENT prompt but SAME content - should miss cache
        prompt2 = "Check this code for bugs"
        prompt_hash2 = ResponseCache.compute_content_hash(prompt2)

        response3 = provider.generate(
            prompt2,
            cache_key="test_file.py",
            content_hash=content_hash,
            prompt_hash=prompt_hash2,
        )

        assert provider.call_count == 2  # New call made
        assert response3.startswith("Response 2:")
        assert response3 != response1  # Different response

    def test_cache_invalidates_on_content_change(self, tmp_path):
        """Test that cache still invalidates on content change."""
        cache_dir = tmp_path / "cache"
        cache = ResponseCache(cache_dir=cache_dir)

        provider_config = ProviderConfig(provider=ProviderType.ANTHROPIC)
        model_config = ModelConfig(model_id="test-model", provider=ProviderType.ANTHROPIC)
        provider = MockProvider(provider_config, model_config, cache)

        # First call with original content
        prompt = "Analyze this code"
        prompt_hash = ResponseCache.compute_content_hash(prompt)
        content1 = "def foo(): pass"
        content_hash1 = ResponseCache.compute_content_hash(content1)

        response1 = provider.generate(
            prompt,
            cache_key="test_file.py",
            content_hash=content_hash1,
            prompt_hash=prompt_hash,
        )

        assert provider.call_count == 1

        # Second call with SAME prompt but DIFFERENT content - should miss cache
        content2 = "def bar(): return 42"
        content_hash2 = ResponseCache.compute_content_hash(content2)

        response2 = provider.generate(
            prompt,
            cache_key="test_file.py",
            content_hash=content_hash2,
            prompt_hash=prompt_hash,
        )

        assert provider.call_count == 2  # New call made
        assert response2 != response1  # Different response

    def test_cache_hits_when_nothing_changes(self, tmp_path):
        """Test that cache hits when both prompt and content stay same."""
        cache_dir = tmp_path / "cache"
        cache = ResponseCache(cache_dir=cache_dir)

        provider_config = ProviderConfig(provider=ProviderType.ANTHROPIC)
        model_config = ModelConfig(model_id="test-model", provider=ProviderType.ANTHROPIC)
        provider = MockProvider(provider_config, model_config, cache)

        prompt = "Analyze this code"
        content = "def foo(): pass"
        content_hash = ResponseCache.compute_content_hash(content)
        prompt_hash = ResponseCache.compute_content_hash(prompt)

        # First call
        response1 = provider.generate(
            prompt,
            cache_key="test_file.py",
            content_hash=content_hash,
            prompt_hash=prompt_hash,
        )

        assert provider.call_count == 1

        # Multiple subsequent calls - all should hit cache
        for _ in range(5):
            response = provider.generate(
                prompt,
                cache_key="test_file.py",
                content_hash=content_hash,
                prompt_hash=prompt_hash,
            )
            assert response == response1
            assert provider.call_count == 1  # No new calls

    def test_cache_backward_compatible_without_prompt_hash(self, tmp_path):
        """Test that cache works without prompt_hash for backward compatibility."""
        cache_dir = tmp_path / "cache"
        cache = ResponseCache(cache_dir=cache_dir)

        provider_config = ProviderConfig(provider=ProviderType.ANTHROPIC)
        model_config = ModelConfig(model_id="test-model", provider=ProviderType.ANTHROPIC)
        provider = MockProvider(provider_config, model_config, cache)

        prompt = "Analyze this code"
        content = "def foo(): pass"
        content_hash = ResponseCache.compute_content_hash(content)

        # First call without prompt_hash
        response1 = provider.generate(
            prompt,
            cache_key="test_file.py",
            content_hash=content_hash,
        )

        assert provider.call_count == 1

        # Second call without prompt_hash - should hit cache
        response2 = provider.generate(
            prompt,
            cache_key="test_file.py",
            content_hash=content_hash,
        )

        assert provider.call_count == 1  # No new call
        assert response2 == response1
