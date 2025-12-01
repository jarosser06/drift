"""Mock provider for testing without real LLM calls."""

from drift.providers.base import Provider


class MockProvider(Provider):
    """Mock provider that returns canned responses for testing."""

    def __init__(self, provider_config=None, model_config=None):
        """Initialize mock provider.

        Args:
            provider_config: Provider configuration (ignored)
            model_config: Model configuration (ignored)
        """
        self.provider_config = provider_config
        self.model_config = model_config
        self.call_count = 0
        self.calls = []
        # Return empty JSON array by default (no rules)
        self.response = "[]"

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate a mock response.

        Args:
            prompt: The prompt to generate from
            **kwargs: Additional generation parameters

        Returns:
            Mock response (JSON array of rules)
        """
        self.call_count += 1
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        return self.response

    def is_available(self) -> bool:
        """Check if provider is available.

        Returns:
            Always True for mock provider
        """
        return True

    def set_response(self, response: str):
        """Set the response to return from generate().

        Args:
            response: Response string to return
        """
        self.response = response

    def reset(self):
        """Reset call tracking."""
        self.call_count = 0
        self.calls = []
        self.response = "[]"
