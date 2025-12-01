"""YAML frontmatter parsing utilities for markdown files."""

import re
from typing import Any, Dict, Optional

import yaml


def extract_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Extract YAML frontmatter from markdown content.

    Frontmatter is defined as YAML content between triple-dash markers
    at the beginning of the file.

    Example:
        >>> content = '''---
        ... name: my-skill
        ... skills:
        ...   - other-skill
        ... ---
        ... # Content here
        ... '''
        >>> fm = extract_frontmatter(content)
        >>> fm['name']
        'my-skill'

    Args:
        content: Markdown file content

    Returns:
        Dict of parsed YAML frontmatter, or None if no frontmatter found

    Raises:
        yaml.YAMLError: If frontmatter contains invalid YAML
    """
    # Match --- ... --- blocks at start of file
    # Pattern explanation:
    # ^--- matches "---" at start of string
    # \s* allows optional whitespace after opening ---
    # (.*?) captures frontmatter content (non-greedy)
    # \s*^--- matches closing "---" on its own line
    pattern = r"^---\s*\n(.*?)\n^---\s*$"
    match = re.match(pattern, content, re.MULTILINE | re.DOTALL)

    if not match:
        return None

    frontmatter_text = match.group(1)

    try:
        parsed = yaml.safe_load(frontmatter_text)
        return parsed if isinstance(parsed, dict) else None
    except yaml.YAMLError:
        # Re-raise to let caller handle malformed YAML
        raise
