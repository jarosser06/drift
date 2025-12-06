"""Validators for list matching operations."""

from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.params import ParamResolver
from drift.validation.validators.base import BaseValidator


class ListMatchValidator(BaseValidator):
    """Validator for checking if list items match expected values."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:list_match"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "List match validation failed"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "Items should match expected list"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if list items match expected values.

        Expected params:
            - items: List to check (can be string_list or resource_list)
            - target: List to compare against (can be string_list, resource_list, or file_content)
            - match_mode: "all_in", "none_in", "exact" (default: "all_in")

        -- rule: ValidationRule with params
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if validation fails, None if passes.
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
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure."""
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[f.relative_path for f in bundle.files],
            observed_issue=self._get_failure_message(rule),
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class ListRegexMatchValidator(BaseValidator):
    """Validator for checking if list items match regex patterns in files."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:list_regex_match"

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
        """Check if list items match regex patterns in target files.

        Expected params:
            - items: List to check (can be string_list or resource_list)
            - file_path: File path to search in (can be string or file_content)
            - pattern: Regex pattern to extract matches from file
            - match_mode: "all_in", "none_in" (default: "all_in")

        -- rule: ValidationRule with params
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if validation fails, None if passes.
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
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure."""
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[f.relative_path for f in bundle.files],
            observed_issue=self._get_failure_message(rule),
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )
