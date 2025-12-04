"""Validators for file existence, size checks, and token counting."""

from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class FileExistsValidator(BaseValidator):
    """Validator for checking file existence."""

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
        """Check if specified file(s) exist.

        -- rule: ValidationRule with file_path (supports glob patterns)
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if file doesn't exist, None if it does.
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

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- file_paths: List of file paths involved in the failure

        Returns DocumentRule representing the failure.
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


class FileSizeValidator(BaseValidator):
    """Validator for checking file size constraints."""

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
        """Check if file meets size constraints.

        Supports both line count and byte size validation:
        - max_count: Maximum number of lines
        - min_count: Minimum number of lines
        - max_size: Maximum file size in bytes
        - min_size: Minimum file size in bytes

        -- rule: ValidationRule with file_path and size constraints
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if constraints violated, None if satisfied.
        """
        if not rule.file_path:
            raise ValueError("FileSizeValidator requires rule.file_path")

        project_path = bundle.project_path
        file_path = project_path / rule.file_path

        if not file_path.exists() or not file_path.is_file():
            return self._create_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"File {rule.file_path} does not exist",
            )

        # Check line count constraints
        if rule.max_count is not None or rule.min_count is not None:
            with open(file_path, "r", encoding="utf-8") as f:
                line_count = sum(1 for _ in f)

            if rule.max_count is not None and line_count > rule.max_count:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    observed_issue=f"File has {line_count} lines (exceeds max {rule.max_count})",
                )

            if rule.min_count is not None and line_count < rule.min_count:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    observed_issue=f"File has {line_count} lines (below min {rule.min_count})",
                )

        # Check byte size constraints
        if rule.max_size is not None or rule.min_size is not None:
            byte_size = file_path.stat().st_size

            if rule.max_size is not None and byte_size > rule.max_size:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    observed_issue=f"File is {byte_size} bytes (exceeds max {rule.max_size})",
                )

            if rule.min_size is not None and byte_size < rule.min_size:
                return self._create_failure(
                    rule=rule,
                    bundle=bundle,
                    file_paths=[rule.file_path],
                    observed_issue=f"File is {byte_size} bytes (below min {rule.min_size})",
                )

        # All constraints satisfied
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
            expected_quality=rule.expected_behavior,
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
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check if file token count meets constraints.

        Requires a 'provider' parameter in rule.params specifying the tokenizer:
        - 'anthropic' (default for Claude)
        - 'openai' (for GPT models)
        - 'llama' (for Llama models)

        Supports:
        - max_count: Maximum number of tokens
        - min_count: Minimum number of tokens

        -- rule: ValidationRule with file_path, provider, and token constraints
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if constraints violated, None if satisfied.
        """
        if not rule.file_path:
            raise ValueError("TokenCountValidator requires rule.file_path")

        # Get provider from params (default to anthropic for Claude)
        provider = rule.params.get("provider", "anthropic") if rule.params else "anthropic"

        if provider not in ["anthropic", "openai", "llama"]:
            raise ValueError(
                f"Unsupported token counter provider: {provider}. "
                "Must be 'anthropic', 'openai', or 'llama'"
            )

        project_path = bundle.project_path
        file_path = project_path / rule.file_path

        if not file_path.exists() or not file_path.is_file():
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
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
                file_paths=[rule.file_path],
                observed_issue=f"Failed to read file: {e}",
            )

        # Count tokens using the specified provider
        try:
            token_count = self._count_tokens(content, provider)
        except ImportError as e:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=(
                    f"Token counting failed: {e}. "
                    f"Install required package for '{provider}' provider."
                ),
            )
        except Exception as e:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=f"Token counting failed: {e}",
            )

        # Check constraints
        if rule.max_count is not None and token_count > rule.max_count:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=(
                    f"File has {token_count} tokens "
                    f"(exceeds max {rule.max_count}) using {provider} tokenizer"
                ),
            )

        if rule.min_count is not None and token_count < rule.min_count:
            return self._create_token_failure(
                rule=rule,
                bundle=bundle,
                file_paths=[rule.file_path],
                observed_issue=(
                    f"File has {token_count} tokens "
                    f"(below min {rule.min_count}) using {provider} tokenizer"
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
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}",
        )
