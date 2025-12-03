"""Anthropic API LLM provider."""

import os
from typing import Any, Optional

from anthropic import Anthropic, AnthropicError

from drift.config.models import ModelConfig, ProviderConfig
from drift.providers.base import Provider


class AnthropicProvider(Provider):
    """Anthropic API LLM provider."""

    def __init__(
        self,
        provider_config: ProviderConfig,
        model_config: ModelConfig,
        cache: Optional[Any] = None,
    ):
        """Initialize Anthropic provider.

        -- provider_config: Provider configuration (API key env, etc)
        -- model_config: Model configuration
        -- cache: Optional response cache
        """
        super().__init__(provider_config, model_config, cache)
        self.client: Optional[Anthropic] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Anthropic client using API key from environment."""
        try:
            # Get API key environment variable name from provider params
            api_key_env = self.provider_config.params.get("api_key_env", "ANTHROPIC_API_KEY")
            api_key = os.getenv(api_key_env)

            if api_key:
                self.client = Anthropic(api_key=api_key)
            else:
                # Client is None if API key is not available
                self.client = None
        except Exception:
            # Client initialization might fail
            # We'll catch this in is_available()
            self.client = None

    def is_available(self) -> bool:
        """Check if Anthropic provider is available.

        Returns True if client is initialized with valid API key.
        """
        return self.client is not None

    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using Anthropic API (implementation).

        -- prompt: User prompt
        -- system_prompt: Optional system prompt

        Returns generated response text.

        Raises RuntimeError if provider is not available.
        Raises Exception if generation fails.
        """
        if not self.is_available():
            api_key_env = self.provider_config.params.get("api_key_env", "ANTHROPIC_API_KEY")
            raise RuntimeError(
                f"Anthropic provider is not available. "
                f"Please ensure {api_key_env} environment variable is set."
            )

        # Build messages for Claude models
        messages = [{"role": "user", "content": prompt}]

        # Build request parameters
        request_params = {
            "model": self.model_config.model_id,
            "max_tokens": self.model_config.params.get("max_tokens", 4096),
            "temperature": self.model_config.params.get("temperature", 0.0),
            "messages": messages,
        }

        # Add system prompt if provided
        if system_prompt:
            request_params["system"] = system_prompt

        # Add any additional model parameters (e.g., top_k, top_p)
        for key, value in self.model_config.params.items():
            if key not in ["max_tokens", "temperature"]:
                request_params[key] = value

        try:
            if self.client is None:
                raise ValueError("Anthropic client is not available")

            response = self.client.messages.create(**request_params)

            # Extract text from Claude response format
            if response.content and len(response.content) > 0:
                text_result: str = response.content[0].text
                return text_result
            else:
                raise ValueError("Unexpected response format from Anthropic API")

        except AnthropicError as e:
            raise Exception(f"Anthropic API error: {e}")
        except Exception as e:
            if "Anthropic API error" in str(e):
                raise
            raise Exception(f"Error calling Anthropic API: {e}")
