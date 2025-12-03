"""Validators for markdown content validation."""

from pathlib import Path as PathLib
from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.utils.link_validator import LinkValidator
from drift.validation.validators.base import BaseValidator


class MarkdownLinkValidator(BaseValidator):
    """Validator for checking links in markdown content."""

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate all links in markdown files.

        -- rule: ValidationRule with params for link types to check
        -- bundle: Document bundle being validated
        -- all_bundles: Not used

        Returns DocumentRule if broken links found, None otherwise.
        """
        # Extract params
        check_local_files = rule.params.get("check_local_files", True)
        check_external_urls = rule.params.get("check_external_urls", True)
        check_resource_refs = rule.params.get("check_resource_refs", False)
        resource_patterns = rule.params.get("resource_patterns", [])

        # Extract filtering params (with defaults matching LinkValidator defaults)
        skip_example_domains = rule.params.get("skip_example_domains", True)
        skip_code_blocks = rule.params.get("skip_code_blocks", True)
        skip_placeholder_paths = rule.params.get("skip_placeholder_paths", True)
        custom_skip_patterns = rule.params.get("custom_skip_patterns", [])

        validator = LinkValidator(
            skip_example_domains=skip_example_domains,
            skip_code_blocks=skip_code_blocks,
            skip_placeholder_paths=skip_placeholder_paths,
            custom_skip_patterns=custom_skip_patterns,
        )
        broken_links = []

        for file in bundle.files:
            file_path = PathLib(file.file_path)
            file_dir = file_path.parent

            # Extract all file references from content (markdown links and plain paths)
            file_refs = validator.extract_all_file_references(file.content)

            for ref in file_refs:
                # Categorize the reference
                link_type = validator.categorize_link(ref)

                # Validate based on type and settings
                if link_type == "local" and check_local_files:
                    # Try both relative to file's directory and project root
                    # First try relative to file's directory (for local resources)
                    found_relative_to_file = validator.validate_local_file(ref, file_dir)
                    # Then try relative to project root (for project-wide references)
                    found_relative_to_project = validator.validate_local_file(
                        ref, bundle.project_path
                    )

                    # Only report as broken if not found in either location
                    if not found_relative_to_file and not found_relative_to_project:
                        broken_links.append((file.relative_path, ref, "local file not found"))
                elif link_type == "external" and check_external_urls:
                    if not validator.validate_external_url(ref):
                        broken_links.append((file.relative_path, ref, "external URL unreachable"))

            # Also check resource references if enabled
            if check_resource_refs and resource_patterns:
                # Extract markdown links for resource checking
                markdown_links = validator.extract_links(file.content)

                for link_text, link_url in markdown_links:
                    # Check if link matches any resource pattern
                    import re

                    for pattern in resource_patterns:
                        match = re.search(pattern, link_text)
                        if match:
                            # Extract resource name from match
                            resource_name = match.group(1) if match.groups() else link_text
                            # Try to determine resource type
                            resource_type = self._guess_resource_type(pattern)
                            if resource_type:
                                if not validator.validate_resource_reference(
                                    resource_name, bundle.project_path, resource_type
                                ):
                                    broken_links.append(
                                        (
                                            file.relative_path,
                                            resource_name,
                                            f"{resource_type} reference not found",
                                        )
                                    )

        if broken_links:
            # Build detailed message
            messages = []
            for file_rel_path, link, reason in broken_links:
                messages.append(f"{file_rel_path}: [{link}] - {reason}")

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=list(set(bl[0] for bl in broken_links)),
                observed_issue=rule.failure_message + ": " + "; ".join(messages),
                expected_quality=rule.expected_behavior,
                rule_type="",
                context=f"Validation rule: {rule.description}",
            )

        return None

    def _guess_resource_type(self, pattern: str) -> Optional[str]:
        """Guess resource type from pattern.

        -- pattern: Regex pattern used to match resource

        Returns resource type (skill, command, agent) or None.
        """
        pattern_lower = pattern.lower()
        if "skill" in pattern_lower:
            return "skill"
        elif "command" in pattern_lower or "/" in pattern_lower:
            return "command"
        elif "agent" in pattern_lower:
            return "agent"
        return None
