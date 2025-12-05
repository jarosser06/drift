"""Generic dependency graph analysis framework.

This module provides an abstract base class for dependency graph analysis
that can be extended for different file-based dependency systems.
"""

from abc import ABC, abstractmethod
from collections import deque
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class DependencyGraph(ABC):
    """Abstract base class for dependency graph analysis.

    This class provides generic graph algorithms (cycle detection, depth
    calculation, transitive duplicate detection) that work with any
    dependency system. Subclasses implement how dependencies are extracted
    from files.

    Example:
        >>> # Subclass for your specific dependency system
        >>> class MyGraph(DependencyGraph):
        ...     def extract_dependencies(self, file_path, resource_type):
        ...         # Parse your file format
        ...         return {"dep1", "dep2"}
        ...     def extract_resource_id(self, resource_path, resource_type):
        ...         return resource_path.stem
        >>> graph = MyGraph(Path("/project"))
        >>> graph.load_resource(Path("/project/file.ext"), "type")
        >>> cycles = graph.find_cycles("resource_id")

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

    @abstractmethod
    def extract_dependencies(self, file_path: Path, resource_type: str) -> Set[str]:
        """Extract dependencies from a file.

        Subclasses implement this to define dependency extraction logic.
        For example:
        - Parse YAML frontmatter
        - Parse import statements
        - Parse file links

        Args:
            file_path: Path to resource file
            resource_type: Type of resource

        Returns:
            Set of dependency identifiers
        """
        pass

    @abstractmethod
    def extract_resource_id(self, resource_path: Path, resource_type: str) -> str:
        """Extract resource ID from file path.

        Subclasses implement this to define naming conventions.

        Args:
            resource_path: Path to resource file
            resource_type: Type of resource

        Returns:
            Resource ID (name without extension/directory)
        """
        pass

    def load_resource(self, resource_path: Path, resource_type: str) -> None:
        """Load a resource and extract its dependencies.

        Calls subclass methods to extract resource ID and dependencies,
        then stores them in the graph.

        Args:
            resource_path: Absolute path to the resource file
            resource_type: Type of resource

        Raises:
            FileNotFoundError: If resource file doesn't exist
        """
        if not resource_path.exists():
            raise FileNotFoundError(f"Resource file not found: {resource_path}")

        # Extract resource ID from path
        resource_id = self.extract_resource_id(resource_path, resource_type)

        # Extract dependencies using subclass implementation
        deps = self.extract_dependencies(resource_path, resource_type)

        # Store in graph
        self.dependencies[resource_id] = deps
        self.resource_paths[resource_id] = resource_path

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

    def find_cycles(self, resource_id: str) -> List[List[str]]:
        """Find all cycles reachable from a resource.

        Uses DFS with path tracking to detect cycles in the dependency graph.
        A cycle exists when we revisit a node that's already in the current path.

        Args:
            resource_id: Starting resource ID

        Returns:
            List of cycles, where each cycle is a list of resource IDs forming
            the cycle path (e.g., [['A', 'B', 'C', 'A']])

        Raises:
            KeyError: If resource_id not found in graph
        """
        if resource_id not in self.dependencies:
            raise KeyError(f"Resource '{resource_id}' not found in dependency graph")

        cycles: List[List[str]] = []
        visited: Set[str] = set()
        path: List[str] = []
        path_set: Set[str] = set()

        def dfs(current: str) -> None:
            """DFS helper to detect cycles."""
            if current in path_set:
                # Found a cycle - extract the cycle path
                cycle_start_idx = path.index(current)
                cycle_path = path[cycle_start_idx:] + [current]
                cycles.append(cycle_path)
                return

            if current in visited:
                # Already fully explored this node
                return

            if current not in self.dependencies:
                # Node not in graph
                return

            # Add to current path
            path.append(current)
            path_set.add(current)

            # Explore dependencies
            for dep in self.dependencies[current]:
                dfs(dep)

            # Remove from current path
            path.pop()
            path_set.remove(current)
            visited.add(current)

        dfs(resource_id)
        return cycles

    def get_dependency_depth(self, resource_id: str) -> Tuple[int, List[str]]:
        """Calculate the maximum dependency depth from a resource.

        Uses BFS with depth tracking to find the longest dependency chain.
        Handles cycles by tracking visited nodes.

        Args:
            resource_id: Starting resource ID

        Returns:
            Tuple of (max_depth, longest_path) where:
            - max_depth: Maximum depth of dependency chain (0 if no dependencies)
            - longest_path: List of resource IDs forming the longest chain

        Raises:
            KeyError: If resource_id not found in graph
        """
        if resource_id not in self.dependencies:
            raise KeyError(f"Resource '{resource_id}' not found in dependency graph")

        if not self.dependencies[resource_id]:
            # No dependencies
            return (0, [resource_id])

        # BFS with depth and path tracking
        queue: deque = deque([(resource_id, 0, [resource_id])])
        visited: Set[str] = {resource_id}
        max_depth = 0
        longest_path: List[str] = [resource_id]

        while queue:
            current, depth, path = queue.popleft()

            if current not in self.dependencies:
                continue

            deps = self.dependencies[current]
            if not deps:
                # Leaf node - check if this is the longest path
                if depth > max_depth:
                    max_depth = depth
                    longest_path = path
                continue

            for dep in deps:
                new_depth = depth + 1
                new_path = path + [dep]

                # Update max depth if this is longer
                if new_depth > max_depth:
                    max_depth = new_depth
                    longest_path = new_path

                # Only visit if not already visited (avoid cycles)
                if dep not in visited:
                    visited.add(dep)
                    queue.append((dep, new_depth, new_path))

        return (max_depth, longest_path)
