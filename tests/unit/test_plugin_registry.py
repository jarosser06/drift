"""Unit tests for ValidatorRegistry plugin loading system."""

from typing import List, Literal, Optional
from unittest.mock import MagicMock, patch

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators import BaseValidator, ValidatorRegistry


class MockPluginValidator(BaseValidator):
    """Mock validator for testing plugin loading."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "security:scan"

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
        """Mock validation - always passes."""
        return None


class MockPluginValidatorWrongType(BaseValidator):
    """Mock validator with mismatched validation type."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "security:different"  # Different from what's requested

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
        """Mock validation - always passes."""
        return None


class NotAValidator:
    """Class that doesn't inherit from BaseValidator."""

    pass


class TestPluginLoading:
    """Tests for ValidatorRegistry._load_validator() method."""

    def test_load_valid_plugin_class(self):
        """Test successfully loading a valid plugin class."""
        registry = ValidatorRegistry()

        # Mock the import_module to return our test module
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockPluginValidator = MockPluginValidator
            mock_import.return_value = mock_module

            # Load the validator
            validator = registry._load_validator(
                provider="test.module:MockPluginValidator",
                validation_type="security:scan",
            )

            assert isinstance(validator, MockPluginValidator)
            assert validator.validation_type == "security:scan"
            # Should be registered in the registry
            assert "security:scan" in registry._validators

    def test_load_plugin_module_not_found(self):
        """Test error when module not found."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_import.side_effect = ModuleNotFoundError("No module named 'nonexistent'")

            with pytest.raises(ModuleNotFoundError) as exc_info:
                registry._load_validator(
                    provider="nonexistent.module:SomeValidator",
                    validation_type="custom:validator",
                )

            assert "Provider module not found: nonexistent.module" in str(exc_info.value)
            assert "Is the package installed?" in str(exc_info.value)

    def test_load_plugin_class_not_found(self):
        """Test error when class not found in module."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            # Create a real empty module-like object that doesn't have the class
            import types

            mock_module = types.ModuleType("test_module")
            mock_import.return_value = mock_module

            with pytest.raises(AttributeError) as exc_info:
                registry._load_validator(
                    provider="test.module:MissingClass",
                    validation_type="custom:validator",
                )

            assert "Provider class not found: MissingClass in test.module" in str(exc_info.value)

    def test_load_plugin_not_basevalidator_subclass(self):
        """Test error when class doesn't inherit from BaseValidator."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.NotAValidator = NotAValidator
            mock_import.return_value = mock_module

            with pytest.raises(TypeError) as exc_info:
                registry._load_validator(
                    provider="test.module:NotAValidator",
                    validation_type="custom:validator",
                )

            assert "Provider class NotAValidator must inherit from BaseValidator" in str(
                exc_info.value
            )

    def test_load_plugin_caches_after_first_load(self):
        """Test that plugins are cached after first load (singleton pattern)."""
        # Clear the class-level cache before testing
        ValidatorRegistry._loaded_plugins.clear()

        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockPluginValidator = MockPluginValidator
            mock_import.return_value = mock_module

            # First load - cache should be empty
            cache_key = "security:scan:test.module:MockPluginValidator"
            assert cache_key not in ValidatorRegistry._loaded_plugins

            # Load validator first time
            validator1 = registry._load_validator(
                provider="test.module:MockPluginValidator",
                validation_type="security:scan",
            )

            # Should have been added to cache
            assert cache_key in ValidatorRegistry._loaded_plugins
            assert mock_import.call_count == 1

            # Second load - should use cache, not import again
            validator2 = registry._load_validator(
                provider="test.module:MockPluginValidator",
                validation_type="security:scan",
            )

            # Should still only have imported once (using cache for second call)
            assert mock_import.call_count == 1
            # Both should be instances of the same class
            assert isinstance(validator1, type(validator2))

    def test_load_plugin_duplicate_namespace_type(self):
        """Test error when validation type already registered by another validator."""
        registry = ValidatorRegistry()

        # core:file_exists is already registered by builtin validator
        with patch("importlib.import_module") as mock_import:
            # Create a mock validator that claims to be core:file_exists
            class DuplicateValidator(BaseValidator):
                @property
                def validation_type(self) -> str:
                    return "core:file_exists"

                @property
                def computation_type(self) -> Literal["programmatic", "llm"]:
                    return "programmatic"

                def validate(
                    self,
                    rule: ValidationRule,
                    bundle: DocumentBundle,
                    all_bundles: Optional[List[DocumentBundle]] = None,
                ) -> Optional[DocumentRule]:
                    return None

            mock_module = MagicMock()
            mock_module.DuplicateValidator = DuplicateValidator
            mock_import.return_value = mock_module

            with pytest.raises(ValueError) as exc_info:
                registry._load_validator(
                    provider="test.module:DuplicateValidator",
                    validation_type="core:file_exists",
                )

            assert "Validation type 'core:file_exists' already registered" in str(exc_info.value)
            assert "FileExistsValidator" in str(exc_info.value)

    def test_load_plugin_type_mismatch(self):
        """Test error when plugin declares different type than requested."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockPluginValidatorWrongType = MockPluginValidatorWrongType
            mock_import.return_value = mock_module

            with pytest.raises(ValueError) as exc_info:
                registry._load_validator(
                    provider="test.module:MockPluginValidatorWrongType",
                    validation_type="security:scan",  # Requested type
                )

            assert "declares validation_type 'security:different'" in str(exc_info.value)
            assert "but was requested for 'security:scan'" in str(exc_info.value)

    def test_load_plugin_invalid_provider_format(self):
        """Test error when provider format is invalid."""
        registry = ValidatorRegistry()

        # Missing colon separator
        with pytest.raises(ValueError) as exc_info:
            registry._load_validator(
                provider="test.module.ClassName",  # No colon
                validation_type="custom:validator",
            )

        assert "Invalid provider format" in str(exc_info.value)
        assert "Must be 'module.path:ClassName'" in str(exc_info.value)


class TestGetValidator:
    """Tests for ValidatorRegistry._get_validator() method."""

    def test_get_builtin_validator(self):
        """Test getting a built-in core validator."""
        registry = ValidatorRegistry()

        validator = registry._get_validator("core:file_exists")

        assert validator is not None
        assert validator.validation_type == "core:file_exists"
        assert validator.computation_type == "programmatic"

    def test_get_validator_with_provider(self):
        """Test getting a validator with provider loading."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockPluginValidator = MockPluginValidator
            mock_import.return_value = mock_module

            validator = registry._get_validator(
                rule_type="security:scan",
                provider="test.module:MockPluginValidator",
            )

            assert validator is not None
            assert validator.validation_type == "security:scan"

    def test_get_validator_not_found_no_provider(self):
        """Test error when validator not found and no provider given."""
        registry = ValidatorRegistry()

        with pytest.raises(ValueError) as exc_info:
            registry._get_validator("custom:missing")

        assert "Unsupported validation rule type: custom:missing" in str(exc_info.value)
        assert "For custom validators, specify a provider" in str(exc_info.value)

    def test_get_cached_validator(self):
        """Test that getting a validator uses cache."""
        registry = ValidatorRegistry()

        # Get validator twice
        validator1 = registry._get_validator("core:file_exists")
        validator2 = registry._get_validator("core:file_exists")

        # Should be the exact same instance
        assert validator1 is validator2


class TestRegistryComputationType:
    """Tests for get_computation_type and is_programmatic methods."""

    def test_get_computation_type_builtin(self):
        """Test getting computation type for built-in validator."""
        registry = ValidatorRegistry()

        assert registry.get_computation_type("core:file_exists") == "programmatic"
        assert registry.get_computation_type("core:regex_match") == "programmatic"

    def test_get_computation_type_plugin(self):
        """Test getting computation type for plugin validator."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockPluginValidator = MockPluginValidator
            mock_import.return_value = mock_module

            comp_type = registry.get_computation_type(
                "security:scan",
                provider="test.module:MockPluginValidator",
            )

            assert comp_type == "programmatic"

    def test_is_programmatic_builtin(self):
        """Test is_programmatic for built-in validators."""
        registry = ValidatorRegistry()

        assert registry.is_programmatic("core:file_exists") is True
        assert registry.is_programmatic("core:file_size") is True

    def test_is_programmatic_plugin(self):
        """Test is_programmatic for plugin validators."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockPluginValidator = MockPluginValidator
            mock_import.return_value = mock_module

            is_prog = registry.is_programmatic(
                "security:scan",
                provider="test.module:MockPluginValidator",
            )

            assert is_prog is True

    def test_is_programmatic_unknown_defaults_false(self):
        """Test is_programmatic defaults to False for unknown validators."""
        registry = ValidatorRegistry()

        # Unknown validator without provider
        assert registry.is_programmatic("unknown:type") is False


class TestPluginExecution:
    """Tests for executing validation with plugin validators."""

    @pytest.fixture
    def sample_bundle(self, tmp_path):
        """Create a sample document bundle."""
        return DocumentBundle(
            bundle_id="test-bundle",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=tmp_path,
        )

    def test_execute_plugin_rule(self, sample_bundle):
        """Test executing a validation rule with a plugin validator."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.MockPluginValidator = MockPluginValidator
            mock_import.return_value = mock_module

            rule = ValidationRule(
                rule_type="security:scan",
                description="Security scan",
                failure_message="Security issue found",
                expected_behavior="No security issues",
            )

            result = registry.execute_rule(
                rule=rule,
                bundle=sample_bundle,
                provider="test.module:MockPluginValidator",
            )

            # MockPluginValidator always returns None (pass)
            assert result is None

    def test_execute_plugin_rule_with_failure(self, sample_bundle):
        """Test executing a plugin rule that fails validation."""

        class FailingValidator(BaseValidator):
            @property
            def validation_type(self) -> str:
                return "security:fail"

            @property
            def computation_type(self) -> Literal["programmatic", "llm"]:
                return "programmatic"

            def validate(
                self,
                rule: ValidationRule,
                bundle: DocumentBundle,
                all_bundles: Optional[List[DocumentBundle]] = None,
            ) -> Optional[DocumentRule]:
                # Always fails
                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[],
                    observed_issue=rule.failure_message,
                    expected_quality=rule.expected_behavior,
                    rule_type="",
                    context=f"Validation rule: {rule.description}",
                )

        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.FailingValidator = FailingValidator
            mock_import.return_value = mock_module

            rule = ValidationRule(
                rule_type="security:fail",
                description="Security scan",
                failure_message="Security issue found",
                expected_behavior="No security issues",
            )

            result = registry.execute_rule(
                rule=rule,
                bundle=sample_bundle,
                provider="test.module:FailingValidator",
            )

            assert result is not None
            assert result.observed_issue == "Security issue found"
            assert result.expected_quality == "No security issues"


class TestBuiltinValidatorMigration:
    """Tests that all built-in validators use core: prefix."""

    def test_all_builtin_validators_registered(self):
        """Test that all 19 core validators are registered with core: prefix."""
        registry = ValidatorRegistry()

        expected_core_validators = [
            "core:file_exists",
            "core:file_size",
            "core:token_count",
            "core:json_schema",
            "core:yaml_schema",
            "core:yaml_frontmatter",
            "core:regex_match",
            "core:list_match",
            "core:list_regex_match",
            "core:markdown_link",
            "core:dependency_duplicate",
            "core:circular_dependencies",
            "core:max_dependency_depth",
            "core:claude_dependency_duplicate",
            "core:claude_circular_dependencies",
            "core:claude_max_dependency_depth",
            "core:claude_skill_settings",
            "core:claude_settings_duplicates",
            "core:claude_mcp_permissions",
        ]

        for validator_type in expected_core_validators:
            assert validator_type in registry._validators, f"{validator_type} not registered"

        # Ensure count matches
        assert len(registry._validators) == len(expected_core_validators)

    def test_no_builtin_validators_without_namespace(self):
        """Test that no built-in validators are registered without namespace."""
        registry = ValidatorRegistry()

        # All registered validators should have the namespace:type format
        for validator_type in registry._validators.keys():
            assert ":" in validator_type, f"{validator_type} missing namespace"
            namespace, type_name = validator_type.split(":", 1)
            assert namespace in ["core"], f"Unexpected namespace: {namespace}"

    def test_builtin_validators_work_correctly(self, tmp_path):
        """Test that built-in validators still work with new namespaced types."""
        registry = ValidatorRegistry()

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        bundle = DocumentBundle(
            bundle_id="test-bundle",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=tmp_path,
        )

        # Test core:file_exists
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check test file exists",
            file_path="test.txt",
            failure_message="File not found",
            expected_behavior="File should exist",
        )

        result = registry.execute_rule(rule, bundle)
        assert result is None  # File exists, should pass

        # Test core:file_exists with missing file
        rule_missing = ValidationRule(
            rule_type="core:file_exists",
            description="Check missing file",
            file_path="missing.txt",
            failure_message="Missing file not found",
            expected_behavior="File should exist",
        )

        result_missing = registry.execute_rule(rule_missing, bundle)
        assert result_missing is not None  # File doesn't exist, should fail
