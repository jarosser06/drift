"""Validators for file existence, size checks, and token counting."""

from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class FileExistsValidator(BaseValidator):
    """Validator for checking file existence."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:file_exists"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "File {file_path} does not exist"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "File should exist"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if specified file(s) exist.

        Expected params:
            - file_path: File path or glob pattern (required)

        -- rule: ValidationRule with params.file_path (supports glob patterns)
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator
        -- ignore_patterns: Optional list of patterns to ignore (not used by FileExistsValidator)

        Returns DocumentRule if file doesn't exist, None if it does.
        """
        if not rule.params:
            raise ValueError("FileExistsValidator requires params")

        file_path = rule.params.get("file_path")
        if not file_path:
            raise ValueError("FileExistsValidator requires params.file_path")

        project_path = bundle.project_path

        # Check if file_path contains glob patterns
        if "*" in file_path or "?" in file_path:
            # Glob pattern - check if any files match
            matches = list(project_path.glob(file_path))
            matching_files = [m for m in matches if m.is_file()]

            # Check if parent directory structure exists for the glob pattern
            # E.g., for .claude/skills/*/SKILL.md, check if .claude/skills/ exists
            # Extract the parent path before the first wildcard
            parts = file_path.split("/")
            parent_parts = []
            for part in parts:
                if "*" in part or "?" in part:
                    break
                parent_parts.append(part)

            if parent_parts:
                parent_path = project_path / "/".join(parent_parts)
                # If parent doesn't exist, pass (nothing to validate)
                if not (parent_path.exists() and parent_path.is_dir()):
                    return None

                # Check if there are subdirectories that could contain the files
                # For patterns like .claude/skills/*/SKILL.md:
                # - If .claude/skills/ has no subdirectories, pass (nothing to validate)
                # - If .claude/skills/ has subdirectories, fail if no SKILL.md found
                try:
                    # Get the wildcard part to determine what we're looking for
                    wildcard_idx = next(
                        (i for i, p in enumerate(parts) if "*" in p or "?" in p), None
                    )
                    if wildcard_idx is not None and wildcard_idx < len(parts) - 1:
                        # Pattern like */SKILL.md - check for subdirectories
                        has_subdirs = any(p.is_dir() for p in parent_path.iterdir())
                        if not has_subdirs:
                            return None  # No subdirectories, nothing to validate
                    else:
                        # Pattern like *.md - check for any contents
                        has_contents = any(parent_path.iterdir())
                        if not has_contents:
                            return None  # Empty directory, nothing to validate
                except (OSError, PermissionError):
                    # Can't read directory, treat as empty
                    return None

            if matching_files:
                # Files exist - validation passes
                return None
            else:
                # No matching files but parent/subdirs exist - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[file_path],
                )
        else:
            # Specific file path
            file_path_obj = project_path / file_path

            if file_path_obj.exists() and file_path_obj.is_file():
                # File exists - validation passes
                return None
            else:
                # File doesn't exist - validation fails
                return self._create_failure_learning(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[file_path],
                )

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure

        Returns DocumentRule representing the failure.
        """
        # Create failure details for template substitution
        failure_details = {"file_path": file_paths[0] if file_paths else "unknown"}

        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=self._get_failure_message(rule, failure_details),
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
            failure_details=failure_details,
        )


class FileSizeValidator(BaseValidator):
    """Validator for checking file size constraints."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:file_size"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "File size constraint violated"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "File should meet size constraints"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if file meets size constraints.

        Expected params:
            - file_path: File path to validate (optional - if not provided, validates bundle.files)
            - max_count: Maximum number of lines (optional)
            - min_count: Minimum number of lines (optional)
            - max_size: Maximum file size in bytes (optional)
            - min_size: Minimum file size in bytes (optional)

        -- rule: ValidationRule with params containing optional file_path and size constraints
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if constraints violated, None if satisfied.
        """
        # Check params exist
        if not rule.params:
            raise ValueError("FileSizeValidator requires params")

        max_count = rule.params.get("max_count")
        min_count = rule.params.get("min_count")
        max_size = rule.params.get("max_size")
        min_size = rule.params.get("min_size")
        file_path_str = rule.params.get("file_path")

        # At least one constraint must be specified (file_path doesn't count)
        if all(c is None for c in [max_count, min_count, max_size, min_size]):
            raise ValueError(
                "FileSizeValidator requires at least one constraint: "
                "max_count, min_count, max_size, or min_size"
            )

        # If file_path provided, validate that specific file (outside bundle)
        if file_path_str:
            return self._validate_specific_file(
                rule, bundle, file_path_str, max_count, min_count, max_size, min_size
            )

        # Otherwise, validate all files in the bundle
        failed_files = []
        for rel_path, content, abs_path in self._iter_bundle_files(bundle, rule):
            failure = self._validate_file_constraints(
                rel_path, abs_path, content, max_count, min_count, max_size, min_size
            )
            if failure:
                failed_files.append((rel_path, failure))

        if failed_files:
            # Build detailed message
            messages = [f"{path}: {issue}" for path, issue in failed_files]
            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[f[0] for f in failed_files],
                observed_issue="; ".join(messages),
                expected_quality=self._get_expected_behavior(rule),
                rule_type="",
                context=f"Validation rule: {rule.description}",
            )

        return None

    def _validate_specific_file(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_path_str: str,
        max_count: Optional[int],
        min_count: Optional[int],
        max_size: Optional[int],
        min_size: Optional[int],
    ) -> Optional[DocumentRule]:
        """Validate a specific file path (outside bundle).

        -- rule: ValidationRule being executed
        -- bundle: Document bundle for context
        -- file_path_str: Relative path to file to validate
        -- max_count: Maximum line count
        -- min_count: Minimum line count
        -- max_size: Maximum byte size
        -- min_size: Minimum byte size

        Returns DocumentRule if validation fails, None otherwise.
        """
        project_path = bundle.project_path
        file_path = project_path / file_path_str

        if not file_path.exists() or not file_path.is_file():
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=f"File {file_path_str} does not exist",
            )

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=f"Failed to read file: {e}",
            )

        failure = self._validate_file_constraints(
            file_path_str, str(file_path), content, max_count, min_count, max_size, min_size
        )

        if failure:
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=failure,
            )

        return None

    def _validate_file_constraints(
        self,
        rel_path: str,
        abs_path: str,
        content: str,
        max_count: Optional[int],
        min_count: Optional[int],
        max_size: Optional[int],
        min_size: Optional[int],
    ) -> Optional[str]:
        """Validate file against size constraints.

        -- rel_path: Relative path for error messages
        -- abs_path: Absolute path for file operations
        -- content: File content
        -- max_count: Maximum line count
        -- min_count: Minimum line count
        -- max_size: Maximum byte size
        -- min_size: Minimum byte size

        Returns error message if validation fails, None otherwise.
        """
        # Check line count constraints
        if max_count is not None or min_count is not None:
            line_count = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

            if max_count is not None and line_count > max_count:
                return f"File has {line_count} lines (exceeds max {max_count})"

            if min_count is not None and line_count < min_count:
                return f"File has {line_count} lines (below min {min_count})"

        # Check byte size constraints
        if max_size is not None or min_size is not None:
            from pathlib import Path

            file_path = Path(abs_path)
            if file_path.exists():
                byte_size = file_path.stat().st_size

                if max_size is not None and byte_size > max_size:
                    return f"File is {byte_size} bytes (exceeds max {max_size})"

                if min_size is not None and byte_size < min_size:
                    return f"File is {byte_size} bytes (below min {min_size})"

        return None

    def _create_failure(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
        observed_issue: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure
        -- observed_issue: Specific issue observed

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=observed_issue,
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )


class TokenCountValidator(BaseValidator):
    """Validator for checking file token count.

    DEPRECATED: This validator requires provider-specific authentication and dependencies.
    For example, Anthropic token counting requires API credentials, making it unsuitable
    for offline programmatic checks. Use FileSizeValidator with line count (max_count/min_count)
    instead for a general, offline validation approach.

    Supports multiple tokenizer providers:
    - anthropic: For Claude models (requires 'anthropic' package + API credentials)
    - openai: For OpenAI models (requires 'tiktoken' package)
    - llama: For Llama models (requires 'transformers' package)
    """

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "core:token_count"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message template."""
        return "File token count constraint violated"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior description."""
        return "File should meet token count constraints"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if file token count meets constraints.

        Expected params:
            - file_path: File path to validate (required)
            - provider: Tokenizer provider ('anthropic', 'openai', 'llama', default: 'anthropic')
            - max_count: Maximum number of tokens (optional)
            - min_count: Minimum number of tokens (optional)

        -- rule: ValidationRule with params containing file_path, provider, and token constraints
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if constraints violated, None if satisfied.
        """
        if not rule.params:
            raise ValueError("TokenCountValidator requires params")

        file_path_str = rule.params.get("file_path")
        if not file_path_str:
            raise ValueError("TokenCountValidator requires params.file_path")

        provider = rule.params.get("provider", "anthropic")
        if provider not in ["anthropic", "openai", "llama"]:
            raise ValueError(
                f"Unsupported token counter provider: {provider}. "
                "Must be 'anthropic', 'openai', or 'llama'"
            )

        max_count = rule.params.get("max_count")
        min_count = rule.params.get("min_count")

        project_path = bundle.project_path
        file_path = project_path / file_path_str

        if not file_path.exists() or not file_path.is_file():
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=f"File {rule.file_path} does not exist",
            )

        # Read file content
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=f"Failed to read file: {e}",
            )

        # Count tokens using the specified provider
        try:
            token_count = self._count_tokens(content, provider)
        except ImportError as e:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=(
                    f"Token counting failed: {e}. "
                    f"Install required package for '{provider}' provider."
                ),
            )
        except Exception as e:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=f"Token counting failed: {e}",
            )

        # Check constraints
        if max_count is not None and token_count > max_count:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=(
                    f"File has {token_count} tokens "
                    f"(exceeds max {max_count}) using {provider} tokenizer"
                ),
            )

        if min_count is not None and token_count < min_count:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[file_path_str],
                observed_issue=(
                    f"File has {token_count} tokens "
                    f"(below min {min_count}) using {provider} tokenizer"
                ),
            )

        # All constraints satisfied
        return None

    def _count_tokens(self, text: str, provider: str) -> int:
        """Count tokens using the specified provider.

        -- text: Text to count tokens for
        -- provider: Token counter provider ('anthropic', 'openai', 'llama')

        Returns token count.
        Raises ImportError if required library not installed.
        """
        if provider == "anthropic":
            try:
                from anthropic import Anthropic
            except ImportError:
                raise ImportError(
                    "Anthropic token counting requires 'anthropic' package. "
                    "Install with: pip install anthropic"
                )

            client = Anthropic()
            # Use the new beta messages.count_tokens API (Nov 2024+)
            # https://docs.claude.com/en/api/messages-count-tokens
            response = client.beta.messages.count_tokens(
                betas=["token-counting-2024-11-01"],
                model="claude-sonnet-4-5-20250929",  # Use Claude Sonnet 4.5
                messages=[{"role": "user", "content": text}],
            )
            return response.input_tokens

        elif provider == "openai":
            try:
                import tiktoken
            except ImportError:
                raise ImportError(
                    "OpenAI token counting requires 'tiktoken' package. "
                    "Install with: pip install tiktoken"
                )

            # Use GPT-4 tokenizer as default
            encoding = tiktoken.encoding_for_model("gpt-4")
            return len(encoding.encode(text))

        elif provider == "llama":
            try:
                from transformers import AutoTokenizer
            except ImportError:
                raise ImportError(
                    "Llama token counting requires 'transformers' package. "
                    "Install with: pip install transformers"
                )

            # Use Llama-2 tokenizer as default
            tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")
            return len(tokenizer.encode(text))

        else:
            raise ValueError(f"Unsupported provider: {provider}")

    def _create_token_failure(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        file_paths: List[str],
        observed_issue: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure
        -- observed_issue: Specific issue observed

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=file_paths,
            observed_issue=observed_issue,
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )
