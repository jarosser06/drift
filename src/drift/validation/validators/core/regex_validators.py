"""Validators for regex pattern matching."""

import re
from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class RegexMatchValidator(BaseValidator):
    """Validator for checking if file content matches a regex pattern."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:regex_match"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "Pattern match validation failed"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "File should match the specified pattern"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if file content matches the specified regex pattern.

        -- rule: ValidationRule with optional file_path and required pattern
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if pattern doesn't match, None if it does.

        If file_path is provided, validates that specific file.
        If file_path is not provided, validates all files in the bundle.
        """
        if not rule.pattern:
            raise ValueError("RegexMatchValidator requires rule.pattern")

        # Compile pattern once
        try:
            flags = rule.flags or 0
            pattern = re.compile(rule.pattern, flags)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        # If file_path is specified, validate that specific file
        if rule.file_path:
            return self._validate_file(
                rule=rule,
                bundle=bundle,
                file_path=rule.file_path,
                pattern=pattern,
            )

        # Otherwise, validate all files in bundle
        failed_files = []
        for doc_file in bundle.files:
            result = self._validate_content(
                rule=rule,
                bundle=bundle,
                file_path=doc_file.relative_path,
                content=doc_file.content,
                pattern=pattern,
            )
            if result:
                failed_files.append(doc_file.relative_path)

        if failed_files:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=failed_files,
                context=f"Pattern '{rule.pattern}' not found in {len(failed_files)} file(s)",
            )

        return None

    def _validate_file(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_path: str,
        pattern: re.Pattern,
    ) -> Optional[DocumentRule]:
        """Validate a specific file by path.

        -- rule: ValidationRule
        -- bundle: Document bundle
        -- file_path: Relative path to file
        -- pattern: Compiled regex pattern

        Returns DocumentRule if validation fails, None if passes.
        """
        project_path = bundle.project_path
        full_path = project_path / file_path

        # Check if file exists
        if not full_path.exists() or not full_path.is_file():
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path],
                context=f"File not found: {file_path}",
            )

        # Read file content
        try:
            content = full_path.read_text()
        except Exception as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path],
                context=f"Failed to read file: {e}",
            )

        return self._validate_content(rule, bundle, file_path, content, pattern)

    def _validate_content(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_path: str,
        content: str,
        pattern: re.Pattern,
    ) -> Optional[DocumentRule]:
        """Validate content against pattern.

        -- rule: ValidationRule
        -- bundle: Document bundle
        -- file_path: Relative path for error reporting
        -- content: File content to validate
        -- pattern: Compiled regex pattern

        Returns DocumentRule if validation fails, None if passes.
        """
        if pattern.search(content):
            # Pattern found - validation passes
            return None
        else:
            # Pattern not found - validation fails
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path],
                context=f"Pattern '{rule.pattern}' not found in file",
            )

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
            observed_issue=self._get_failure_message(rule),
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )
