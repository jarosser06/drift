"""Unit tests for namespace validation and PhaseDefinition provider validation."""

import pytest
from pydantic import ValidationError

from drift.config.models import VALIDATION_TYPE_PATTERN, PhaseDefinition


class TestNamespacePatternValidation:
    """Tests for VALIDATION_TYPE_PATTERN regex validation."""

    def test_valid_namespace_formats(self):
        """Test that valid namespace formats match the pattern."""
        valid_formats = [
            "core:file_exists",
            "security:scan",
            "my_company:check",
            "custom:validator",
            "a:b",  # Minimal valid format
            "my_namespace:my_type_123",
            "namespace123:type456",
            "long_namespace_name:long_type_name",
        ]

        for format_str in valid_formats:
            assert VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Valid format '{format_str}' should match pattern"

    def test_invalid_namespace_no_colon(self):
        """Test that formats without colon are rejected."""
        invalid_formats = [
            "no_namespace",
            "justtext",
            "file_exists",
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Invalid format '{format_str}' should not match pattern"

    def test_invalid_namespace_uppercase(self):
        """Test that uppercase letters are rejected."""
        invalid_formats = [
            "Core:test",
            "core:Test",
            "CORE:test",
            "MyNamespace:test",
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Invalid format '{format_str}' should not match pattern (uppercase)"

    def test_invalid_namespace_empty_parts(self):
        """Test that empty namespace or type parts are rejected."""
        invalid_formats = [
            ":test",  # Empty namespace
            "test:",  # Empty type
            ":",  # Both empty
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Invalid format '{format_str}' should not match pattern (empty parts)"

    def test_invalid_namespace_dashes(self):
        """Test that dashes are rejected (only underscores allowed)."""
        invalid_formats = [
            "test-dash:scan",
            "core:test-type",
            "my-namespace:my-type",
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Invalid format '{format_str}' should not match pattern (dashes)"

    def test_invalid_namespace_special_chars(self):
        """Test that special characters are rejected."""
        invalid_formats = [
            "core@test:scan",
            "core:test!",
            "core.test:scan",
            "core:test.scan",
            "core/test:scan",
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Invalid format '{format_str}' should not match pattern (special chars)"

    def test_invalid_namespace_starts_with_digit(self):
        """Test that namespaces/types starting with digits are rejected."""
        invalid_formats = [
            "123namespace:test",
            "namespace:123test",
            "1:2",
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Invalid format '{format_str}' should not match pattern (starts with digit)"

    def test_valid_namespace_contains_digits(self):
        """Test that digits in the middle/end are allowed."""
        valid_formats = [
            "namespace123:test",
            "test:type456",
            "ns1:type2",
        ]

        for format_str in valid_formats:
            assert VALIDATION_TYPE_PATTERN.match(
                format_str
            ), f"Valid format '{format_str}' should match pattern (contains digits)"


class TestPhaseDefinitionProviderValidation:
    """Tests for PhaseDefinition provider field validation."""

    def test_prompt_type_no_provider_validation(self):
        """Test that prompt type doesn't validate provider field."""
        # Should work with provider
        phase = PhaseDefinition(
            name="test",
            type="prompt",
            prompt="Test prompt",
            provider="some.module:Class",  # Should be ignored
        )
        assert phase.type == "prompt"
        assert phase.provider == "some.module:Class"

        # Should work without provider
        phase2 = PhaseDefinition(
            name="test",
            type="prompt",
            prompt="Test prompt",
        )
        assert phase2.type == "prompt"
        assert phase2.provider is None

    def test_core_type_must_not_have_provider(self):
        """Test that core:* types must NOT have a provider."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseDefinition(
                name="test",
                type="core:file_exists",
                provider="some.module:Class",  # Should error
            )

        error_msg = str(exc_info.value)
        assert "Core validation type 'core:file_exists' must not have a provider" in error_msg
        assert "Set provider to None or omit it" in error_msg

    def test_core_type_without_provider_succeeds(self):
        """Test that core:* types work without provider."""
        phase = PhaseDefinition(
            name="test",
            type="core:file_exists",
            file_path="test.txt",
        )
        assert phase.type == "core:file_exists"
        assert phase.provider is None

        # Explicitly setting to None should also work
        phase2 = PhaseDefinition(
            name="test",
            type="core:file_exists",
            provider=None,
            file_path="test.txt",
        )
        assert phase2.provider is None

    def test_custom_type_must_have_provider(self):
        """Test that non-core types MUST have a provider."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseDefinition(
                name="test",
                type="security:scan",  # Non-core type
                provider=None,  # Explicitly None (missing provider)
            )

        error_msg = str(exc_info.value)
        assert "Custom validation type 'security:scan' requires a provider" in error_msg
        assert "Specify provider as 'module.path:ClassName'" in error_msg

    def test_custom_type_with_provider_succeeds(self):
        """Test that non-core types work with provider."""
        phase = PhaseDefinition(
            name="test",
            type="security:scan",
            provider="mypackage.validators:SecurityValidator",
        )
        assert phase.type == "security:scan"
        assert phase.provider == "mypackage.validators:SecurityValidator"

    def test_provider_format_validation(self):
        """Test that provider format must be 'module.path:ClassName'."""
        # Valid formats
        valid_providers = [
            "module:Class",
            "package.module:Class",
            "package.subpackage.module:ClassName",
            "a.b.c:D",
        ]

        for provider in valid_providers:
            phase = PhaseDefinition(
                name="test",
                type="custom:type",
                provider=provider,
            )
            assert phase.provider == provider

    def test_provider_format_invalid_no_colon(self):
        """Test that provider without colon is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseDefinition(
                name="test",
                type="custom:type",
                provider="module.Class",  # Missing colon
            )

        error_msg = str(exc_info.value)
        assert "Invalid provider format: 'module.Class'" in error_msg
        assert "Must be 'module.path:ClassName'" in error_msg

    def test_provider_format_invalid_empty_module(self):
        """Test that provider with empty module part is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseDefinition(
                name="test",
                type="custom:type",
                provider=":ClassName",  # Empty module
            )

        error_msg = str(exc_info.value)
        assert "Invalid provider format" in error_msg

    def test_provider_format_invalid_empty_class(self):
        """Test that provider with empty class part is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseDefinition(
                name="test",
                type="custom:type",
                provider="module.path:",  # Empty class
            )

        error_msg = str(exc_info.value)
        assert "Invalid provider format" in error_msg

    def test_validation_type_format_validated(self):
        """Test that validation type format is validated for namespaced types."""
        # Type without colon (non-namespaced) doesn't trigger provider validation
        # Only types with colons are validated
        # So we test an invalid namespaced type
        with pytest.raises(ValidationError) as exc_info:
            PhaseDefinition(
                name="test",
                type="Invalid-Format:test",  # Invalid namespace (dash not allowed)
                provider="module:Class",
            )

        error_msg = str(exc_info.value)
        assert "Invalid validation type format: 'Invalid-Format:test'" in error_msg
        assert "Must match pattern: namespace:type" in error_msg

    def test_validation_type_format_uppercase_rejected(self):
        """Test that uppercase in validation type is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PhaseDefinition(
                name="test",
                type="Core:test",  # Uppercase C
                provider="module:Class",
            )

        error_msg = str(exc_info.value)
        assert "Invalid validation type format: 'Core:test'" in error_msg

    def test_multiple_core_validators(self):
        """Test that all core validators work without provider."""
        core_types = [
            "core:file_exists",
            "core:file_size",
            "core:token_count",
            "core:regex_match",
            "core:json_schema",
        ]

        for core_type in core_types:
            phase = PhaseDefinition(
                name="test",
                type=core_type,
            )
            assert phase.type == core_type
            assert phase.provider is None

    def test_multiple_custom_validators_with_providers(self):
        """Test that multiple custom validators work with different providers."""
        custom_configs = [
            ("security:scan", "security_pkg:ScanValidator"),
            ("quality:check", "quality_pkg:CheckValidator"),
            ("compliance:audit", "compliance_pkg.validators:AuditValidator"),
        ]

        for val_type, provider in custom_configs:
            phase = PhaseDefinition(
                name="test",
                type=val_type,
                provider=provider,
            )
            assert phase.type == val_type
            assert phase.provider == provider

    def test_core_type_empty_string_provider_succeeds(self):
        """Test that core types with empty string provider are treated as no provider."""
        # Empty string is falsy in Python, so `if v:` evaluates to False
        # This means empty string is treated as "no provider" and should succeed
        phase = PhaseDefinition(
            name="test",
            type="core:file_exists",
            provider="",  # Empty string is falsy, treated as no provider
        )

        assert phase.provider == ""  # Empty string is preserved
        # This is acceptable since the validation checks `if v:` which is False for empty string

    def test_phase_definition_with_all_fields(self):
        """Test PhaseDefinition with all optional fields."""
        phase = PhaseDefinition(
            name="custom_validation",
            type="security:scan",
            provider="security_pkg:ScanValidator",
            params={"severity": "high", "scan_depth": 3},
            file_path="config.yaml",
            failure_message="Security issue found",
            expected_behavior="No security issues",
        )

        assert phase.name == "custom_validation"
        assert phase.type == "security:scan"
        assert phase.provider == "security_pkg:ScanValidator"
        assert phase.params == {"severity": "high", "scan_depth": 3}
        assert phase.file_path == "config.yaml"
        assert phase.failure_message == "Security issue found"
        assert phase.expected_behavior == "No security issues"


class TestEdgeCases:
    """Tests for edge cases in namespace and provider validation."""

    def test_type_with_multiple_colons(self):
        """Test that types with multiple colons are rejected."""
        # The pattern only allows one colon
        assert not VALIDATION_TYPE_PATTERN.match("namespace:type:extra")

    def test_very_long_namespace_and_type(self):
        """Test that very long but valid names work."""
        long_namespace = "very_long_namespace_name_with_many_words"
        long_type = "very_long_type_name_with_many_words_123"
        valid_format = f"{long_namespace}:{long_type}"

        assert VALIDATION_TYPE_PATTERN.match(valid_format)

        phase = PhaseDefinition(
            name="test",
            type=valid_format,
            provider="module:Class",
        )
        assert phase.type == valid_format

    def test_whitespace_in_validation_type(self):
        """Test that whitespace in validation type is rejected."""
        invalid_formats = [
            "core :file_exists",
            "core: file_exists",
            "core:file_exists ",
            " core:file_exists",
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(format_str)

    def test_unicode_in_validation_type(self):
        """Test that unicode characters are rejected."""
        invalid_formats = [
            "core:file_exists_\u00e9",  # e with accent
            "\u4e2d\u6587:test",  # Chinese characters
            "core:test_\u0444",  # Cyrillic character
        ]

        for format_str in invalid_formats:
            assert not VALIDATION_TYPE_PATTERN.match(format_str)

    def test_provider_with_multiple_colons(self):
        """Test that provider with multiple colons works (namespaced module)."""
        # This should actually fail based on the validation logic
        # which splits on the last colon
        phase = PhaseDefinition(
            name="test",
            type="custom:type",
            provider="package:subpackage:Class",  # Multiple colons
        )
        # This will pass because rsplit(":", 1) will split on the last colon
        assert phase.provider == "package:subpackage:Class"
