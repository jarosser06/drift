"""Claude Code-specific dependency validators."""

from pathlib import Path
from typing import Any, Optional

from drift.utils.claude_dependency_graph import ClaudeDependencyGraph
from drift.validation.validators.core.circular_dependencies_validator import (
    CircularDependenciesValidator as BaseCircularValidator,
)
from drift.validation.validators.core.dependency_validators import (
    DependencyDuplicateValidator as BaseDuplicateValidator,
)
from drift.validation.validators.core.max_dependency_depth_validator import (
    MaxDependencyDepthValidator as BaseDepthValidator,
)


class ClaudeCircularDependenciesValidator(BaseCircularValidator):
    """Claude Code circular dependency validator.

    Detects cycles in Claude Code resource dependencies (commands, skills, agents).
    Uses YAML frontmatter 'skills' field for dependency information.
    """

    def __init__(self, loader: Any = None) -> None:
        """Initialize with ClaudeDependencyGraph.

        Args:
            loader: Optional document loader for resource access
        """
        super().__init__(loader, graph_class=ClaudeDependencyGraph)

    def _determine_resource_type(self, file_path: Path) -> Optional[str]:
        """Determine Claude Code resource type from file path.

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


class ClaudeMaxDependencyDepthValidator(BaseDepthValidator):
    """Claude Code max dependency depth validator.

    Detects when Claude Code resource dependency chains exceed maximum depth.
    Uses YAML frontmatter 'skills' field for dependency information.
    """

    def __init__(self, loader: Any = None) -> None:
        """Initialize with ClaudeDependencyGraph.

        Args:
            loader: Optional document loader for resource access
        """
        super().__init__(loader, graph_class=ClaudeDependencyGraph)

    def _determine_resource_type(self, file_path: Path) -> Optional[str]:
        """Determine Claude Code resource type from file path.

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


class ClaudeDependencyDuplicateValidator(BaseDuplicateValidator):
    """Claude Code dependency duplicate validator.

    Detects redundant dependencies in Claude Code resources where a dependency
    is already declared by a transitive dependency.
    Uses YAML frontmatter 'skills' field for dependency information.
    """

    def __init__(self, loader: Any = None) -> None:
        """Initialize with ClaudeDependencyGraph.

        Args:
            loader: Optional document loader for resource access
        """
        super().__init__(loader, graph_class=ClaudeDependencyGraph)

    def _determine_resource_type(self, file_path: Path) -> Optional[str]:
        """Determine Claude Code resource type from file path.

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
