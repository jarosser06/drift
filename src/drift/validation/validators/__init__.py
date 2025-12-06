"""Validators for rule-based document validation.

This package provides a modular structure for validators:
- base.py: BaseValidator abstract class
- core/: Core validators for generic validation tasks
- client/: Client-specific validators for tool/platform-specific validation
"""

import importlib
from typing import Any, Dict, List, Optional, Type

from drift.config.models import ClientType, ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator
from drift.validation.validators.client import (
    ClaudeCircularDependenciesValidator,
    ClaudeDependencyDuplicateValidator,
    ClaudeMaxDependencyDepthValidator,
    ClaudeMcpPermissionsValidator,
    ClaudeSettingsDuplicatesValidator,
    ClaudeSkillSettingsValidator,
)
from drift.validation.validators.core import (
    CircularDependenciesValidator,
    DependencyDuplicateValidator,
    FileExistsValidator,
    FileSizeValidator,
    JsonSchemaValidator,
    ListMatchValidator,
    ListRegexMatchValidator,
    MarkdownLinkValidator,
    MaxDependencyDepthValidator,
    RegexMatchValidator,
    TokenCountValidator,
    YamlFrontmatterValidator,
    YamlSchemaValidator,
)


class ValidatorRegistry:
    """Registry mapping namespaced validation types to validator implementations.

    The ValidatorRegistry provides a centralized system for managing validators
    and executing validation rules. Validators use namespaced types (e.g.,
    'core:file_exists', 'security:vulnerability_scan') and can be dynamically
    loaded from external packages.

    Usage Examples:

        Basic validation execution:
        >>> from drift.validation.validators import ValidatorRegistry
        >>> from drift.config.models import ValidationRule
        >>> registry = ValidatorRegistry()
        >>> rule = ValidationRule(
        ...     rule_type="core:file_exists",
        ...     file_path="README.md",
        ...     description="Check README exists",
        ...     failure_message="README.md not found",
        ...     expected_behavior="README.md should exist"
        ... )
        >>> result = registry.execute_rule(rule, bundle)
        >>> if result is None:
        ...     print("Validation passed")

        Query computation type:
        >>> registry.get_computation_type("core:regex_match")
        'programmatic'
        >>> registry.is_programmatic("core:markdown_link")
        True

        Filter programmatic validators for --no-llm mode:
        >>> programmatic_rules = [
        ...     rule for rule in rules
        ...     if registry.is_programmatic(rule.rule_type)
        ... ]

    Attributes:
        _validators: Dictionary mapping namespace:type strings to validator instances
        _loaded_plugins: Cache of dynamically loaded validator classes
    """

    # Singleton cache for loaded plugin classes
    _loaded_plugins: Dict[str, Type[BaseValidator]] = {}

    def __init__(self, loader: Any = None) -> None:
        """Initialize registry with built-in validators.

        -- loader: Optional document loader for resource access
        """
        self.loader = loader
        self._validators: Dict[str, BaseValidator] = {}

        # Register all built-in core validators
        self._register_builtin_validators()

    def _register_builtin_validators(self) -> None:
        """Register all built-in core validators with their namespaced types."""
        builtin_validators = [
            # File validators
            FileExistsValidator(self.loader),
            FileSizeValidator(self.loader),
            TokenCountValidator(self.loader),
            # Format validators
            JsonSchemaValidator(self.loader),
            YamlSchemaValidator(self.loader),
            YamlFrontmatterValidator(self.loader),
            # Pattern validators
            RegexMatchValidator(self.loader),
            ListMatchValidator(self.loader),
            ListRegexMatchValidator(self.loader),
            MarkdownLinkValidator(self.loader),
            # Dependency validators
            DependencyDuplicateValidator(self.loader),
            CircularDependenciesValidator(self.loader),
            MaxDependencyDepthValidator(self.loader),
            # Claude Code validators
            ClaudeDependencyDuplicateValidator(self.loader),
            ClaudeCircularDependenciesValidator(self.loader),
            ClaudeMaxDependencyDepthValidator(self.loader),
            ClaudeSkillSettingsValidator(self.loader),
            ClaudeSettingsDuplicatesValidator(self.loader),
            ClaudeMcpPermissionsValidator(self.loader),
        ]

        for validator in builtin_validators:
            validation_type = validator.validation_type

            # Check for duplicate registrations
            if validation_type in self._validators:
                existing = self._validators[validation_type]
                raise ValueError(
                    f"Validation type '{validation_type}' already registered "
                    f"by {existing.__class__.__name__}. "
                    f"Cannot register {validator.__class__.__name__}."
                )

            self._validators[validation_type] = validator

    def _load_validator(self, provider: str, validation_type: str) -> BaseValidator:
        """Dynamically load a validator from an external provider.

        -- provider: Provider string in format 'module.path:ClassName'
        -- validation_type: The namespace:type being loaded

        Returns instance of the loaded validator class.

        Raises:
            ModuleNotFoundError: If the provider module is not installed
            AttributeError: If the provider class is not found in the module
            TypeError: If the provider class doesn't inherit from BaseValidator
        """
        # Check cache first
        cache_key = f"{validation_type}:{provider}"
        if cache_key in self._loaded_plugins:
            cached_class = self._loaded_plugins[cache_key]
            return cached_class(self.loader)

        # Parse provider string
        if ":" not in provider:
            raise ValueError(
                f"Invalid provider format: '{provider}'. " "Must be 'module.path:ClassName'"
            )

        module_path, class_name = provider.rsplit(":", 1)

        # Import module
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f"Provider module not found: {module_path}. Is the package installed?"
            ) from e

        # Get class from module
        try:
            validator_class_any = getattr(module, class_name)
        except AttributeError as e:
            raise AttributeError(f"Provider class not found: {class_name} in {module_path}") from e

        # Verify it's a BaseValidator subclass
        if not issubclass(validator_class_any, BaseValidator):
            raise TypeError(f"Provider class {class_name} must inherit from BaseValidator")

        # Type narrowing: now we know it's a Type[BaseValidator]
        validator_class: Type[BaseValidator] = validator_class_any

        # Cache the class
        self._loaded_plugins[cache_key] = validator_class

        # Check for namespace conflicts
        validator_instance = validator_class(self.loader)
        actual_type = validator_instance.validation_type

        if actual_type != validation_type:
            raise ValueError(
                f"Provider {class_name} declares validation_type '{actual_type}' "
                f"but was requested for '{validation_type}'"
            )

        if actual_type in self._validators:
            existing = self._validators[actual_type]
            raise ValueError(
                f"Validation type '{actual_type}' already registered by "
                f"{existing.__class__.__name__}. Cannot load {class_name} from {module_path}."
            )

        # Register the validator
        self._validators[actual_type] = validator_instance

        return validator_instance

    def _get_validator(self, rule_type: str, provider: Optional[str] = None) -> BaseValidator:
        """Get validator for a given rule type, loading if necessary.

        -- rule_type: Namespaced validation type (e.g., 'core:file_exists')
        -- provider: Optional provider string for custom validators

        Returns the validator instance.

        Raises ValueError if validator cannot be found or loaded.
        """
        # Map inverted rules to their base validators
        actual_type = rule_type
        if rule_type == "core:file_not_exists":
            actual_type = "core:file_exists"

        # Check if already registered
        if actual_type in self._validators:
            return self._validators[actual_type]

        # If not registered and provider is given, try to load it
        if provider:
            return self._load_validator(provider, rule_type)

        # Not found and no provider
        raise ValueError(
            f"Unsupported validation rule type: {rule_type}. "
            "For custom validators, specify a provider."
        )

    def get_computation_type(self, rule_type: str, provider: Optional[str] = None) -> str:
        """Get the computation type for a given rule type.

        -- rule_type: The namespaced validation rule type
        -- provider: Optional provider for custom validators

        Returns "programmatic" or "llm".

        Raises ValueError if rule type is not supported.
        """
        validator = self._get_validator(rule_type, provider)
        return validator.computation_type

    def is_programmatic(self, rule_type: str, provider: Optional[str] = None) -> bool:
        """Check if a rule type is programmatic (non-LLM).

        -- rule_type: The namespaced validation rule type
        -- provider: Optional provider for custom validators

        Returns True if programmatic, False if LLM-based.
        """
        try:
            return self.get_computation_type(rule_type, provider) == "programmatic"
        except ValueError:
            # Unknown rule type - default to LLM
            return False

    def get_supported_clients(
        self, rule_type: str, provider: Optional[str] = None
    ) -> List[ClientType]:
        """Get the list of client types supported by a given rule type.

        -- rule_type: The namespaced validation rule type
        -- provider: Optional provider for custom validators

        Returns list of ClientType enum values.

        Raises ValueError if rule type is not supported.
        """
        validator = self._get_validator(rule_type, provider)
        return validator.supported_clients

    def supports_client(
        self, rule_type: str, client_type: ClientType, provider: Optional[str] = None
    ) -> bool:
        """Check if a rule type supports a specific client.

        -- rule_type: The namespaced validation rule type
        -- client_type: The client type to check
        -- provider: Optional provider for custom validators

        Returns True if the validator supports the client, False otherwise.
        """
        try:
            supported = self.get_supported_clients(rule_type, provider)
            return ClientType.ALL in supported or client_type in supported
        except ValueError:
            # Unknown rule type - default to not supported
            return False

    def execute_rule(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
        provider: Optional[str] = None,
    ) -> Optional[DocumentRule]:
        """Execute a validation rule.

        -- rule: The validation rule to execute
        -- bundle: The document bundle to validate
        -- all_bundles: Optional list of all bundles
        -- provider: Optional provider for custom validators

        Returns DocumentRule if validation fails, None if passes.

        Raises ValueError if rule type is not supported.
        """
        validator = self._get_validator(rule.rule_type, provider)
        result = validator.validate(rule, bundle, all_bundles)

        # Handle inverted rules (file_not_exists)
        if rule.rule_type == "core:file_not_exists":
            return self._invert_result(result, rule, bundle)

        return result

    def _invert_result(
        self,
        result: Optional[DocumentRule],
        rule: ValidationRule,
        bundle: DocumentBundle,
    ) -> Optional[DocumentRule]:
        """Invert validation result for NOT rules.

        -- result: Original validation result
        -- rule: The validation rule
        -- bundle: The document bundle

        Returns inverted result (None becomes DocumentRule, DocumentRule becomes None).
        """
        if result is None:
            # Original validation passed (file exists), but we want it NOT to exist
            # So this is a failure
            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=[rule.file_path] if rule.file_path else [],
                observed_issue=rule.failure_message or "File exists but should not",
                expected_quality=rule.expected_behavior or "File should not exist",
                rule_type="",  # Will be set by analyzer
                context=f"Validation rule: {rule.description}",
            )
        else:
            # Original validation failed (file doesn't exist), which is what we want
            # So this is a pass
            return None


__all__ = [
    "BaseValidator",
    "CircularDependenciesValidator",
    "ClaudeCircularDependenciesValidator",
    "ClaudeDependencyDuplicateValidator",
    "ClaudeMcpPermissionsValidator",
    "ClaudeMaxDependencyDepthValidator",
    "ClaudeSettingsDuplicatesValidator",
    "ClaudeSkillSettingsValidator",
    "ClientType",
    "DependencyDuplicateValidator",
    "FileExistsValidator",
    "FileSizeValidator",
    "JsonSchemaValidator",
    "ListMatchValidator",
    "ListRegexMatchValidator",
    "MarkdownLinkValidator",
    "MaxDependencyDepthValidator",
    "RegexMatchValidator",
    "TokenCountValidator",
    "ValidatorRegistry",
    "YamlFrontmatterValidator",
    "YamlSchemaValidator",
]
