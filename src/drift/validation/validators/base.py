"""Base validator class for rule-based document validation.

VALIDATOR PARAMETER ARCHITECTURE
================================

Validators use a strict parameter architecture to ensure consistency:

**Core Rule Fields** (defined in ValidationRule model):
    - type: Validation type (required, e.g., "core:file_exists")
    - description: Human-readable description (required)
    - failure_message: Custom failure message (optional)
    - expected_behavior: Expected behavior description (optional)

**Validator-Specific Parameters** (under params dict):
    ALL validator-specific parameters MUST go under the `params` dictionary.
    This includes file paths, patterns, counts, sizes, flags, etc.

    Examples:
        params:
            file_path: "CLAUDE.md"
            pattern: "^```"
            flags: 8
            max_count: 300
            required_fields: ["name", "description"]

**Configuration Example**:
    # .drift_rules.yaml
    phases:
        - name: check_file_exists
          type: core:file_exists
          params:
              file_path: CLAUDE.md
          failure_message: "CLAUDE.md missing"
          expected_behavior: "Should have CLAUDE.md"

**Implementation Pattern**:
    All validators MUST read parameters from rule.params:

        def validate(self, rule, bundle, all_bundles=None):
            if not rule.params:
                raise ValueError("Validator requires params")

            param_value = rule.params.get("param_name")
            if not param_value:
                raise ValueError("Validator requires params.param_name")
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional

from drift.config.models import ClientType, ValidationRule
from drift.core.types import DocumentBundle, DocumentRule


class BaseValidator(ABC):
    """Abstract base class for all validators.

    Validators implement specific validation logic and should follow the
    parameter architecture documented in this module's docstring.
    """

    def __init__(self, loader: Any = None):
        """Initialize validator.

        -- loader: Optional document loader for resource access
        """
        self.loader = loader

    @property
    @abstractmethod
    def validation_type(self) -> str:
        """Return the namespaced validation type for this validator.

        Must be implemented by all validators to declare their validation type.
        Format: namespace:type (e.g., "core:file_exists", "security:vulnerability_scan")

        Returns namespaced validation type string.

        Raises NotImplementedError if not implemented by subclass.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement validation_type property"
        )

    @property
    @abstractmethod
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return the computation type for this validator.

        Must be implemented by all validators to explicitly declare whether
        they perform programmatic validation or require LLM computation.

        Returns either "programmatic" or "llm".

        Raises NotImplementedError if not implemented by subclass.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement computation_type property"
        )

    @property
    def supported_clients(self) -> List[ClientType]:
        """Return the list of client types this validator supports.

        Defaults to [ClientType.ALL] for validators that work with all clients.
        Override this property for client-specific validators.

        Returns list of ClientType enum values.
        """
        return [ClientType.ALL]

    @property
    def default_failure_message(self) -> str:
        """Return the default failure message template for this validator.

        This message is used when no custom failure_message is provided in the rule.
        The template can include {placeholder} variables that will be filled from
        failure_details.

        Override this property to provide a validator-specific default message.
        If not overridden, returns a generic message based on validation_type.

        Returns message template string with optional {placeholder} syntax.

        Examples:
            "File {file_path} does not exist"
            "Circular dependency detected: {circular_path}"
            "File exceeds maximum size of {max_size} bytes"
        """
        return f"Validation failed for {self.validation_type}"

    @property
    def default_expected_behavior(self) -> str:
        """Return the default expected behavior description for this validator.

        This description is used when no custom expected_behavior is provided in the rule.

        Override this property to provide a validator-specific default.
        If not overridden, returns a generic message based on validation_type.

        Returns expected behavior description string.
        """
        return f"Should pass {self.validation_type} validation"

    @abstractmethod
    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Execute validation rule.

        -- rule: The validation rule to execute
        -- bundle: The document bundle to validate
        -- all_bundles: Optional list of all bundles (for cross-bundle validation)

        Returns DocumentRule if validation fails, None if passes.

        Implementation Note:
            Validators should populate the failure_details field in DocumentRule
            when returning validation failures. This enables detailed, actionable
            violation messages. For example:

            return DocumentRule(
                ...
                observed_issue=self._format_message(
                    rule.failure_message,
                    {"circular_path": "A → B → C → A"}
                ),
                failure_details={"circular_path": "A → B → C → A"}
            )
        """
        pass

    def _get_failure_message(
        self, rule: ValidationRule, details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get the effective failure message (custom or default).

        Uses rule.failure_message if provided, otherwise falls back to
        the validator's default_failure_message. Formats the message with
        failure_details if provided.

        -- rule: ValidationRule with optional failure_message
        -- details: Optional dictionary of values for template placeholders

        Returns formatted failure message string.

        Examples:
            >>> # With custom message
            >>> rule = ValidationRule(failure_message="Custom: {path}")
            >>> self._get_failure_message(rule, {"path": "foo.txt"})
            'Custom: foo.txt'

            >>> # With default message
            >>> rule = ValidationRule(failure_message=None)
            >>> self._get_failure_message(rule, {"path": "foo.txt"})
            'File foo.txt does not exist'  # Uses validator default
        """
        template = rule.failure_message or self.default_failure_message
        return self._format_message(template, details)

    def _get_expected_behavior(self, rule: ValidationRule) -> str:
        """Get the effective expected behavior (custom or default).

        Uses rule.expected_behavior if provided, otherwise falls back to
        the validator's default_expected_behavior.

        -- rule: ValidationRule with optional expected_behavior

        Returns expected behavior description string.
        """
        return rule.expected_behavior or self.default_expected_behavior

    def _format_message(self, template: str, details: Optional[Dict[str, Any]] = None) -> str:
        """Format a message template with failure details.

        Supports simple {key} placeholders that are replaced with values from
        the details dictionary. If a placeholder is not found in details or
        details is None, the placeholder is left unchanged.

        -- template: Message template with {placeholder} syntax
        -- details: Optional dictionary of values to interpolate

        Returns formatted message string.

        Examples:
            >>> self._format_message(
            ...     "Circular dependency: {circular_path}",
            ...     {"circular_path": "A → B → A"}
            ... )
            'Circular dependency: A → B → A'

            >>> self._format_message(
            ...     "Depth {actual_depth} exceeds max {max_depth}",
            ...     {"actual_depth": 5, "max_depth": 3}
            ... )
            'Depth 5 exceeds max 3'
        """
        if not details:
            return template

        # Use safe formatting - only replace placeholders that exist in details
        formatted = template
        for key, value in details.items():
            placeholder = f"{{{key}}}"
            if placeholder in formatted:
                formatted = formatted.replace(placeholder, str(value))

        return formatted
