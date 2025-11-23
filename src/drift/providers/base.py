"""Base provider interface for LLM interactions."""

from abc import ABC, abstractmethod
from typing import Optional

from drift.config.models import ModelConfig, ProviderConfig


class Provider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, provider_config: ProviderConfig, model_config: ModelConfig):
        """Initialize the provider.

        Args:
            provider_config: Provider-specific configuration (region, auth, etc)
            model_config: Model-specific configuration (model_id, params)
        """
        self.provider_config = provider_config
        self.model_config = model_config

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response from the LLM.

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
