"""Integration tests for Claude Code provider with DriftAnalyzer."""

from unittest.mock import Mock, patch

import pytest

from drift.config.models import DriftConfig, ModelConfig, ProviderConfig, ProviderType
from drift.core.analyzer import DriftAnalyzer
from drift.providers.claude_code import ClaudeCodeProvider


@pytest.fixture
def temp_project_path(tmp_path):
    """Create a temporary project directory."""
    return tmp_path


@pytest.fixture
def claude_code_config():
    """Create a minimal config with Claude Code provider."""
    return DriftConfig(
        providers={
            "claude-code": ProviderConfig(
                provider=ProviderType.CLAUDE_CODE,
                params={},
            ),
        },
        models={
            "claude-sonnet": ModelConfig(
                provider="claude-code",
                model_id="sonnet",
                params={"max_tokens": 4096, "temperature": 0.0},
            ),
        },
        default_model="claude-sonnet",
        agent_tools={
            "claude-code": {
                "conversation_path": "~/.claude/projects/",
                "enabled": True,
            },
        },
        rule_definitions={},
    )


class TestClaudeCodeIntegration:
    """Test Claude Code provider integration with DriftAnalyzer."""

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_analyzer_initializes_claude_code_provider(
        self, mock_run, mock_which, claude_code_config, temp_project_path
    ):
        """Test that DriftAnalyzer properly initializes Claude Code provider."""
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        analyzer = DriftAnalyzer(config=claude_code_config, project_path=temp_project_path)

        # Check that provider was created
        assert "claude-sonnet" in analyzer.providers
        provider = analyzer.providers["claude-sonnet"]
        assert isinstance(provider, ClaudeCodeProvider)
        assert provider.is_available()

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_analyzer_with_unavailable_claude_code(
        self, mock_run, mock_which, claude_code_config, temp_project_path
    ):
        """Test analyzer initialization when Claude Code CLI is not available."""
        mock_which.return_value = None

        analyzer = DriftAnalyzer(config=claude_code_config, project_path=temp_project_path)

        # Provider should be created but not available
        assert "claude-sonnet" in analyzer.providers
        provider = analyzer.providers["claude-sonnet"]
        assert isinstance(provider, ClaudeCodeProvider)
        assert not provider.is_available()

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_analyzer_with_multiple_providers(
        self, mock_run, mock_which, temp_project_path, monkeypatch
    ):
        """Test analyzer with both Claude Code and Anthropic API providers."""
        # Set mock API key for Anthropic
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Mock Claude Code availability
        mock_which.return_value = "/usr/local/bin/claude"
        mock_run.return_value = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")

        # Create config with multiple providers
        config = DriftConfig(
            providers={
                "anthropic": ProviderConfig(
                    provider=ProviderType.ANTHROPIC,
                    params={"api_key_env": "ANTHROPIC_API_KEY"},
                ),
                "claude-code": ProviderConfig(
                    provider=ProviderType.CLAUDE_CODE,
                    params={},
                ),
            },
            models={
                "api-sonnet": ModelConfig(
                    provider="anthropic",
                    model_id="claude-sonnet-4-5-20250929",
                    params={},
                ),
                "cli-sonnet": ModelConfig(
                    provider="claude-code",
                    model_id="sonnet",
                    params={},
                ),
            },
            default_model="api-sonnet",
            agent_tools={
                "claude-code": {
                    "conversation_path": "~/.claude/projects/",
                    "enabled": True,
                },
            },
            rule_definitions={},
        )

        analyzer = DriftAnalyzer(config=config, project_path=temp_project_path)

        # Both providers should be initialized
        assert "api-sonnet" in analyzer.providers
        assert "cli-sonnet" in analyzer.providers

        # Check provider types
        from drift.providers.anthropic import AnthropicProvider

        assert isinstance(analyzer.providers["api-sonnet"], AnthropicProvider)
        assert isinstance(analyzer.providers["cli-sonnet"], ClaudeCodeProvider)

    @patch("drift.providers.claude_code.shutil.which")
    @patch("drift.providers.claude_code.subprocess.run")
    def test_analyzer_uses_claude_code_for_generation(
        self, mock_run, mock_which, claude_code_config, temp_project_path
    ):
        """Test that analyzer can use Claude Code provider for generation."""
        # Mock CLI availability
        mock_which.return_value = "/usr/local/bin/claude"
        version_result = Mock(returncode=0, stdout="claude version 1.0.0\n", stderr="")
        generate_result = Mock(
            returncode=0,
            stdout='{"response": "Analysis result"}',
            stderr="",
        )
        mock_run.side_effect = [version_result, generate_result]

        analyzer = DriftAnalyzer(config=claude_code_config, project_path=temp_project_path)

        # Get the provider
        provider = analyzer.providers["claude-sonnet"]

        # Test generation
        result = provider.generate("Test prompt")

        assert result == "Analysis result"
        assert mock_run.call_count == 2  # version check + generation

    @patch("drift.providers.claude_code.shutil.which")
    def test_analyzer_model_mapping(self, mock_which, temp_project_path):
        """Test that analyzer correctly maps model names."""
        mock_which.return_value = None  # Don't need CLI for this test

        # Create config with different model names
        config = DriftConfig(
            providers={
                "claude-code": ProviderConfig(
                    provider=ProviderType.CLAUDE_CODE,
                    params={},
                ),
            },
            models={
                "haiku": ModelConfig(
                    provider="claude-code",
                    model_id="haiku",
                    params={},
                ),
                "opus": ModelConfig(
                    provider="claude-code",
                    model_id="opus",
                    params={},
                ),
                "full-model-id": ModelConfig(
                    provider="claude-code",
                    model_id="claude-sonnet-4-5-20250929",
                    params={},
                ),
            },
            default_model="haiku",
            agent_tools={
                "claude-code": {
                    "conversation_path": "~/.claude/projects/",
                    "enabled": True,
                },
            },
            rule_definitions={},
        )

        analyzer = DriftAnalyzer(config=config, project_path=temp_project_path)

        # All models should be initialized
        assert len(analyzer.providers) == 3
        assert all(isinstance(p, ClaudeCodeProvider) for p in analyzer.providers.values())
