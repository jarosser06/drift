"""Pattern matching utilities for ignore configurations.

This module provides utilities for matching file paths against various pattern types
including glob patterns, regex patterns, and literal paths.
"""

import re
from pathlib import Path
from typing import List


def is_regex_pattern(pattern: str) -> bool:
    """Detect if a pattern is a regex pattern.

    Checks for common regex metacharacters that indicate the pattern
    is intended as a regular expression rather than a glob pattern.

    -- pattern: Pattern string to check

    Returns True if pattern appears to be regex, False otherwise.
    """
    regex_indicators = [
        r"\(",
        r"\)",
        r"\[",
        r"\]",
        r"\{",
        r"\}",
        r"\^",
        r"\$",
        r"\+",
        r"\.",
        r"\|",
    ]
    return any(indicator in pattern for indicator in regex_indicators)


def match_glob_pattern(path: str, pattern: str) -> bool:
    """Match a path against a glob pattern.

    Uses pathlib.Path.match() for glob pattern matching.
    Supports patterns like:
    - "*.md" - matches any .md file
    - "**/*.py" - matches .py files in any subdirectory
    - "src/**" - matches anything under src/

    -- path: File path to check (relative or absolute)
    -- pattern: Glob pattern to match against

    Returns True if path matches pattern, False otherwise.
    """
    try:
        path_obj = Path(path)
        return path_obj.match(pattern)
    except (ValueError, TypeError):
        return False


def match_regex_pattern(path: str, pattern: str) -> bool:
    """Match a path against a regex pattern.

    Uses re.match() for regex pattern matching. The pattern is
    matched from the beginning of the path string.

    -- path: File path to check
    -- pattern: Regex pattern to match against

    Returns True if path matches pattern, False otherwise.

    Raises re.error if pattern is invalid regex.
    """
    try:
        compiled = re.compile(pattern)
        return compiled.match(path) is not None
    except re.error as e:
        raise ValueError(f"Invalid regex pattern '{pattern}': {e}") from e


def match_literal_path(path: str, literal: str) -> bool:
    """Match a path against a literal path string.

    Performs exact string comparison after normalizing both paths.
    Also checks if the path ends with the literal (for matching
    relative paths against absolute paths).

    -- path: File path to check
    -- literal: Literal path string to match

    Returns True if paths match, False otherwise.
    """
    path_normalized = Path(path).as_posix()
    literal_normalized = Path(literal).as_posix()

    return path_normalized == literal_normalized or path_normalized.endswith(
        "/" + literal_normalized.lstrip("/")
    )


def match_pattern(path: str, pattern: str) -> bool:
    """Match a path against a pattern, auto-detecting pattern type.

    Automatically detects whether the pattern is a regex pattern
    or glob pattern and applies the appropriate matching logic.

    Pattern type detection:
    - If pattern contains regex metacharacters (^, $, etc.), treat as regex
    - Otherwise, treat as glob pattern

    -- path: File path to check
    -- pattern: Pattern to match (glob or regex)

    Returns True if path matches pattern, False otherwise.

    Raises ValueError if regex pattern is invalid.
    """
    if is_regex_pattern(pattern):
        return match_regex_pattern(path, pattern)
    else:
        return match_glob_pattern(path, pattern)


def should_ignore_path(path: str, ignore_patterns: List[str]) -> bool:
    """Check if a path should be ignored based on a list of patterns.

    Checks the path against all ignore patterns. Returns True if
    any pattern matches.

    -- path: File path to check
    -- ignore_patterns: List of patterns (glob or regex)

    Returns True if path matches any pattern, False otherwise.

    Raises ValueError if any regex pattern is invalid.
    """
    if not ignore_patterns:
        return False

    for pattern in ignore_patterns:
        if match_pattern(path, pattern):
            return True

    return False
