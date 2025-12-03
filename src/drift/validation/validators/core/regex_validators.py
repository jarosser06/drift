"""Validators for regex pattern matching."""

import re
from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class RegexMatchValidator(BaseValidator):
    """Validator for checking if file content matches a regex pattern."""

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if file content matches the specified regex pattern.

        -- rule: ValidationRule with file_path and pattern
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if pattern doesn't match, None if it does.
        """
        if not rule.file_path:
            raise ValueError("RegexMatchValidator requires rule.file_path")
        if not rule.pattern:
            raise ValueError("RegexMatchValidator requires rule.pattern")

        project_path = bundle.project_path
        file_path = project_path / rule.file_path

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                context=f"File not found: {rule.file_path}",
            )

        # Read file content
        try:
            content = file_path.read_text()
        except Exception as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                context=f"Failed to read file: {e}",
            )

        # Compile and search for pattern
        try:
            flags = rule.flags or 0
            pattern = re.compile(rule.pattern, flags)
            if pattern.search(content):
                # Pattern found - validation passes
                return None
            else:
                # Pattern not found - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    context=f"Pattern '{rule.pattern}' not found in file",
                )
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
        context: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure
        -- context: Additional context about the failure

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )
