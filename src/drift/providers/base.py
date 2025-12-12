"""Base provider interface for LLM interactions."""

from abc import ABC, abstractmethod
from typing import Optional

from drift.cache import ResponseCache
from drift.config.models import ModelConfig, ProviderConfig


class Provider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(
        self,
        provider_config: ProviderConfig,
        model_config: ModelConfig,
        cache: Optional[ResponseCache] = None,
    ):
        """Initialize the provider.

        Args:
            provider_config: Provider-specific configuration (region, auth, etc)
            model_config: Model-specific configuration (model_id, params)
            cache: Optional response cache for LLM responses
        """
        self.provider_config = provider_config
        self.model_config = model_config
        self.cache = cache

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        cache_key: Optional[str] = None,
        content_hash: Optional[str] = None,
        prompt_hash: Optional[str] = None,
        drift_type: Optional[str] = None,
    ) -> str:
        """Generate a response from the LLM with optional caching.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            cache_key: Optional cache key (arbitrary string, e.g., file name)
            content_hash: Optional SHA-256 hash for cache validation
            prompt_hash: Optional SHA-256 hash of the prompt for cache invalidation
            drift_type: Optional drift type for cache metadata

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails
        """
        # Try cache if enabled and parameters provided
        if self.cache and cache_key and content_hash:
            cached_response = self.cache.get(cache_key, content_hash, prompt_hash)
            if cached_response is not None:
                return cached_response

        # Cache miss or disabled - call LLM
        response = self._generate_impl(prompt, system_prompt)

        # Store in cache if enabled and parameters provided
        if self.cache and cache_key and content_hash:
            self.cache.set(cache_key, content_hash, response, prompt_hash, drift_type)

        return response

    @abstractmethod
    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response from the LLM (implementation).

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt

        Returns:
            Generated text response

        Raises:
            Exception: If generation fails
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured.

        Returns:
            True if provider can be used, False otherwise
        """
        pass

    def get_model_id(self) -> str:
        """Get the model identifier.

        Returns:
            Model ID string
        """
        return self.model_config.model_id

    def get_provider_type(self) -> str:
        """Get the provider type.

        Returns:
            Provider type string
        """
        return self.provider_config.provider.value
