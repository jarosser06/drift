"""Markdown link validation utilities."""

import re
from pathlib import Path
from typing import List, Tuple

import requests


class LinkValidator:
    """Validate various types of markdown links.

    This class provides utilities to extract and validate links from
    markdown content, including local files, external URLs, and resource
    references.

    Example:
        >>> validator = LinkValidator()
        >>> links = validator.extract_links("[doc](file.md)")
        >>> for text, url in links:
        ...     print(f"{text}: {url}")
        doc: file.md

    Attributes:
        None
    """

    def extract_links(self, content: str) -> List[Tuple[str, str]]:
        """Extract all markdown links from content.

        Extracts standard markdown links in the format [text](url).

        Args:
            content: Markdown content to parse

        Returns:
            List of (link_text, link_url) tuples
        """
        # Regex pattern for markdown links: [text](url)
        # Pattern explanation:
        # \[ matches opening bracket
        # ([^\]]+) captures link text (anything except ])
        # \] matches closing bracket
        # \( matches opening paren
        # ([^\)]+) captures link URL (anything except ))
        # \) matches closing paren
        pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
        matches = re.findall(pattern, content)
        return matches

    def extract_all_file_references(self, content: str) -> List[str]:
        """Extract all file references from content.

        Extracts both markdown-style links and plain file path references.
        This includes:
        - Markdown links: [text](path)
        - Relative paths: ./file.sh, ../dir/file.py
        - Absolute paths: /path/to/file
        - Simple paths: path/to/file.ext

        Args:
            content: Content to parse

        Returns:
            List of file path strings found in content
        """
        references = []

        # Extract markdown links first
        markdown_links = self.extract_links(content)
        markdown_urls = set()
        for _, url in markdown_links:
            references.append(url)
            markdown_urls.add(url)

        # Remove markdown link content and URLs from the text to avoid matching fragments
        # Replace [text](url) with just text to avoid matching url fragments
        content_without_md_links = re.sub(r"\[([^\]]+)\]\(([^\)]+)\)", r"\1", content)
        # Also remove plain URLs like https://example.com
        content_without_urls = re.sub(r"https?://[^\s]+", "", content_without_md_links)

        # Extract path-like references (but not URLs)
        # Match patterns like:
        # - Standalone files with extensions: README.md, config.yaml
        # - Relative paths: ./file.sh, ../dir/file.py
        # - /absolute/path/to/file (but not URLs like https://...)
        # - Nested paths: path/to/file.ext
        path_patterns = [
            # Relative paths starting with ./ or ../ (most reliable indicator)
            r"\.{1,2}/[\w\-./]+",
            # Paths with slashes and file extensions: path/to/file.ext
            # This requires both a slash AND an extension to avoid false positives
            r"\b[\w\-]+(?:/[\w\-]+)+\.[\w]+\b",
            # Standalone filenames with common extensions: README.md, test.py
            # Only match if it looks like a filename (has extension, reasonable length)
            r"\b[\w\-]{1,50}\.(?:md|py|js|ts|tsx|jsx|yaml|yml|json|sh|bash|txt|csv|xml"
            r"|html|css|rs|go|java|rb|php|c|cpp|h|hpp|toml|ini|conf|cfg)\b",
        ]

        for pattern in path_patterns:
            matches = re.findall(pattern, content_without_urls)
            references.extend(matches)

        # Remove duplicates while preserving order
        seen = set()
        unique_refs = []
        for ref in references:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        return unique_refs

    def validate_local_file(self, link: str, base_path: Path) -> bool:
        """Check if local file exists.

        Resolves relative paths from the base_path and checks if the
        file exists in the filesystem.

        Args:
            link: Relative or absolute file path
            base_path: Base directory to resolve relative paths from

        Returns:
            True if file exists and is a file, False otherwise
        """
        # Handle absolute paths
        if link.startswith("/"):
            file_path = Path(link)
        else:
            # Resolve relative to base_path
            file_path = (base_path / link).resolve()

        return file_path.exists() and file_path.is_file()

    def validate_external_url(self, url: str, timeout: int = 5) -> bool:
        """Check if external URL is valid (simple HEAD request).

        Performs a HEAD request to check if the URL is reachable.
        This is a simple check - does not retry or handle complex cases.

        Args:
            url: HTTP/HTTPS URL to validate
            timeout: Request timeout in seconds (default: 5)

        Returns:
            True if URL returns status < 400, False otherwise
        """
        try:
            response = requests.head(
                url,
                timeout=timeout,
                allow_redirects=True,
                headers={"User-Agent": "Drift-Validator/1.0"},
            )
            return bool(response.status_code < 400)
        except (
            requests.RequestException,
            requests.Timeout,
            requests.ConnectionError,
        ):
            # Treat any request error as invalid
            return False

    def validate_resource_reference(self, ref: str, project_path: Path, resource_type: str) -> bool:
        """Check if resource reference exists (skill/command/agent).

        Checks if the referenced Claude Code resource exists in the
        expected location based on its type.

        Args:
            ref: Resource name/ID
            project_path: Root path of the project
            resource_type: Type of resource (skill, command, agent)

        Returns:
            True if resource exists, False otherwise
        """
        if resource_type == "skill":
            # Skills are in .claude/skills/{ref}/SKILL.md
            skill_file = project_path / ".claude" / "skills" / ref / "SKILL.md"
            return skill_file.exists() and skill_file.is_file()
        elif resource_type == "command":
            # Commands are in .claude/commands/{ref}.md
            command_file = project_path / ".claude" / "commands" / f"{ref}.md"
            return command_file.exists() and command_file.is_file()
        elif resource_type == "agent":
            # Agents are in .claude/agents/{ref}.md
            agent_file = project_path / ".claude" / "agents" / f"{ref}.md"
            return agent_file.exists() and agent_file.is_file()
        else:
            # Unknown resource type
            return False

    def categorize_link(self, link: str) -> str:
        """Categorize a link as local, external, or unknown.

        Args:
            link: Link URL to categorize

        Returns:
            One of: "local", "external", "unknown"
        """
        if link.startswith(("http://", "https://")):
            return "external"
        elif link.startswith(("#", "mailto:", "tel:")):
            # Anchors, mailto, tel are not validated
            return "unknown"
        else:
            # Assume local file
            return "local"
