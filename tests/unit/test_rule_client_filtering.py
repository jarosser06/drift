"""Tests for automatic rule client filtering based on validators.

This module tests that rules are automatically filtered by client type
based on the validators they use, without requiring explicit supported_clients
configuration.
"""

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    RuleDefinition,
    ValidationRule,
    ValidationRulesConfig,
)
from drift.core.analyzer import _get_supported_clients_from_rule
from drift.validation.validators import ValidatorRegistry


class TestRuleClientFiltering:
    """Tests for automatic client filtering based on validators."""

    def test_explicit_supported_clients_takes_precedence(self):
        """Test that explicit supported_clients in rule definition takes precedence."""
        registry = ValidatorRegistry()

        # Rule with explicit supported_clients
        rule_def = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            supported_clients=["claude-code"],
            validation_rules=ValidationRulesConfig(
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                rules=[
                    ValidationRule(
                        rule_type="core:file_exists",
                        file_path="test.txt",
                        description="Test",
                        failure_message="Fail",
                        expected_behavior="Pass",
                    )
                ],
            ),
        )

        supported = _get_supported_clients_from_rule(rule_def, registry, "claude-code")
        assert supported == ["claude-code"]

    def test_all_client_validators_return_none(self):
        """Test that validators supporting ALL clients return None (no filtering)."""
        registry = ValidatorRegistry()

        # Rule with only validators that support ALL clients
        rule_def = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                rules=[
                    ValidationRule(
                        rule_type="core:file_exists",
                        file_path="test.txt",
                        description="Test",
                        failure_message="Fail",
                        expected_behavior="Pass",
                    ),
                    ValidationRule(
                        rule_type="core:regex_match",
                        pattern="test",
                        description="Test",
                        failure_message="Fail",
                        expected_behavior="Pass",
                    ),
                ],
            ),
        )

        supported = _get_supported_clients_from_rule(rule_def, registry, "claude-code")
        assert supported is None  # Supports all clients

    def test_claude_specific_validator_returns_claude_code(self):
        """Test that Claude-specific validators return claude-code client."""
        registry = ValidatorRegistry()

        # Rule with Claude-specific validator
        rule_def = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                rules=[
                    ValidationRule(
                        rule_type="core:claude_skill_settings",
                        description="Test",
                        failure_message="Fail",
                        expected_behavior="Pass",
                    )
                ],
            ),
        )

        supported = _get_supported_clients_from_rule(rule_def, registry, "claude-code")
        assert supported == ["claude-code"]

    def test_mixed_validators_returns_none_if_any_support_all(self):
        """Test that mixing ALL and specific validators returns None (no filtering)."""
        registry = ValidatorRegistry()

        # Rule with both ALL and Claude-specific validators
        rule_def = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                rules=[
                    ValidationRule(
                        rule_type="core:file_exists",  # Supports ALL
                        file_path="test.txt",
                        description="Test",
                        failure_message="Fail",
                        expected_behavior="Pass",
                    ),
                    ValidationRule(
                        rule_type="core:claude_skill_settings",  # Claude only
                        description="Test",
                        failure_message="Fail",
                        expected_behavior="Pass",
                    ),
                ],
            ),
        )

        supported = _get_supported_clients_from_rule(rule_def, registry, "claude-code")
        assert supported is None  # One validator supports ALL, so no filtering

    def test_no_validation_rules_returns_none(self):
        """Test that rules without validation_rules support all clients."""
        registry = ValidatorRegistry()

        # LLM-based rule without validation rules
        rule_def = RuleDefinition(
            description="Test rule",
            scope="conversation_level",
            context="Test",
            requires_project_context=True,
        )

        supported = _get_supported_clients_from_rule(rule_def, registry, "claude-code")
        assert supported is None  # Supports all clients

    def test_empty_validation_rules_returns_none(self):
        """Test that rules with empty validation rules list support all clients."""
        registry = ValidatorRegistry()

        # Rule with empty validation rules
        rule_def = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                document_bundle=DocumentBundleConfig(
                    bundle_type="test",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.INDIVIDUAL,
                    resource_patterns=[],
                ),
                rules=[],
            ),
        )

        supported = _get_supported_clients_from_rule(rule_def, registry, "claude-code")
        assert supported is None  # Supports all clients
