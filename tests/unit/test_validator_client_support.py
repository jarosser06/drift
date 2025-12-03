"""Tests for validator client type support.

This module tests the client type support functionality that allows validators
to declare which client types they support (ALL, CLAUDE, etc.).
"""

import pytest

from drift.config.models import ClientType, ValidationType
from drift.validation.validators import ValidatorRegistry


class TestValidatorClientSupport:
    """Tests for validator client type support."""

    def test_core_validators_support_all_clients(self):
        """Test that core validators support all clients by default."""
        registry = ValidatorRegistry()

        # All core validators should support ALL clients
        core_validators = [
            ValidationType.FILE_EXISTS,
            ValidationType.FILE_NOT_EXISTS,
            ValidationType.REGEX_MATCH,
            ValidationType.LIST_MATCH,
            ValidationType.LIST_REGEX_MATCH,
            ValidationType.DEPENDENCY_DUPLICATE,
            ValidationType.MARKDOWN_LINK,
        ]

        for rule_type in core_validators:
            clients = registry.get_supported_clients(rule_type)
            assert ClientType.ALL in clients, f"{rule_type} should support ALL clients"
            assert len(clients) == 1, f"{rule_type} should only list ALL"

    def test_claude_specific_validator_supports_claude(self):
        """Test that Claude-specific validators only support CLAUDE client."""
        registry = ValidatorRegistry()

        clients = registry.get_supported_clients(ValidationType.CLAUDE_SKILL_SETTINGS)
        assert ClientType.CLAUDE in clients
        assert ClientType.ALL not in clients
        assert len(clients) == 1

    def test_supports_client_with_all_type(self):
        """Test supports_client method for validators with ALL support."""
        registry = ValidatorRegistry()

        # Validators with ALL support should support any client type
        assert registry.supports_client(ValidationType.REGEX_MATCH, ClientType.ALL)
        assert registry.supports_client(ValidationType.REGEX_MATCH, ClientType.CLAUDE)

    def test_supports_client_with_specific_type(self):
        """Test supports_client method for client-specific validators."""
        registry = ValidatorRegistry()

        # Claude-specific validator should only support CLAUDE
        assert registry.supports_client(ValidationType.CLAUDE_SKILL_SETTINGS, ClientType.CLAUDE)
        assert not registry.supports_client(ValidationType.CLAUDE_SKILL_SETTINGS, ClientType.ALL)

    def test_get_supported_clients_invalid_type(self):
        """Test get_supported_clients raises error for invalid rule type."""
        registry = ValidatorRegistry()

        with pytest.raises(ValueError, match="Unsupported validation rule type"):
            # FILE_COUNT is not implemented yet
            registry.get_supported_clients(ValidationType.FILE_COUNT)

    def test_supports_client_invalid_type(self):
        """Test supports_client returns False for invalid rule type."""
        registry = ValidatorRegistry()

        # Should return False for unknown rule types instead of raising
        assert not registry.supports_client(ValidationType.FILE_COUNT, ClientType.CLAUDE)
