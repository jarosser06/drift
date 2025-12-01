"""Dependency graph analysis for Claude Code resources."""

from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from drift.utils.frontmatter import extract_frontmatter


class DependencyGraph:
    """Build and analyze Claude Code resource dependency graphs.

    This class builds a dependency graph from Claude Code resources
    (commands, skills, agents) and can detect transitive duplicate
    dependencies.

    Example:
        >>> graph = DependencyGraph(Path("/project"))
        >>> graph.load_resource(Path("/.claude/commands/test.md"), "command")
        >>> graph.load_resource(Path("/.claude/skills/testing/SKILL.md"), "skill")
        >>> duplicates = graph.find_transitive_duplicates("test")
        >>> for dup, declared_by in duplicates:
        ...     print(f"{dup} is redundant (already in {declared_by})")

    Attributes:
        project_path: Root path of the project
        dependencies: Mapping of resource_id -> Set of dependency IDs
        resource_paths: Mapping of resource_id -> file path
    """

    def __init__(self, project_path: Path):
        """Initialize dependency graph.

        Args:
            project_path: Root path of the project
        """
        self.project_path = project_path
        self.dependencies: Dict[str, Set[str]] = {}
        self.resource_paths: Dict[str, Path] = {}

    def load_resource(self, resource_path: Path, resource_type: str) -> None:
        """Load a resource and extract its dependencies.

        Reads the resource file, extracts YAML frontmatter, and stores
        the 'skills' field as dependencies.

        Args:
            resource_path: Absolute path to the resource file
            resource_type: Type of resource (command, skill, agent)

        Raises:
            FileNotFoundError: If resource file doesn't exist
            yaml.YAMLError: If frontmatter contains invalid YAML
        """
        if not resource_path.exists():
            raise FileNotFoundError(f"Resource file not found: {resource_path}")

        # Extract resource ID from path
        resource_id = self._extract_resource_id(resource_path, resource_type)

        # Read and parse file
        content = resource_path.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)

        # Extract dependencies (skills field)
        deps = set()
        if frontmatter and "skills" in frontmatter:
            skills = frontmatter["skills"]
            if isinstance(skills, list):
                deps = set(skills)

        # Store in graph
        self.dependencies[resource_id] = deps
        self.resource_paths[resource_id] = resource_path

    def _extract_resource_id(self, resource_path: Path, resource_type: str) -> str:
        """Extract resource ID from file path.

        Args:
            resource_path: Path to resource file
            resource_type: Type of resource

        Returns:
            Resource ID (name without extension/directory)
        """
        if resource_type == "skill":
            # Skills are in .claude/skills/{name}/SKILL.md
            return resource_path.parent.name
        elif resource_type in ("command", "agent"):
            # Commands/agents are .claude/commands/{name}.md or .claude/agents/{name}.md
            return resource_path.stem
        else:
            # Fallback: use stem
            return resource_path.stem

    def find_transitive_duplicates(self, resource_id: str) -> List[Tuple[str, str]]:
        """Find duplicate declarations in transitive dependencies.

        Detects when a resource declares a dependency that's already
        declared by one of its transitive dependencies.

        Example:
            If Command A declares [Skill B, Skill C]
            and Skill B declares [Skill C]
            then Skill C is redundant in Command A's declaration.

        Args:
            resource_id: ID of resource to check

        Returns:
            List of (duplicate_resource, declared_by) tuples where:
            - duplicate_resource: The redundant dependency
            - declared_by: Which transitive dependency already declares it

        Raises:
            KeyError: If resource_id not found in graph
        """
        if resource_id not in self.dependencies:
            raise KeyError(f"Resource '{resource_id}' not found in dependency graph")

        direct_deps = self.dependencies[resource_id]
        duplicates: List[Tuple[str, str]] = []

        # For each direct dependency, get its transitive dependencies
        for dep in direct_deps:
            if dep not in self.dependencies:
                # Dependency not loaded (might not exist)
                continue

            transitive_deps = self._get_transitive_dependencies(dep)

            # Find overlap between direct deps and this dependency's transitive deps
            for other_direct_dep in direct_deps:
                if other_direct_dep != dep and other_direct_dep in transitive_deps:
                    # Found a duplicate: resource_id declares other_direct_dep,
                    # but dep (a dependency of resource_id) already declares it transitively
                    duplicates.append((other_direct_dep, dep))

        return duplicates

    def _get_transitive_dependencies(
        self, resource_id: str, visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """Get all transitive dependencies of a resource.

        Uses BFS to traverse the dependency graph and collect all
        reachable dependencies.

        Args:
            resource_id: Starting resource ID
            visited: Set of already visited nodes (for cycle detection)

        Returns:
            Set of all transitive dependency IDs
        """
        if visited is None:
            visited = set()

        if resource_id in visited:
            # Cycle detected, stop recursion
            return set()

        if resource_id not in self.dependencies:
            # Resource not loaded
            return set()

        visited.add(resource_id)
        all_deps = set()

        # BFS to collect all transitive dependencies
        queue = deque([resource_id])
        processed = {resource_id}

        while queue:
            current = queue.popleft()

            if current not in self.dependencies:
                continue

            for dep in self.dependencies[current]:
                all_deps.add(dep)

                if dep not in processed:
                    processed.add(dep)
                    queue.append(dep)

        return all_deps
