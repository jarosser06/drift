"""File existence checker for draft functionality.

Checks which target files already exist on disk to prevent accidental overwrites.
"""

from pathlib import Path
from typing import List, Tuple


class FileExistenceChecker:
    """Checks if target files already exist."""

    @staticmethod
    def check(target_files: List[Path]) -> Tuple[bool, List[Path]]:
        """Check if any target files exist.

        Parameters
        ----------
        target_files : List[Path]
            List of file paths to check for existence.

        Returns
        -------
        Tuple[bool, List[Path]]
            A tuple of (any_exist, existing_files) where any_exist is True
            if at least one file exists, and existing_files is the list of
            files that exist.

        Examples
        --------
        >>> files = [Path("/tmp/a.txt"), Path("/tmp/b.txt")]
        >>> any_exist, existing = FileExistenceChecker.check(files)
        >>> if any_exist:
        ...     print(f"Files exist: {existing}")
        """
        existing = [f for f in target_files if f.exists()]
        return len(existing) > 0, existing
