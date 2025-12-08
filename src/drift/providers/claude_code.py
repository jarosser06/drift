"""Claude Code CLI provider implementation."""

import json
import logging
import shutil
import subprocess
from typing import Any, Optional

from drift.config.models import ModelConfig, ProviderConfig
from drift.providers.base import Provider

logger = logging.getLogger(__name__)


class ClaudeCodeProvider(Provider):
    """Claude Code CLI LLM provider.

    Uses the `claude` CLI tool in headless mode to interact with Claude models.
    This provider requires Claude Code to be installed and available in PATH.
    """

    # Map friendly model names to Claude Code model identifiers
    MODEL_MAP = {
        "sonnet": "sonnet",
        "opus": "opus",
        "haiku": "haiku",
    }

    def __init__(
        self,
        provider_config: ProviderConfig,
        model_config: ModelConfig,
        cache: Optional[Any] = None,
    ):
        """Initialize Claude Code provider.

        -- provider_config: Provider configuration
        -- model_config: Model configuration
        -- cache: Optional response cache
        """
        super().__init__(provider_config, model_config, cache)
        self._available: Optional[bool] = None
        self._check_availability()

    def _check_availability(self) -> None:
        """Check if Claude Code CLI is available.

        Sets self._available to True if claude command exists and is executable.
        """
        try:
            # Check if claude command exists
            claude_path = shutil.which("claude")
            if claude_path is None:
                logger.debug("Claude Code CLI not found in PATH")
                self._available = False
                return

            # Try to get version to verify it works
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                logger.debug(f"Claude Code CLI found: {result.stdout.strip()}")
                self._available = True
            else:
                logger.debug(f"Claude Code CLI check failed: {result.stderr}")
                self._available = False

        except subprocess.TimeoutExpired:
            logger.debug("Claude Code CLI version check timed out")
            self._available = False
        except Exception as e:
            logger.debug(f"Error checking Claude Code availability: {e}")
            self._available = False

    def is_available(self) -> bool:
        """Check if Claude Code provider is available.

        Returns True if claude CLI is installed and executable.
        """
        return self._available is True

    def _get_model_name(self) -> str:
        """Get the Claude Code model name from config.

        Returns model name suitable for claude CLI (sonnet, opus, or haiku).
        """
        model_id = self.model_config.model_id

        # Check if it's already a simple model name
        if model_id in self.MODEL_MAP:
            return self.MODEL_MAP[model_id]

        # Try to extract from full model ID (e.g., "claude-sonnet-4-5-20250929")
        model_lower = model_id.lower()
        if "sonnet" in model_lower:
            return "sonnet"
        elif "opus" in model_lower:
            return "opus"
        elif "haiku" in model_lower:
            return "haiku"

        # Default to sonnet if we can't determine
        logger.warning(
            f"Could not determine Claude Code model from '{model_id}', defaulting to sonnet"
        )
        return "sonnet"

    def _generate_impl(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using Claude Code CLI (implementation).

        -- prompt: User prompt
        -- system_prompt: Optional system prompt (not used by Claude Code CLI)

        Returns generated response text.

        Raises RuntimeError if provider is not available.
        Raises Exception if generation fails.
        """
        if not self.is_available():
            raise RuntimeError(
                "Claude Code provider is not available. "
                "Please ensure the 'claude' CLI is installed and in your PATH. "
                "Visit https://claude.ai/download for installation instructions."
            )

        # Get model name for CLI
        model_name = self._get_model_name()

        # Get timeout from params (default 120 seconds)
        timeout = self.model_config.params.get("timeout", 120)

        # Build command
        # Use -p for headless prompt mode and --output-format json for structured output
        # Use --mcp-config with empty config and --strict-mcp-config to disable MCP servers
        cmd = [
            "claude",
            "-p",
            prompt,
            "--model",
            model_name,
            "--output-format",
            "json",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--strict-mcp-config",
        ]

        # Add system prompt if provided (if claude CLI supports it)
        # Note: The current claude CLI may not support system prompts directly
        # We'll prepend it to the user prompt as a workaround
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
            cmd[2] = full_prompt

        try:
            logger.debug(f"Executing Claude Code CLI with model: {model_name}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or result.stdout.strip()
                raise Exception(f"Claude Code CLI error: {error_msg}")

            # Parse JSON response
            try:
                response_data = json.loads(result.stdout)

                # Extract text from response
                # Claude Code JSON output structure uses "result" field
                if isinstance(response_data, dict):
                    # Primary field for Claude Code CLI JSON output
                    if "result" in response_data:
                        result_value = response_data["result"]
                        if isinstance(result_value, str):
                            return result_value
                        else:
                            raise ValueError(
                                f"Expected 'result' field to be string, "
                                f"got {type(result_value)}"
                            )

                    # Fallback: try other common field names
                    text = (
                        response_data.get("response")
                        or response_data.get("content")
                        or response_data.get("text")
                        or response_data.get("message")
                    )

                    if text:
                        return str(text)

                    # If no known field found, raise an error
                    available_fields = list(response_data.keys())
                    raise ValueError(
                        f"Could not extract response text from Claude "
                        f"Code output. Expected 'result' field but got: "
                        f"{available_fields}"
                    )

                elif isinstance(response_data, str):
                    return response_data

                else:
                    raise ValueError(f"Unexpected response type: {type(response_data)}")

            except json.JSONDecodeError:
                # If JSON parsing fails, return raw output
                # This handles cases where --output-format json isn't supported
                logger.warning("Could not parse JSON from Claude Code, using raw output")
                return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise Exception(
                f"Claude Code CLI timed out after {timeout} seconds. "
                "You can increase timeout with 'params.timeout' in model config."
            )
        except FileNotFoundError:
            raise Exception(
                "Claude Code CLI not found. "
                "Please ensure 'claude' is installed and in your PATH."
            )
        except Exception as e:
            if "Claude Code CLI error" in str(e) or "Claude Code CLI timed out" in str(e):
                raise
            raise Exception(f"Error calling Claude Code CLI: {e}")
