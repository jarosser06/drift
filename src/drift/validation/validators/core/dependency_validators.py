"""Validators for dependency analysis."""

from pathlib import Path
from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.utils.dependency_graph import DependencyGraph
from drift.validation.validators.base import BaseValidator


class DependencyDuplicateValidator(BaseValidator):
    """Validator for detecting duplicate dependencies in Claude Code resources."""

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

        -- rule: ValidationRule with params for agent_tool and resource_dirs
        -- bundle: Document bundle being validated (command/skill/agent)
        -- all_bundles: List of all bundles (needed for cross-bundle analysis)

        Returns DocumentRule if duplicates found, None otherwise.
        """
        # Extract params
        # agent_tool = rule.params.get("agent_tool", "claude-code")  # For future use
        resource_dirs = rule.params.get("resource_dirs", [])

        if not all_bundles:
            # Need all bundles for cross-bundle analysis
            return None

        if not resource_dirs:
            raise ValueError("DependencyDuplicateValidator requires 'resource_dirs' param")

        # Build dependency graph from all bundles
        project_path = bundle.project_path
        graph = DependencyGraph(project_path)

        # Load all resources from all bundles
        for b in all_bundles:
            for file in b.files:
                # Determine resource type from path
                file_path = Path(file.file_path)
                resource_type = self._determine_resource_type(file_path)
                if resource_type:
                    try:
                        graph.load_resource(file_path, resource_type)
                    except Exception:
                        # Skip files that can't be loaded
                        continue

        # Check current bundle for duplicates
        duplicates_found = []
        for file in bundle.files:
            file_path = Path(file.file_path)
            resource_type = self._determine_resource_type(file_path)
            if not resource_type:
                continue

            resource_id = graph._extract_resource_id(file_path, resource_type)

            try:
                duplicates = graph.find_transitive_duplicates(resource_id)
                if duplicates:
                    for dup_resource, declared_by in duplicates:
                        duplicates_found.append((file.relative_path, dup_resource, declared_by))
            except KeyError:
                # Resource not in graph
                continue

        if duplicates_found:
            # Build detailed message
            messages = []
            for file_rel_path, dup_resource, declared_by in duplicates_found:
                messages.append(
                    f"{file_rel_path}: '{dup_resource}' is redundant "
                    f"(already declared by '{declared_by}')"
                )

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[d[0] for d in duplicates_found],
                observed_issue=rule.failure_message + ": " + "; ".join(messages),
                expected_quality=rule.expected_behavior,
                rule_type="",
                context=f"Validation rule: {rule.description}",
            )

        return None

    def _determine_resource_type(self, file_path: Path) -> Optional[str]:
        """Determine resource type from file path.

        -- file_path: Path to resource file

        Returns resource type (skill, command, agent) or None.
        """
        path_str = str(file_path)
        if "/skills/" in path_str and file_path.name == "SKILL.md":
            return "skill"
        elif "/commands/" in path_str and file_path.suffix == ".md":
            return "command"
        elif "/agents/" in path_str and file_path.suffix == ".md":
            return "agent"
        return None
