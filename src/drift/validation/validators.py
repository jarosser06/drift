"""Validators for rule-based document validation."""

from abc import ABC, abstractmethod
from typing import List, Optional

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentLearning


class BaseValidator(ABC):
    """Abstract base class for all validators."""

    @abstractmethod
    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentLearning]:
        """Execute validation rule.

        Args:
            rule: The validation rule to execute
            bundle: The document bundle to validate
            all_bundles: Optional list of all bundles (for cross-bundle validation)

        Returns:
            DocumentLearning if validation fails, None if passes
        """
        pass


class FileExistsValidator(BaseValidator):
    """Validator for checking file existence."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentLearning]:
        """Check if specified file(s) exist.

        Args:
            rule: ValidationRule with file_path (supports glob patterns)
            bundle: Document bundle being validated
            all_bundles: Not used for this validator

        Returns:
            DocumentLearning if file doesn't exist, None if it does
        """
        if not rule.file_path:
            raise ValueError("FileExistsValidator requires rule.file_path")

        project_path = bundle.project_path

        # Check if file_path contains glob patterns
        if "*" in rule.file_path or "?" in rule.file_path:
            # Glob pattern - check if any files match
            matches = list(project_path.glob(rule.file_path))
            matching_files = [m for m in matches if m.is_file()]

            if matching_files:
                # Files exist - validation passes
                return None
            else:
                # No matching files - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                )
        else:
            # Specific file path
            file_path = project_path / rule.file_path

            if file_path.exists() and file_path.is_file():
                # File exists - validation passes
                return None
            else:
                # File doesn't exist - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                )

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
    ) -> DocumentLearning:
        """Create a DocumentLearning for a validation failure.

        Args:
            rule: The validation rule that failed
            bundle: The document bundle being validated
            file_paths: List of file paths involved in the failure

        Returns:
            DocumentLearning representing the failure
        """
        return DocumentLearning(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            learning_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )


class ValidatorRegistry:
    """Registry mapping rule types to validator implementations."""

    def __init__(self) -> None:
        """Initialize registry with available validators."""
        self._validators = {
            ValidationType.FILE_EXISTS: FileExistsValidator(),
            ValidationType.FILE_NOT_EXISTS: FileExistsValidator(),
        }

    def execute_rule(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentLearning]:
        """Execute a validation rule.

        Args:
            rule: The validation rule to execute
            bundle: The document bundle to validate
            all_bundles: Optional list of all bundles

        Returns:
            DocumentLearning if validation fails, None if passes

        Raises:
            ValueError: If rule type is not supported
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
        result: Optional[DocumentLearning],
        rule: ValidationRule,
        bundle: DocumentBundle,
    ) -> Optional[DocumentLearning]:
        """Invert validation result for NOT rules.

        Args:
            result: Original validation result
            rule: The validation rule
            bundle: The document bundle

        Returns:
            Inverted result (None becomes DocumentLearning, DocumentLearning becomes None)
        """
        if result is None:
            # Original validation passed (file exists), but we want it NOT to exist
            # So this is a failure
            return DocumentLearning(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[rule.file_path] if rule.file_path else [],
                observed_issue=rule.failure_message,
                expected_quality=rule.expected_behavior,
                learning_type="",  # Will be set by analyzer
                context=f"Validation rule: {rule.description}",
            )
        else:
            # Original validation failed (file doesn't exist), which is what we want
            # So this is a pass
            return None
