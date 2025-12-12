"""Document loader for analyzing project documentation."""

import hashlib
from pathlib import Path
from typing import List

from drift.config.models import BundleStrategy, DocumentBundleConfig
from drift.core.types import DocumentBundle, DocumentFile


class DocumentLoader:
    """Loads and processes document bundles for analysis."""

    def __init__(self, project_path: Path):
        """Initialize document loader.

        Args:
            project_path: Root path of the project
        """
        self.project_path = Path(project_path)

    def list_resources(self, resource_type: str) -> List[str]:
        """List available resources of a given type.

        Args:
            resource_type: Type of resource (skill, command, agent, rule, etc.)

        Returns:
            List of resource identifiers (e.g., skill names, command names)
        """
        # Map resource types to common patterns
        patterns_map = {
            "skill": [".claude/skills/*/SKILL.md", ".claude/skills/*/skill.md"],
            "command": [".claude/commands/*.md"],
            "agent": [".claude/agents/*/AGENT.md", ".claude/agents/*/agent.md"],
            "rule": [".claude/rules/**/*.md"],
        }

        patterns = patterns_map.get(resource_type, [])
        if not patterns:
            return []

        resource_names = []
        for pattern in patterns:
            matches = self.project_path.glob(pattern)
            for match in matches:
                if match.is_file():
                    # Extract resource name from path
                    if resource_type in ["skill", "agent"]:
                        # For skills/agents, use parent directory name
                        resource_names.append(match.parent.name)
                    elif resource_type in ["command", "rule"]:
                        # For commands/rules, use filename without extension
                        resource_names.append(match.stem)

        return sorted(set(resource_names))

    def load_bundles(self, bundle_config: DocumentBundleConfig) -> List[DocumentBundle]:
        """Load document bundles based on configuration.

        Args:
            bundle_config: Configuration specifying how to load bundles

        Returns:
            List of document bundles ready for analysis
        """
        # Discover main files matching patterns
        main_files = self._discover_files(bundle_config.file_patterns)

        if not main_files:
            return []

        if bundle_config.bundle_strategy == BundleStrategy.INDIVIDUAL:
            # Each file becomes its own bundle (with optional resources)
            return self._create_individual_bundles(main_files, bundle_config)
        else:
            # All files combined into single bundle
            return self._create_collection_bundle(main_files, bundle_config)

    def _create_individual_bundles(
        self, main_files: List[Path], bundle_config: DocumentBundleConfig
    ) -> List[DocumentBundle]:
        """Create individual bundles, one per main file.

        Args:
            main_files: List of main document files
            bundle_config: Bundle configuration

        Returns:
            List of individual document bundles
        """
        bundles = []

        for main_file in main_files:
            files = [self._create_document_file(main_file)]

            # If resource patterns specified, find resources relative to main file's directory
            if bundle_config.resource_patterns:
                resource_files = self._discover_resources(
                    main_file, bundle_config.resource_patterns
                )
                files.extend([self._create_document_file(f) for f in resource_files])

            bundle_id = self._generate_bundle_id(main_file)
            bundles.append(
                DocumentBundle(
                    bundle_id=bundle_id,
                    bundle_type=bundle_config.bundle_type,
                    bundle_strategy=bundle_config.bundle_strategy.value,
                    files=files,
                    project_path=self.project_path,
                )
            )

        return bundles

    def _create_collection_bundle(
        self, main_files: List[Path], bundle_config: DocumentBundleConfig
    ) -> List[DocumentBundle]:
        """Create a single collection bundle from all files.

        Args:
            main_files: List of main document files
            bundle_config: Bundle configuration

        Returns:
            List containing single collection bundle
        """
        files = [self._create_document_file(f) for f in main_files]

        # Resource patterns don't make sense for collections (unclear which directory to use)
        # User should include resource files explicitly in file_patterns if needed

        bundle_id = self._generate_bundle_id(*main_files)
        bundle = DocumentBundle(
            bundle_id=bundle_id,
            bundle_type=bundle_config.bundle_type,
            bundle_strategy=bundle_config.bundle_strategy.value,
            files=files,
            project_path=self.project_path,
        )

        return [bundle]

    def _discover_files(self, patterns: List[str]) -> List[Path]:
        """Find files matching glob patterns relative to project root.

        Args:
            patterns: List of glob patterns (e.g., ".claude/skills/*/SKILL.md")

        Returns:
            List of absolute paths to matching files
        """
        found_files = []

        for pattern in patterns:
            # Glob from project root
            matches = self.project_path.glob(pattern)
            for match in matches:
                if match.is_file():
                    found_files.append(match)

        # Remove duplicates and sort by path
        # Use string representation for deduplication to handle case-insensitive
        # filesystems (e.g., macOS) where different case patterns may match same file
        seen = set()
        unique_files = []
        for file_path in found_files:
            # Normalize by converting to lowercase for comparison on case-insensitive systems
            key = str(file_path).lower()
            if key not in seen:
                seen.add(key)
                # On case-insensitive filesystems, glob returns the pattern's casing, not the file's
                # Get the actual filesystem casing by listing the parent directory
                try:
                    parent = file_path.parent
                    actual_name = None
                    for item in parent.iterdir():
                        if item.name.lower() == file_path.name.lower():
                            actual_name = item.name
                            break

                    if actual_name and actual_name != file_path.name:
                        # Use the actual filesystem casing
                        actual_path = parent / actual_name
                        unique_files.append(actual_path)
                    else:
                        unique_files.append(file_path)
                except (OSError, RuntimeError):
                    # If reading directory fails, fall back to original path
                    unique_files.append(file_path)

        return sorted(unique_files)

    def _discover_resources(self, main_file: Path, resource_patterns: List[str]) -> List[Path]:
        """Find resource files relative to a main file's directory.

        Args:
            main_file: The main document file
            resource_patterns: Glob patterns for resources (e.g., "**/*.py")

        Returns:
            List of resource file paths
        """
        resource_dir = main_file.parent
        found_resources = []

        for pattern in resource_patterns:
            matches = resource_dir.glob(pattern)
            for match in matches:
                # Skip the main file itself
                if match.is_file() and match != main_file:
                    found_resources.append(match)

        return sorted(set(found_resources))

    def _create_document_file(self, file_path: Path) -> DocumentFile:
        """Create a DocumentFile from a path.

        Args:
            file_path: Absolute path to the file

        Returns:
            DocumentFile with loaded content
        """
        relative_path = str(file_path.relative_to(self.project_path))
        content = self._load_file_content(file_path)

        return DocumentFile(
            relative_path=relative_path,
            content=content,
            file_path=file_path,
        )

    def _load_file_content(self, file_path: Path) -> str:
        """Read file content with error handling.

        Args:
            file_path: Path to file to read

        Returns:
            File content as string
        """
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try fallback encoding
            try:
                return file_path.read_text(encoding="latin-1")
            except Exception as e:
                return f"[Error reading file: {e}]"
        except Exception as e:
            return f"[Error reading file: {e}]"

    def _generate_bundle_id(self, *files: Path) -> str:
        """Generate a unique bundle ID from file paths.

        Args:
            *files: One or more file paths

        Returns:
            Unique bundle identifier
        """
        # Create stable hash from file paths
        paths_str = "|".join(str(f.relative_to(self.project_path)) for f in files)
        return hashlib.md5(paths_str.encode()).hexdigest()[:12]

    def format_bundle_for_llm(self, bundle: DocumentBundle) -> str:
        """Format bundle content for LLM analysis.

        Args:
            bundle: Document bundle to format

        Returns:
            Formatted string with file paths and contents
        """
        lines = []
        for file in bundle.files:
            lines.append(f"{file.relative_path}:")
            lines.append(file.content)
            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)
