"""Claude Code dependency graph implementation."""

from pathlib import Path
from typing import Set

from drift.utils.dependency_graph import DependencyGraph
from drift.utils.frontmatter import extract_frontmatter


class ClaudeDependencyGraph(DependencyGraph):
    """Dependency graph for Claude Code resources.

    Parses dependencies from YAML frontmatter 'skills:' field.
    Uses Claude Code directory conventions for resource identification.

    Example:
        >>> graph = ClaudeDependencyGraph(Path("/project"))
        >>> graph.load_resource(Path("/.claude/commands/test.md"), "command")
        >>> graph.load_resource(Path("/.claude/skills/testing/SKILL.md"), "skill")
        >>> duplicates = graph.find_transitive_duplicates("test")
        >>> for dup, declared_by in duplicates:
        ...     print(f"{dup} is redundant (already in {declared_by})")
    """

    def extract_dependencies(self, file_path: Path, resource_type: str) -> Set[str]:
        """Extract dependencies from YAML frontmatter skills field.

        Args:
            file_path: Path to resource file
            resource_type: Type of resource

        Returns:
            Set of dependency IDs from the 'skills' frontmatter field

        Raises:
            yaml.YAMLError: If frontmatter contains invalid YAML
        """
        content = file_path.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)

        deps = set()
        if frontmatter and "skills" in frontmatter:
            skills = frontmatter["skills"]
            if isinstance(skills, list):
                deps = set(skills)

        return deps

    def extract_resource_id(self, resource_path: Path, resource_type: str) -> str:
        """Extract resource ID using Claude Code conventions.

        Args:
            resource_path: Path to resource file
            resource_type: Type of resource

        Returns:
            Resource ID (skill directory name, or command/agent stem)
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
