"""Tests for validator client type support.

This module tests the client type support functionality that allows validators
to declare which client types they support (ALL, CLAUDE, etc.).
"""

import pytest

from drift.config.models import ClientType
from drift.validation.validators import ValidatorRegistry


class TestValidatorClientSupport:
    """Tests for validator client type support."""

    def test_core_validators_support_all_clients(self):
        """Test that core validators support all clients by default."""
        registry = ValidatorRegistry()

        # All core validators should support ALL clients
        core_validators = [
            "core:file_exists",
            "core:file_exists",
            "core:regex_match",
            "core:list_match",
            "core:list_regex_match",
            "core:dependency_duplicate",
            "core:markdown_link",
        ]

        for rule_type in core_validators:
            clients = registry.get_supported_clients(rule_type)
            assert ClientType.ALL in clients, f"{rule_type} should support ALL clients"
            assert len(clients) == 1, f"{rule_type} should only list ALL"

    def test_claude_specific_validator_supports_claude(self):
        """Test that Claude-specific validators only support CLAUDE client."""
        registry = ValidatorRegistry()

        clients = registry.get_supported_clients("core:claude_skill_settings")
        assert ClientType.CLAUDE in clients
        assert ClientType.ALL not in clients
        assert len(clients) == 1

    def test_supports_client_with_all_type(self):
        """Test supports_client method for validators with ALL support."""
        registry = ValidatorRegistry()

        # Validators with ALL support should support any client type
        assert registry.supports_client("core:regex_match", ClientType.ALL)
        assert registry.supports_client("core:regex_match", ClientType.CLAUDE)

    def test_supports_client_with_specific_type(self):
        """Test supports_client method for client-specific validators."""
        registry = ValidatorRegistry()

        # Claude-specific validator should only support CLAUDE
        assert registry.supports_client("core:claude_skill_settings", ClientType.CLAUDE)
        assert not registry.supports_client("core:claude_skill_settings", ClientType.ALL)

    def test_get_supported_clients_invalid_type(self):
        """Test get_supported_clients raises error for invalid rule type."""
        registry = ValidatorRegistry()

        with pytest.raises(ValueError, match="Unsupported validation rule type"):
            # Use an actually invalid type
            registry.get_supported_clients("invalid:nonexistent_type")

    def test_supports_client_invalid_type(self):
        """Test supports_client returns False for invalid rule type."""
        registry = ValidatorRegistry()

        # Should return False for unknown rule types instead of raising
        assert not registry.supports_client("invalid:nonexistent_type", ClientType.CLAUDE)
