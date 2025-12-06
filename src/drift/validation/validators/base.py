"""Base validator class for rule-based document validation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Literal, Optional

from drift.config.models import ClientType, ValidationRule
from drift.core.types import DocumentBundle, DocumentRule


class BaseValidator(ABC):
    """Abstract base class for all validators."""

    def __init__(self, loader: Any = None):
        """Initialize validator.

        -- loader: Optional document loader for resource access
        """
        self.loader = loader

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
