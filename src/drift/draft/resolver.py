"""File pattern resolver for draft functionality.

Resolves glob patterns with wildcards to concrete target file paths,
handling cases where directories may not exist yet.
"""

from pathlib import Path
from typing import List


class FilePatternResolver:
    """Resolves file patterns to concrete target paths."""

    def __init__(self, project_path: Path):
        """Initialize resolver with project path.

        Parameters
        ----------
        project_path : Path
            Root path of the project.
        """
        self.project_path = project_path

    def resolve(self, file_pattern: str) -> List[Path]:
        """Resolve file pattern to a single concrete path.

        For patterns with wildcards (e.g., `.claude/skills/*/SKILL.md`):
        - Returns empty list (requires explicit file path via --target-file)

        For patterns without wildcards (e.g., `.claude/skills/testing/SKILL.md`):
        - Returns single path (whether or not it exists)

        This prevents auto-discovery of multiple files. Draft should work
        on ONE file at a time, explicitly specified either in the rule pattern
        or via the --target-file flag.

        Parameters
        ----------
        file_pattern : str
            File pattern (e.g., ".claude/skills/*/SKILL.md" or ".claude/skills/testing/SKILL.md").

        Returns
        -------
        List[Path]
            List containing single path if no wildcards, empty list if wildcards present.

        Examples
        --------
        >>> resolver = FilePatternResolver(Path("/project"))
        >>> resolver.resolve(".claude/skills/testing/SKILL.md")
        [Path("/project/.claude/skills/testing/SKILL.md")]
        >>> resolver.resolve(".claude/skills/*/SKILL.md")
        []
        """
        # Check if pattern has wildcards
        has_wildcard = "*" in file_pattern or "?" in file_pattern

        # If wildcards present, return empty (require explicit --target-file)
        if has_wildcard:
            return []

        # No wildcard - return single path
        return [self.project_path / file_pattern]
