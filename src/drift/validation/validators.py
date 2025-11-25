"""Validators for rule-based document validation."""

from abc import ABC, abstractmethod
from typing import Any, List, Optional

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentLearning
from drift.validation.params import ParamResolver


class BaseValidator(ABC):
    """Abstract base class for all validators."""

    def __init__(self, loader: Any = None):
        """Initialize validator.

        Args:
            loader: Optional document loader for resource access
        """
        self.loader = loader

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


class ListMatchValidator(BaseValidator):
    """Validator for checking if list items match expected values."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentLearning]:
        """Check if list items match expected values.

        Expected params:
            - items: List to check (can be string_list or resource_list)
            - target: List to compare against (can be string_list, resource_list, or file_content)
            - match_mode: "all_in", "none_in", "exact" (default: "all_in")

        Args:
            rule: ValidationRule with params
            bundle: Document bundle being validated
            all_bundles: Not used for this validator

        Returns:
            DocumentLearning if validation fails, None if passes
        """
        resolver = ParamResolver(bundle, self.loader)

        try:
            # Resolve parameters
            items_spec = rule.params.get("items")
            target_spec = rule.params.get("target")
            match_mode = rule.params.get("match_mode", "all_in")

            if not items_spec or not target_spec:
                raise ValueError("ListMatchValidator requires 'items' and 'target' params")

            items = resolver.resolve(items_spec)
            target = resolver.resolve(target_spec)

            # Ensure both are lists
            if not isinstance(items, list):
                items = [items]
            if not isinstance(target, list):
                target = [target]

            # Perform match based on mode
            if match_mode == "all_in":
                # All items must be in target
                missing = [item for item in items if item not in target]
                if missing:
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Items not found in target: {', '.join(missing)}",
                    )
            elif match_mode == "none_in":
                # No items should be in target
                found = [item for item in items if item in target]
                if found:
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Items found in target but should not be: {', '.join(found)}",
                    )
            elif match_mode == "exact":
                # Lists must be exactly the same (order-independent)
                if set(items) != set(target):
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Lists do not match exactly. Items: {items}, Target: {target}",
                    )
            else:
                raise ValueError(f"Unknown match_mode: {match_mode}")

            return None

        except Exception as e:
            raise ValueError(f"ListMatchValidator error: {e}")

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        context: str,
    ) -> DocumentLearning:
        """Create a DocumentLearning for a validation failure."""
        return DocumentLearning(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[f.relative_path for f in bundle.files],
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            learning_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class ListRegexMatchValidator(BaseValidator):
    """Validator for checking if list items match regex patterns in files."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentLearning]:
        """Check if list items match regex patterns in target files.

        Expected params:
            - items: List to check (can be string_list or resource_list)
            - file_path: File path to search in (can be string or file_content)
            - pattern: Regex pattern to extract matches from file
            - match_mode: "all_in", "none_in" (default: "all_in")

        Args:
            rule: ValidationRule with params
            bundle: Document bundle being validated
            all_bundles: Not used for this validator

        Returns:
            DocumentLearning if validation fails, None if passes
        """
        resolver = ParamResolver(bundle, self.loader)

        try:
            # Resolve parameters
            items_spec = rule.params.get("items")
            file_path_spec = rule.params.get("file_path")
            pattern_spec = rule.params.get("pattern")
            match_mode = rule.params.get("match_mode", "all_in")

            if not items_spec or not file_path_spec or not pattern_spec:
                raise ValueError(
                    "ListRegexMatchValidator requires 'items', 'file_path', and 'pattern' params"
                )

            items = resolver.resolve(items_spec)
            pattern = resolver.resolve(pattern_spec)

            # Resolve file content
            if isinstance(file_path_spec, dict) and file_path_spec.get("type") == "file_content":
                file_content = resolver.resolve(file_path_spec)
            else:
                # Legacy: file_path is a string path
                file_path = resolver.resolve({"type": "string", "value": file_path_spec})
                file_content = resolver.resolve({"type": "file_content", "value": file_path})

            # Ensure items is a list
            if not isinstance(items, list):
                items = [items]

            # Extract matches from file content using pattern
            matches = pattern.findall(file_content)
            matches = list(set(matches))  # Remove duplicates

            # Perform match based on mode
            if match_mode == "all_in":
                # All items must be found in matches
                missing = [item for item in items if item not in matches]
                if missing:
                    missing_items = ", ".join(missing)
                    found_items = ", ".join(matches)
                    context_msg = f"Items not found in file: {missing_items}. Found: {found_items}"
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=context_msg,
                    )
            elif match_mode == "none_in":
                # No items should be found in matches
                found = [item for item in items if item in matches]
                if found:
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Items found in file but should not be: {', '.join(found)}",
                    )
            else:
                raise ValueError(f"Unknown match_mode: {match_mode}")

            return None

        except Exception as e:
            raise ValueError(f"ListRegexMatchValidator error: {e}")

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        context: str,
    ) -> DocumentLearning:
        """Create a DocumentLearning for a validation failure."""
        return DocumentLearning(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[f.relative_path for f in bundle.files],
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            learning_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class ValidatorRegistry:
    """Registry mapping rule types to validator implementations."""

    def __init__(self, loader: Any = None) -> None:
        """Initialize registry with available validators.

        Args:
            loader: Optional document loader for resource access
        """
        self._validators = {
            ValidationType.FILE_EXISTS: FileExistsValidator(loader),
            ValidationType.FILE_NOT_EXISTS: FileExistsValidator(loader),
            ValidationType.LIST_MATCH: ListMatchValidator(loader),
            ValidationType.LIST_REGEX_MATCH: ListRegexMatchValidator(loader),
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
