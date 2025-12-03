"""Markdown link validation utilities."""

import re
from pathlib import Path
from typing import List, Optional, Tuple

import requests

# RFC 2606 reserved example domains and localhost addresses
EXAMPLE_DOMAINS = {
    "example.com",
    "example.org",
    "example.net",
    "example.edu",
    "test.com",
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
}

# Patterns that indicate placeholder/example file paths
PLACEHOLDER_PATH_PATTERNS = [
    r"\bpath/to/",  # path/to/file.py
    r"\byour-[^/]+/",  # your-project/src
    r"\bmy-[^/]+/",  # my-app/config
    r"\{[^}]+\}",  # {variable}/path
    r"\$\{[^}]+\}",  # ${VAR}/path
    r"<[^>]+>",  # <something>/path
]


class LinkValidator:
    """Validate various types of markdown links.

    This class provides utilities to extract and validate links from
    markdown content, including local files, external URLs, and resource
    references. Supports filtering of example/placeholder links to reduce
    false positives.

    Example:
        >>> validator = LinkValidator()
        >>> links = validator.extract_links("[doc](file.md)")
        >>> for text, url in links:
        ...     print(f"{text}: {url}")
        doc: file.md

    Args:
        skip_example_domains: Skip RFC 2606 example domains (default: True)
        skip_code_blocks: Skip links in code blocks (default: True)
        skip_placeholder_paths: Skip placeholder patterns like path/to/ (default: True)
        custom_skip_patterns: List of custom regex patterns to skip (default: empty)

    Attributes:
        skip_example_domains: Whether to skip example domains
        skip_code_blocks: Whether to skip code blocks
        skip_placeholder_paths: Whether to skip placeholder paths
        custom_skip_patterns: List of custom skip patterns
    """

    def __init__(
        self,
        skip_example_domains: bool = True,
        skip_code_blocks: bool = True,
        skip_placeholder_paths: bool = True,
        custom_skip_patterns: Optional[List[str]] = None,
    ) -> None:
        """Initialize LinkValidator with filtering options.

        Args:
            skip_example_domains: Skip RFC 2606 example domains (example.com, localhost, etc.)
            skip_code_blocks: Skip links found in code blocks
            skip_placeholder_paths: Skip placeholder patterns (path/to/, your-*, etc.)
            custom_skip_patterns: Custom regex patterns for links/paths to skip
        """
        self.skip_example_domains = skip_example_domains
        self.skip_code_blocks = skip_code_blocks
        self.skip_placeholder_paths = skip_placeholder_paths
        self.custom_skip_patterns = custom_skip_patterns or []

    def _remove_code_blocks(self, content: str) -> str:
        """Remove code blocks and inline code from markdown content.

        Removes fenced code blocks (```), indented code blocks (4 spaces or tab),
        and inline code (`...`) to prevent extraction of links from example code.

        Args:
            content: Markdown content to process

        Returns:
            Content with code blocks and inline code removed
        """
        # Remove fenced code blocks (```...```)
        # Match from ``` to closing ``` including language specifier
        content = re.sub(r"^```.*?^```\s*$", "", content, flags=re.MULTILINE | re.DOTALL)

        # Remove indented code blocks (4 spaces or tab at line start)
        content = re.sub(r"^(    |\t).*$", "", content, flags=re.MULTILINE)

        # Remove inline code (`...`)
        # This prevents extraction of file paths wrapped in backticks
        content = re.sub(r"`[^`]+`", "", content)

        return content

    def _remove_placeholder_patterns(self, content: str) -> str:
        """Remove placeholder patterns from content before extraction.

        This prevents partial extraction of paths that contain placeholder markers.
        For example, {variable}/path/file.py should not extract path/file.py.

        Args:
            content: Content to process

        Returns:
            Content with placeholder patterns removed
        """
        # Remove lines or segments containing placeholder markers
        # This prevents extraction of fragments after the placeholder
        for pattern in PLACEHOLDER_PATH_PATTERNS:
            # For path prefix patterns, remove the entire path that follows
            if pattern in (r"\bpath/to/", r"\byour-[^/]+/", r"\bmy-[^/]+/"):
                # Match the pattern plus any path that follows (non-whitespace)
                extended = pattern.rstrip("/") + r"[^\s]*"
                content = re.sub(extended, "", content)
            # For template variable patterns, also remove any path that follows
            elif pattern in (r"\{[^}]+\}", r"\$\{[^}]+\}", r"<[^>]+>"):
                # Match the template variable plus optional following path
                extended = pattern + r"[^\s]*"
                content = re.sub(extended, "", content)
            else:
                # For other patterns, just remove them as-is
                content = re.sub(pattern, "", content)

        return content

    def _is_example_domain(self, link: str) -> bool:
        """Check if link uses an example/test domain.

        Checks against RFC 2606 reserved domains and localhost addresses.
        Supports subdomain matching (api.example.com matches example.com).

        Args:
            link: URL or link to check

        Returns:
            True if link uses an example domain, False otherwise
        """
        # Extract domain from various link formats
        # Handle http://, https://, mailto:, and plain domains
        domain_pattern = r"(?:https?://|mailto:)?([^/:@]+(?:\.[^/:@]+)*)"
        match = re.search(domain_pattern, link)

        if not match:
            return False

        domain = match.group(1).lower()

        # Check if domain or any parent domain is in EXAMPLE_DOMAINS
        # This handles subdomains like api.example.com
        parts = domain.split(".")
        for i in range(len(parts)):
            candidate = ".".join(parts[i:])
            if candidate in EXAMPLE_DOMAINS:
                return True

        return False

    def _is_placeholder_path(self, path: str) -> bool:
        """Check if path matches placeholder patterns.

        Detects common placeholder patterns like path/to/, your-project/, etc.

        Args:
            path: File path to check

        Returns:
            True if path appears to be a placeholder, False otherwise
        """
        for pattern in PLACEHOLDER_PATH_PATTERNS:
            if re.search(pattern, path):
                return True
        return False

    def _matches_custom_pattern(self, link: str) -> bool:
        """Check if link matches any custom skip patterns.

        Args:
            link: Link or path to check

        Returns:
            True if link matches a custom pattern, False otherwise
        """
        for pattern in self.custom_skip_patterns:
            try:
                if re.search(pattern, link):
                    return True
            except re.error:
                # Silently skip invalid regex patterns
                continue
        return False

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

        Applies filtering based on instance configuration to skip example/placeholder
        links and reduce false positives.

        Args:
            content: Content to parse

        Returns:
            List of file path strings found in content
        """
        # Apply code block filtering if enabled
        if self.skip_code_blocks:
            content = self._remove_code_blocks(content)

        # Apply placeholder pattern removal if enabled
        # This must happen before extraction to prevent partial matches
        if self.skip_placeholder_paths:
            content = self._remove_placeholder_patterns(content)

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
        # - Nested paths: path/to/file.ext
        # Note: Absolute paths like /etc/config.yaml are NOT extracted (usually system paths)
        path_patterns = [
            # Relative paths starting with ./ or ../ (most reliable indicator)
            r"\.{1,2}/[\w\-./]+",
            # Paths with slashes and file extensions: path/to/file.ext
            # Require whitespace or start of string before the path to avoid matching
            # paths that are part of absolute paths like /etc/config.yaml
            r"(?:^|(?<=\s))[\w\-]+(?:/[\w\-]+)+\.[\w]+\b",
            # Standalone filenames with common extensions: README.md, test.py
            # Only match if NOT preceded by a slash or word char
            # (to avoid matching file.py from path/to/file.py)
            r"(?<![/\w\-])[\w\-]{1,50}\.(?:md|py|js|ts|tsx|jsx|yaml|yml|json|sh|bash|txt|csv|xml"
            r"|html|css|rs|go|java|rb|php|c|cpp|h|hpp|toml|ini|conf|cfg)\b",
        ]

        for pattern in path_patterns:
            matches = re.findall(pattern, content_without_urls)
            references.extend(matches)

        # Apply filtering to remove example/placeholder references
        filtered_refs = []
        for ref in references:
            # Don't filter "unknown" type links (anchors, mailto, tel) - they're skipped anyway
            if ref.startswith(("#", "mailto:", "tel:")):
                filtered_refs.append(ref)
                continue

            # Skip if matches example domain filter
            if self.skip_example_domains and self._is_example_domain(ref):
                continue

            # Skip if matches placeholder path filter
            if self.skip_placeholder_paths and self._is_placeholder_path(ref):
                continue

            # Skip if matches custom pattern filter
            if self._matches_custom_pattern(ref):
                continue

            filtered_refs.append(ref)

        # Remove duplicates while preserving order
        seen = set()
        unique_refs = []
        for ref in filtered_refs:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)

        return unique_refs

    def validate_local_file(self, link: str, base_path: Path) -> bool:
        """Check if local file or directory exists.

        Resolves relative paths from the base_path and checks if the
        file or directory exists in the filesystem.

        Args:
            link: Relative or absolute file/directory path
            base_path: Base directory to resolve relative paths from

        Returns:
            True if file or directory exists, False otherwise
        """
        # Handle absolute paths
        if link.startswith("/"):
            file_path = Path(link)
        else:
            # Resolve relative to base_path
            file_path = (base_path / link).resolve()

        # Accept both files and directories as valid
        return file_path.exists()

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
