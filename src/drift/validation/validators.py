"""Validators for rule-based document validation."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Optional

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.params import ParamResolver


class BaseValidator(ABC):
    """Abstract base class for all validators."""

    def __init__(self, loader: Any = None):
        """Initialize validator.

        Args:
            loader: Optional document loader for resource access
        """
        self.loader = loader

    @abstractmethod
    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Execute validation rule.

        Args:
            rule: The validation rule to execute
            bundle: The document bundle to validate
            all_bundles: Optional list of all bundles (for cross-bundle validation)

        Returns:
            DocumentRule if validation fails, None if passes
        """
        pass


class FileExistsValidator(BaseValidator):
    """Validator for checking file existence."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if specified file(s) exist.

        Args:
            rule: ValidationRule with file_path (supports glob patterns)
            bundle: Document bundle being validated
            all_bundles: Not used for this validator

        Returns:
            DocumentRule if file doesn't exist, None if it does
        """
        if not rule.file_path:
            raise ValueError("FileExistsValidator requires rule.file_path")

        project_path = bundle.project_path

        # Check if file_path contains glob patterns
        if "*" in rule.file_path or "?" in rule.file_path:
            # Glob pattern - check if any files match
            matches = list(project_path.glob(rule.file_path))
            matching_files = [m for m in matches if m.is_file()]

            if matching_files:
                # Files exist - validation passes
                return None
            else:
                # No matching files - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                )
        else:
            # Specific file path
            file_path = project_path / rule.file_path

            if file_path.exists() and file_path.is_file():
                # File exists - validation passes
                return None
            else:
                # File doesn't exist - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                )

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        Args:
            rule: The validation rule that failed
            bundle: The document bundle being validated
            file_paths: List of file paths involved in the failure

        Returns:
            DocumentRule representing the failure
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )


class RegexMatchValidator(BaseValidator):
    """Validator for checking if file content matches a regex pattern."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if file content matches the specified regex pattern.

        Args:
            rule: ValidationRule with file_path and pattern
            bundle: Document bundle being validated
            all_bundles: Not used for this validator

        Returns:
            DocumentRule if pattern doesn't match, None if it does
        """
        import re

        if not rule.file_path:
            raise ValueError("RegexMatchValidator requires rule.file_path")
        if not rule.pattern:
            raise ValueError("RegexMatchValidator requires rule.pattern")

        project_path = bundle.project_path
        file_path = project_path / rule.file_path

        # Check if file exists
        if not file_path.exists() or not file_path.is_file():
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                context=f"File not found: {rule.file_path}",
            )

        # Read file content
        try:
            content = file_path.read_text()
        except Exception as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                context=f"Failed to read file: {e}",
            )

        # Compile and search for pattern
        try:
            flags = rule.flags or 0
            pattern = re.compile(rule.pattern, flags)
            if pattern.search(content):
                # Pattern found - validation passes
                return None
            else:
                # Pattern not found - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    context=f"Pattern '{rule.pattern}' not found in file",
                )
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
        context: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        Args:
            rule: The validation rule that failed
            bundle: The document bundle being validated
            file_paths: List of file paths involved in the failure
            context: Additional context about the failure

        Returns:
            DocumentRule representing the failure
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class ListMatchValidator(BaseValidator):
    """Validator for checking if list items match expected values."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if list items match expected values.

        Expected params:
            - items: List to check (can be string_list or resource_list)
            - target: List to compare against (can be string_list, resource_list, or file_content)
            - match_mode: "all_in", "none_in", "exact" (default: "all_in")

        Args:
            rule: ValidationRule with params
            bundle: Document bundle being validated
            all_bundles: Not used for this validator

        Returns:
            DocumentRule if validation fails, None if passes
        """
        resolver = ParamResolver(bundle, self.loader)

        try:
            # Resolve parameters
            items_spec = rule.params.get("items")
            target_spec = rule.params.get("target")
            match_mode = rule.params.get("match_mode", "all_in")

            if not items_spec or not target_spec:
                raise ValueError("ListMatchValidator requires 'items' and 'target' params")

            items = resolver.resolve(items_spec)
            target = resolver.resolve(target_spec)

            # Ensure both are lists
            if not isinstance(items, list):
                items = [items]
            if not isinstance(target, list):
                target = [target]

            # Perform match based on mode
            if match_mode == "all_in":
                # All items must be in target
                missing = [item for item in items if item not in target]
                if missing:
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Items not found in target: {', '.join(missing)}",
                    )
            elif match_mode == "none_in":
                # No items should be in target
                found = [item for item in items if item in target]
                if found:
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Items found in target but should not be: {', '.join(found)}",
                    )
            elif match_mode == "exact":
                # Lists must be exactly the same (order-independent)
                if set(items) != set(target):
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Lists do not match exactly. Items: {items}, Target: {target}",
                    )
            else:
                raise ValueError(f"Unknown match_mode: {match_mode}")

            return None

        except Exception as e:
            raise ValueError(f"ListMatchValidator error: {e}")

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        context: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure."""
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[f.relative_path for f in bundle.files],
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class ListRegexMatchValidator(BaseValidator):
    """Validator for checking if list items match regex patterns in files."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if list items match regex patterns in target files.

        Expected params:
            - items: List to check (can be string_list or resource_list)
            - file_path: File path to search in (can be string or file_content)
            - pattern: Regex pattern to extract matches from file
            - match_mode: "all_in", "none_in" (default: "all_in")

        Args:
            rule: ValidationRule with params
            bundle: Document bundle being validated
            all_bundles: Not used for this validator

        Returns:
            DocumentRule if validation fails, None if passes
        """
        resolver = ParamResolver(bundle, self.loader)

        try:
            # Resolve parameters
            items_spec = rule.params.get("items")
            file_path_spec = rule.params.get("file_path")
            pattern_spec = rule.params.get("pattern")
            match_mode = rule.params.get("match_mode", "all_in")

            if not items_spec or not file_path_spec or not pattern_spec:
                raise ValueError(
                    "ListRegexMatchValidator requires 'items', 'file_path', and 'pattern' params"
                )

            items = resolver.resolve(items_spec)
            pattern = resolver.resolve(pattern_spec)

            # Resolve file content
            if isinstance(file_path_spec, dict) and file_path_spec.get("type") == "file_content":
                file_content = resolver.resolve(file_path_spec)
            else:
                # Legacy: file_path is a string path
                file_path = resolver.resolve({"type": "string", "value": file_path_spec})
                file_content = resolver.resolve({"type": "file_content", "value": file_path})

            # Ensure items is a list
            if not isinstance(items, list):
                items = [items]

            # Extract matches from file content using pattern
            matches = pattern.findall(file_content)
            matches = list(set(matches))  # Remove duplicates

            # Perform match based on mode
            if match_mode == "all_in":
                # All items must be found in matches
                missing = [item for item in items if item not in matches]
                if missing:
                    missing_items = ", ".join(missing)
                    found_items = ", ".join(matches)
                    context_msg = f"Items not found in file: {missing_items}. Found: {found_items}"
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=context_msg,
                    )
            elif match_mode == "none_in":
                # No items should be found in matches
                found = [item for item in items if item in matches]
                if found:
                    return self._create_failure_learning(
                        rule=rule,
                        bundle=bundle,
                        context=f"Items found in file but should not be: {', '.join(found)}",
                    )
            else:
                raise ValueError(f"Unknown match_mode: {match_mode}")

            return None

        except Exception as e:
            raise ValueError(f"ListRegexMatchValidator error: {e}")

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        context: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure."""
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[f.relative_path for f in bundle.files],
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class DependencyDuplicateValidator(BaseValidator):
    """Validator for detecting duplicate dependencies in Claude Code resources."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Detect duplicate resource declarations in dependency chain.

        Args:
            rule: ValidationRule with params for agent_tool and resource_dirs
            bundle: Document bundle being validated (command/skill/agent)
            all_bundles: List of all bundles (needed for cross-bundle analysis)

        Returns:
            DocumentRule if duplicates found, None otherwise
        """
        from pathlib import Path

        from drift.utils.dependency_graph import DependencyGraph

        # Extract params
        # agent_tool = rule.params.get("agent_tool", "claude-code")  # For future use
        resource_dirs = rule.params.get("resource_dirs", [])

        if not all_bundles:
            # Need all bundles for cross-bundle analysis
            return None

        if not resource_dirs:
            raise ValueError("DependencyDuplicateValidator requires 'resource_dirs' param")

        # Build dependency graph from all bundles
        project_path = bundle.project_path
        graph = DependencyGraph(project_path)

        # Load all resources from all bundles
        for b in all_bundles:
            for file in b.files:
                # Determine resource type from path
                file_path = Path(file.file_path)
                resource_type = self._determine_resource_type(file_path)
                if resource_type:
                    try:
                        graph.load_resource(file_path, resource_type)
                    except Exception:
                        # Skip files that can't be loaded
                        continue

        # Check current bundle for duplicates
        duplicates_found = []
        for file in bundle.files:
            file_path = Path(file.file_path)
            resource_type = self._determine_resource_type(file_path)
            if not resource_type:
                continue

            resource_id = graph._extract_resource_id(file_path, resource_type)

            try:
                duplicates = graph.find_transitive_duplicates(resource_id)
                if duplicates:
                    for dup_resource, declared_by in duplicates:
                        duplicates_found.append((file.relative_path, dup_resource, declared_by))
            except KeyError:
                # Resource not in graph
                continue

        if duplicates_found:
            # Build detailed message
            messages = []
            for file_rel_path, dup_resource, declared_by in duplicates_found:
                messages.append(
                    f"{file_rel_path}: '{dup_resource}' is redundant "
                    f"(already declared by '{declared_by}')"
                )

            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[d[0] for d in duplicates_found],
                observed_issue=rule.failure_message + ": " + "; ".join(messages),
                expected_quality=rule.expected_behavior,
                rule_type="",
                context=f"Validation rule: {rule.description}",
            )

        return None

    def _determine_resource_type(self, file_path: Path) -> Optional[str]:
        """Determine resource type from file path.

        Args:
            file_path: Path to resource file

        Returns:
            Resource type (skill, command, agent) or None
        """
        path_str = str(file_path)
        if "/skills/" in path_str and file_path.name == "SKILL.md":
            return "skill"
        elif "/commands/" in path_str and file_path.suffix == ".md":
            return "command"
        elif "/agents/" in path_str and file_path.suffix == ".md":
            return "agent"
        return None


class MarkdownLinkValidator(BaseValidator):
    """Validator for checking links in markdown content."""

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate all links in markdown files.

        Args:
            rule: ValidationRule with params for link types to check
            bundle: Document bundle being validated
            all_bundles: Not used

        Returns:
            DocumentRule if broken links found, None otherwise
        """
        from pathlib import Path as PathLib

        from drift.utils.link_validator import LinkValidator

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

        Args:
            pattern: Regex pattern used to match resource

        Returns:
            Resource type (skill, command, agent) or None
        """
        pattern_lower = pattern.lower()
        if "skill" in pattern_lower:
            return "skill"
        elif "command" in pattern_lower or "/" in pattern_lower:
            return "command"
        elif "agent" in pattern_lower:
            return "agent"
        return None


class ValidatorRegistry:
    """Registry mapping rule types to validator implementations."""

    def __init__(self, loader: Any = None) -> None:
        """Initialize registry with available validators.

        Args:
            loader: Optional document loader for resource access
        """
        self._validators = {
            ValidationType.FILE_EXISTS: FileExistsValidator(loader),
            ValidationType.FILE_NOT_EXISTS: FileExistsValidator(loader),
            ValidationType.REGEX_MATCH: RegexMatchValidator(loader),
            ValidationType.LIST_MATCH: ListMatchValidator(loader),
            ValidationType.LIST_REGEX_MATCH: ListRegexMatchValidator(loader),
            ValidationType.DEPENDENCY_DUPLICATE: DependencyDuplicateValidator(loader),
            ValidationType.MARKDOWN_LINK: MarkdownLinkValidator(loader),
        }

    def execute_rule(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Execute a validation rule.

        Args:
            rule: The validation rule to execute
            bundle: The document bundle to validate
            all_bundles: Optional list of all bundles

        Returns:
            DocumentRule if validation fails, None if passes

        Raises:
            ValueError: If rule type is not supported
        """
        if rule.rule_type not in self._validators:
            raise ValueError(f"Unsupported validation rule type: {rule.rule_type}")

        validator = self._validators[rule.rule_type]
        result = validator.validate(rule, bundle, all_bundles)

        # Handle inverted rules (NOT_EXISTS, NOT_MATCH)
        if rule.rule_type == ValidationType.FILE_NOT_EXISTS:
            return self._invert_result(result, rule, bundle)

        return result

    def _invert_result(
        self,
        result: Optional[DocumentRule],
        rule: ValidationRule,
        bundle: DocumentBundle,
    ) -> Optional[DocumentRule]:
        """Invert validation result for NOT rules.

        Args:
            result: Original validation result
            rule: The validation rule
            bundle: The document bundle

        Returns:
            Inverted result (None becomes DocumentRule, DocumentRule becomes None)
        """
        if result is None:
            # Original validation passed (file exists), but we want it NOT to exist
            # So this is a failure
            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[rule.file_path] if rule.file_path else [],
                observed_issue=rule.failure_message,
                expected_quality=rule.expected_behavior,
                rule_type="",  # Will be set by analyzer
                context=f"Validation rule: {rule.description}",
            )
        else:
            # Original validation failed (file doesn't exist), which is what we want
            # So this is a pass
            return None
