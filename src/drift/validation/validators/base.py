"""Base validator class for rule-based document validation."""

from abc import ABC, abstractmethod
from typing import Any, List, Literal, Optional

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
        """
        pass
