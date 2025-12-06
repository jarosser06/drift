"""Generic validators for dependency analysis.

These validators work with any DependencyGraph implementation and can be
used for different file-based dependency systems.
"""

import logging
from pathlib import Path
from typing import Any, List, Literal, Optional, Type

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.utils.dependency_graph import DependencyGraph
from drift.validation.validators.base import BaseValidator

logger = logging.getLogger(__name__)


class DependencyDuplicateValidator(BaseValidator):
    """Generic validator for detecting duplicate dependencies.

    Works with any DependencyGraph implementation. Subclasses should provide
    the graph_class and implement _determine_resource_type for their specific
    file conventions.
    """

    def __init__(
        self, loader: Any = None, graph_class: Optional[Type[DependencyGraph]] = None
    ) -> None:
        """Initialize validator.

        Args:
            loader: Document loader
            graph_class: DependencyGraph class to use (must be set by subclass or caller)
        """
        super().__init__(loader)
        self.graph_class = graph_class

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
        """Detect duplicate resource declarations in dependency chain.

        -- rule: ValidationRule with params for resource_dirs
        -- bundle: Document bundle being validated
        -- all_bundles: List of all bundles (needed for cross-bundle analysis)

        Returns DocumentRule if duplicates found, None otherwise.
        """
        if not all_bundles:
            # Need all bundles for cross-bundle analysis
            return None

        if not self.graph_class:
            raise ValueError("graph_class must be provided")

        resource_dirs = rule.params.get("resource_dirs", [])
        if not resource_dirs:
            raise ValueError("DependencyDuplicateValidator requires 'resource_dirs' param")

        # Build dependency graph from all bundles
        project_path = bundle.project_path
        graph = self.graph_class(project_path)

        # Load all resources from all bundles
        for b in all_bundles:
            for file in b.files:
                file_path = Path(file.file_path)
                resource_type = self._determine_resource_type(file_path)
                if resource_type:
                    try:
                        graph.load_resource(file_path, resource_type)
                    except Exception as e:
                        # Skip files that can't be loaded
                        logger.debug(f"Skipping {file_path}: {e}")
                        continue

        # Check current bundle for duplicates
        duplicates_found = []
        for file in bundle.files:
            file_path = Path(file.file_path)
            resource_type = self._determine_resource_type(file_path)
            if not resource_type:
                continue

            resource_id = graph.extract_resource_id(file_path, resource_type)

            try:
                duplicates = graph.find_transitive_duplicates(resource_id)
                if duplicates:
                    for dup_resource, declared_by in duplicates:
                        duplicates_found.append((file.relative_path, dup_resource, declared_by))
            except KeyError:
                # Resource not in graph
                continue

        if duplicates_found:
            # Build detailed failure information
            duplicate_details = []
            for file_rel_path, dup_resource, declared_by in duplicates_found:
                duplicate_details.append(
                    {
                        "file": file_rel_path,
                        "duplicate_resource": dup_resource,
                        "declared_by": declared_by,
                    }
                )

            # Format primary duplicate for the main message
            primary_dup = duplicates_found[0]
            failure_details = {
                "duplicate_resource": primary_dup[1],
                "declared_by": primary_dup[2],
                "duplicate_count": len(duplicates_found),
                "all_duplicates": duplicate_details,
            }

            # Format observed issue with details
            if len(duplicates_found) == 1:
                detailed_message = self._format_message(
                    rule.failure_message
                    + ": '{duplicate_resource}' is redundant "
                    + "(already declared by '{declared_by}')",
                    failure_details,
                )
            else:
                template = rule.failure_message + ": {duplicate_count} duplicates detected"
                detailed_message = self._format_message(template, failure_details)
                # Add details for each duplicate
                dup_summaries = [
                    f"{dd['file']}: '{dd['duplicate_resource']}' "
                    f"(declared by '{dd['declared_by']}')"
                    for dd in duplicate_details
                ]
                detailed_message += " (" + "; ".join(dup_summaries) + ")"

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[d[0] for d in duplicates_found],
                observed_issue=detailed_message,
                expected_quality=rule.expected_behavior,
                rule_type="",
                context=f"Validation rule: {rule.description}",
                failure_details=failure_details,
            )

        return None

    def _determine_resource_type(self, file_path: Path) -> Optional[str]:
        """Determine resource type from file path.

        Subclasses should override this for specific file conventions.

        -- file_path: Path to resource file

        Returns resource type or None.
        """
        return None
