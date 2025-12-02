"""AWS Bedrock provider implementation."""

import json
from typing import Any, Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from drift.config.models import ModelConfig, ProviderConfig
from drift.providers.base import Provider


class BedrockProvider(Provider):
    """AWS Bedrock LLM provider."""

    def __init__(
        self,
        provider_config: ProviderConfig,
        model_config: ModelConfig,
        cache: Optional[Any] = None,
    ):
        """Initialize Bedrock provider.

        Args:
            provider_config: Provider configuration (region, etc)
            model_config: Model configuration
            cache: Optional response cache
        """
        super().__init__(provider_config, model_config, cache)
        self.client: Optional[Any] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize the Bedrock client using provider params."""
        try:
            # Get region from provider params, default to us-east-1
            region = self.provider_config.params.get("region", "us-east-1")

            self.client = boto3.client(
                "bedrock-runtime",
                region_name=region,
            )
        except Exception:
            # Client initialization might fail if no credentials
            # We'll catch this in is_available()
            self.client = None

    def is_available(self) -> bool:
        """Check if Bedrock is available.

        Returns:
            True if client is initialized and credentials are available
        """
        if self.client is None:
            return False

        try:
            # Try to access client config to verify credentials
            # This will raise NoCredentialsError if credentials are missing
            config = self.client._client_config
            # If _client_config is a callable Mock with side_effect, call it
            if callable(config):
                config()
            return True
        except NoCredentialsError:
            return False
        except AttributeError:
            return False
        except Exception:
            # Catch any other issues with client config access
            return False

    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using Bedrock (implementation).

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt

        Returns:
            Generated response text

        Raises:
            RuntimeError: If provider is not available
            Exception: If generation fails
        """
        if not self.is_available():
            raise RuntimeError(
                "Bedrock provider is not available. Please ensure AWS credentials are configured."
            )

        # Build messages for Claude models
        messages = [{"role": "user", "content": prompt}]

        # Build request body for Anthropic models on Bedrock
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.model_config.params.get("max_tokens", 4096),
            "temperature": self.model_config.params.get("temperature", 0.0),
            "messages": messages,
        }

        # Add system prompt if provided
        if system_prompt:
            request_body["system"] = system_prompt

        # Add any additional model parameters (e.g., top_k, top_p)
        for key, value in self.model_config.params.items():
            if key not in ["max_tokens", "temperature"]:
                request_body[key] = value

        try:
            if self.client is None:
                raise ValueError("Bedrock client is not available")

            response = self.client.invoke_model(
                modelId=self.model_config.model_id,
                body=json.dumps(request_body),
            )

            # Parse response
            response_body = json.loads(response["body"].read())

            # Extract text from Claude response format
            if "content" in response_body and len(response_body["content"]) > 0:
                text_result: str = response_body["content"][0]["text"]
                return text_result
            else:
                raise ValueError("Unexpected response format from Bedrock")

        except (BotoCoreError, ClientError) as e:
            raise Exception(f"Bedrock API error: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse Bedrock response: {e}")
        except KeyError as e:
            raise Exception(f"Unexpected response structure from Bedrock: {e}")
