"""Generic validator for detecting circular dependencies."""

import logging
from pathlib import Path
from typing import Any, List, Literal, Optional, Type

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.utils.dependency_graph import DependencyGraph
from drift.validation.validators.base import BaseValidator

logger = logging.getLogger(__name__)


class CircularDependenciesValidator(BaseValidator):
    """Generic validator for detecting circular dependencies.

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
        return "core:circular_dependencies"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "Circular dependency detected: {circular_path}"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "No circular dependencies should exist"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Detect circular dependencies.

        -- rule: ValidationRule with params for resource_dirs
        -- bundle: Document bundle being validated
        -- all_bundles: List of all bundles (needed for cross-bundle analysis)

        Returns DocumentRule if cycles found, None otherwise.
        """
        if not all_bundles:
            return None

        if not self.graph_class:
            raise ValueError("graph_class must be provided")

        resource_dirs = rule.params.get("resource_dirs", [])
        if not resource_dirs:
            raise ValueError("CircularDependenciesValidator requires 'resource_dirs' param")

        # Build graph using the provided graph class
        graph = self.graph_class(bundle.project_path)

        # Load all resources
        for b in all_bundles:
            for file in b.files:
                file_path = Path(file.file_path)
                resource_type = self._determine_resource_type(file_path)
                if resource_type:
                    try:
                        graph.load_resource(file_path, resource_type)
                    except Exception as e:
                        logger.debug(f"Skipping {file_path}: {e}")
                        continue

        # Check for cycles
        cycles_found = []
        for file in bundle.files:
            file_path = Path(file.file_path)
            resource_type = self._determine_resource_type(file_path)
            if not resource_type:
                continue

            resource_id = graph.extract_resource_id(file_path, resource_type)

            try:
                cycles = graph.find_cycles(resource_id)
                if cycles:
                    for cycle in cycles:
                        cycles_found.append((file.relative_path, cycle))
            except KeyError:
                continue

        if cycles_found:
            # Build detailed failure information
            cycle_details = []
            for file_rel_path, cycle in cycles_found:
                cycle_path = " → ".join(cycle)
                cycle_details.append({"file": file_rel_path, "cycle_path": cycle_path})

            # Format primary cycle for the main message
            primary_cycle = " → ".join(cycles_found[0][1])
            failure_details = {
                "circular_path": primary_cycle,
                "cycle_count": len(cycles_found),
                "all_cycles": cycle_details,
            }

            # Format observed issue with details
            # Use custom message if provided, otherwise use default with template
            observed_issue = self._get_failure_message(rule, failure_details)

            # If custom message doesn't contain {circular_path}, ensure cycle info is present
            # This handles cases where users provide custom messages without template vars
            if "{circular_path}" not in (rule.failure_message or ""):
                if "{circular_path}" not in observed_issue:
                    # Custom message without template - append cycle details
                    if len(cycles_found) == 1:
                        observed_issue += f": {primary_cycle}"
                    else:
                        cycle_summaries = [
                            f"{cd['file']}: {cd['cycle_path']}" for cd in cycle_details
                        ]
                        observed_issue += (
                            f" ({len(cycles_found)} cycles: " + "; ".join(cycle_summaries) + ")"
                        )

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[c[0] for c in cycles_found],
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
