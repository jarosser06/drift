"""Generic validator for detecting excessive dependency chain depth."""

import logging
from pathlib import Path
from typing import Any, List, Literal, Optional, Type

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.utils.dependency_graph import DependencyGraph
from drift.validation.validators.base import BaseValidator

logger = logging.getLogger(__name__)


class MaxDependencyDepthValidator(BaseValidator):
    """Generic validator for detecting excessive dependency chain depth.

    This validator detects when a resource's dependency chain exceeds a
    configurable maximum depth. Deep dependency chains can be hard to maintain,
    understand, and debug.

    The depth is calculated as the longest path from the resource to any leaf
    dependency (a dependency with no further dependencies).

    Example:
        If A depends on B, B depends on C, and C depends on D:
        - A has depth 3 (A → B → C → D)
        - B has depth 2 (B → C → D)
        - C has depth 1 (C → D)
        - D has depth 0 (no dependencies)

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
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:max_dependency_depth"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "Dependency depth {actual_depth} exceeds maximum {max_depth}"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "Dependency depth should not exceed maximum"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Detect when dependency chain exceeds maximum depth.

        -- rule: ValidationRule with params for max_depth and resource_dirs
        -- bundle: Document bundle being validated
        -- all_bundles: List of all bundles (needed for cross-bundle analysis)

        Returns DocumentRule if depth exceeded, None otherwise.
        """
        if not all_bundles:
            # Need all bundles for cross-bundle analysis
            return None

        if not self.graph_class:
            raise ValueError("graph_class must be provided")

        # Extract params
        max_depth = rule.params.get("max_depth", 5)
        resource_dirs = rule.params.get("resource_dirs", [])

        if not resource_dirs:
            raise ValueError("MaxDependencyDepthValidator requires 'resource_dirs' param")

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

        # Check current bundle for excessive depth
        depth_violations = []
        for file in bundle.files:
            file_path = Path(file.file_path)
            resource_type = self._determine_resource_type(file_path)
            if not resource_type:
                continue

            resource_id = graph.extract_resource_id(file_path, resource_type)

            try:
                depth, path = graph.get_dependency_depth(resource_id)
                if depth > max_depth:
                    depth_violations.append((file.relative_path, depth, path))
            except KeyError:
                # Resource not in graph
                continue

        if depth_violations:
            # Build detailed failure information
            violation_details = []
            for file_rel_path, depth, path in depth_violations:
                chain_path = " → ".join(path)
                violation_details.append(
                    {"file": file_rel_path, "actual_depth": depth, "dependency_chain": chain_path}
                )

            # Format primary violation for the main message
            primary_violation = depth_violations[0]
            primary_chain = " → ".join(primary_violation[2])
            failure_details = {
                "actual_depth": primary_violation[1],
                "max_depth": max_depth,
                "dependency_chain": primary_chain,
                "violation_count": len(depth_violations),
                "all_violations": violation_details,
            }

            # Format observed issue with details
            observed_issue = self._get_failure_message(rule, failure_details)

            # If custom message doesn't contain placeholders, append details
            if "{actual_depth}" not in (rule.failure_message or ""):
                if len(depth_violations) == 1:
                    observed_issue += (
                        f": Depth {primary_violation[1]} exceeds maximum {max_depth}. "
                        f"Chain: {primary_chain}"
                    )
                else:
                    observed_issue += f": {len(depth_violations)} violations detected"
                    # Add details for each violation
                    violation_summaries = [
                        f"{vd['file']}: Depth {vd['actual_depth']} exceeds {max_depth}"
                        for vd in violation_details
                    ]
                    observed_issue += " (" + "; ".join(violation_summaries) + ")"

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[v[0] for v in depth_violations],
                observed_issue=observed_issue,
                expected_quality=self._get_expected_behavior(rule),
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
