"""Validators for rule-based document validation.

This package provides a modular structure for validators:
- base.py: BaseValidator abstract class
- core/: Core validators for generic validation tasks
- client/: Client-specific validators for tool/platform-specific validation
"""

from typing import Any, List, Optional

from drift.config.models import ClientType, ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator
from drift.validation.validators.client import (
    ClaudeMcpPermissionsValidator,
    ClaudeSettingsDuplicatesValidator,
    ClaudeSkillSettingsValidator,
)
from drift.validation.validators.core import (
    DependencyDuplicateValidator,
    FileExistsValidator,
    FileSizeValidator,
    JsonSchemaValidator,
    ListMatchValidator,
    ListRegexMatchValidator,
    MarkdownLinkValidator,
    RegexMatchValidator,
    TokenCountValidator,
    YamlFrontmatterValidator,
    YamlSchemaValidator,
)


class ValidatorRegistry:
    """Registry mapping rule types to validator implementations.

    The ValidatorRegistry provides a centralized system for managing validators
    and executing validation rules. Each validator is registered with its
    corresponding ValidationType and can be queried for its computation type
    (programmatic vs LLM-based).

    Usage Examples:

        Basic validation execution:
        >>> from drift.validation.validators import ValidatorRegistry
        >>> from drift.config.models import ValidationRule, ValidationType
        >>> registry = ValidatorRegistry()
        >>> rule = ValidationRule(
        ...     rule_type=ValidationType.FILE_EXISTS,
        ...     file_path="README.md",
        ...     description="Check README exists",
        ...     failure_message="README.md not found",
        ...     expected_behavior="README.md should exist"
        ... )
        >>> result = registry.execute_rule(rule, bundle)
        >>> if result is None:
        ...     print("Validation passed")

        Query computation type:
        >>> registry.get_computation_type(ValidationType.REGEX_MATCH)
        'programmatic'
        >>> registry.is_programmatic(ValidationType.MARKDOWN_LINK)
        True

        Filter programmatic validators for --no-llm mode:
        >>> programmatic_rules = [
        ...     rule for rule in rules
        ...     if registry.is_programmatic(rule.rule_type)
        ... ]

    Attributes:
        _validators: Dictionary mapping ValidationType to validator instances
    """

    def __init__(self, loader: Any = None) -> None:
        """Initialize registry with available validators.

        -- loader: Optional document loader for resource access
        """
        self._validators = {
            ValidationType.FILE_EXISTS: FileExistsValidator(loader),
            ValidationType.FILE_NOT_EXISTS: FileExistsValidator(loader),
            ValidationType.FILE_SIZE: FileSizeValidator(loader),
            ValidationType.TOKEN_COUNT: TokenCountValidator(loader),
            ValidationType.JSON_SCHEMA: JsonSchemaValidator(loader),
            ValidationType.YAML_SCHEMA: YamlSchemaValidator(loader),
            ValidationType.YAML_FRONTMATTER: YamlFrontmatterValidator(loader),
            ValidationType.REGEX_MATCH: RegexMatchValidator(loader),
            ValidationType.LIST_MATCH: ListMatchValidator(loader),
            ValidationType.LIST_REGEX_MATCH: ListRegexMatchValidator(loader),
            ValidationType.DEPENDENCY_DUPLICATE: DependencyDuplicateValidator(loader),
            ValidationType.MARKDOWN_LINK: MarkdownLinkValidator(loader),
            ValidationType.CLAUDE_SKILL_SETTINGS: ClaudeSkillSettingsValidator(loader),
            ValidationType.CLAUDE_SETTINGS_DUPLICATES: ClaudeSettingsDuplicatesValidator(loader),
            ValidationType.CLAUDE_MCP_PERMISSIONS: ClaudeMcpPermissionsValidator(loader),
        }

    def get_computation_type(self, rule_type: ValidationType) -> str:
        """Get the computation type for a given rule type.

        -- rule_type: The validation rule type

        Returns "programmatic" or "llm".

        Raises ValueError if rule type is not supported.
        """
        if rule_type not in self._validators:
            raise ValueError(f"Unsupported validation rule type: {rule_type}")

        validator = self._validators[rule_type]
        return validator.computation_type

    def is_programmatic(self, rule_type: ValidationType) -> bool:
        """Check if a rule type is programmatic (non-LLM).

        -- rule_type: The validation rule type

        Returns True if programmatic, False if LLM-based.
        """
        try:
            return self.get_computation_type(rule_type) == "programmatic"
        except ValueError:
            # Unknown rule type - default to LLM
            return False

    def get_supported_clients(self, rule_type: ValidationType) -> List[ClientType]:
        """Get the list of client types supported by a given rule type.

        -- rule_type: The validation rule type

        Returns list of ClientType enum values.

        Raises ValueError if rule type is not supported.
        """
        if rule_type not in self._validators:
            raise ValueError(f"Unsupported validation rule type: {rule_type}")

        validator = self._validators[rule_type]
        return validator.supported_clients

    def supports_client(self, rule_type: ValidationType, client_type: ClientType) -> bool:
        """Check if a rule type supports a specific client.

        -- rule_type: The validation rule type
        -- client_type: The client type to check

        Returns True if the validator supports the client, False otherwise.
        """
        try:
            supported = self.get_supported_clients(rule_type)
            return ClientType.ALL in supported or client_type in supported
        except ValueError:
            # Unknown rule type - default to not supported
            return False

    def execute_rule(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Execute a validation rule.

        -- rule: The validation rule to execute
        -- bundle: The document bundle to validate
        -- all_bundles: Optional list of all bundles

        Returns DocumentRule if validation fails, None if passes.

        Raises ValueError if rule type is not supported.
        """
        if rule.rule_type not in self._validators:
            raise ValueError(f"Unsupported validation rule type: {rule.rule_type}")

        validator = self._validators[rule.rule_type]
        result = validator.validate(rule, bundle, all_bundles)

        # Handle inverted rules (NOT_EXISTS, NOT_MATCH)
        if rule.rule_type == ValidationType.FILE_NOT_EXISTS:
            return self._invert_result(result, rule, bundle)

        return result

    def _invert_result(
        self,
        result: Optional[DocumentRule],
        rule: ValidationRule,
        bundle: DocumentBundle,
    ) -> Optional[DocumentRule]:
        """Invert validation result for NOT rules.

        -- result: Original validation result
        -- rule: The validation rule
        -- bundle: The document bundle

        Returns inverted result (None becomes DocumentRule, DocumentRule becomes None).
        """
        if result is None:
            # Original validation passed (file exists), but we want it NOT to exist
            # So this is a failure
            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[rule.file_path] if rule.file_path else [],
                observed_issue=rule.failure_message,
                expected_quality=rule.expected_behavior,
                rule_type="",  # Will be set by analyzer
                context=f"Validation rule: {rule.description}",
            )
        else:
            # Original validation failed (file doesn't exist), which is what we want
            # So this is a pass
            return None


__all__ = [
    "BaseValidator",
    "ClientType",
    "ClaudeMcpPermissionsValidator",
    "ClaudeSettingsDuplicatesValidator",
    "ClaudeSkillSettingsValidator",
    "DependencyDuplicateValidator",
    "FileExistsValidator",
    "FileSizeValidator",
    "JsonSchemaValidator",
    "ListMatchValidator",
    "ListRegexMatchValidator",
    "MarkdownLinkValidator",
    "RegexMatchValidator",
    "TokenCountValidator",
    "ValidatorRegistry",
    "YamlFrontmatterValidator",
    "YamlSchemaValidator",
]
