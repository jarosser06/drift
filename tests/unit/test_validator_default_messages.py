"""Unit tests for validator default failure message functionality."""

from typing import List, Literal, Optional

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators import (
    BaseValidator,
    CircularDependenciesValidator,
    FileExistsValidator,
)


class MockValidatorWithDefaults(BaseValidator):
    """Mock validator with custom default messages for testing."""

    @property
    def validation_type(self) -> str:
        """Return validation type."""
        return "test:mock_validator"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type."""
        return "programmatic"

    @property
    def default_failure_message(self) -> str:
        """Return default failure message."""
        return "Default failure: {detail}"

    @property
    def default_expected_behavior(self) -> str:
        """Return default expected behavior."""
        return "Default expected behavior"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Mock validation that always fails for testing."""
        failure_details = {"detail": "test_value"}

        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[],
            observed_issue=self._get_failure_message(rule, failure_details),
            expected_quality=self._get_expected_behavior(rule),
            rule_type="",
            context=f"Test: {rule.description}",
            failure_details=failure_details,
        )


class TestBaseValidatorDefaultMessages:
    """Tests for BaseValidator default message functionality."""

    def test_default_failure_message_generic(self):
        """Test that BaseValidator provides a generic default message."""
        validator = FileExistsValidator()
        assert (
            "core:file_exists" in validator.default_failure_message
            or "File" in validator.default_failure_message
        )

    def test_default_expected_behavior_generic(self):
        """Test that BaseValidator provides a generic default expected behavior."""
        validator = FileExistsValidator()
        assert validator.default_expected_behavior is not None
        assert len(validator.default_expected_behavior) > 0

    def test_get_failure_message_uses_custom_when_provided(self):
        """Test that _get_failure_message uses custom message when provided."""
        validator = MockValidatorWithDefaults()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test rule",
            failure_message="Custom: {detail}",
        )

        message = validator._get_failure_message(rule, {"detail": "foo"})
        assert message == "Custom: foo"

    def test_get_failure_message_uses_default_when_none(self):
        """Test that _get_failure_message uses default when None."""
        validator = MockValidatorWithDefaults()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test rule",
            failure_message=None,
        )

        message = validator._get_failure_message(rule, {"detail": "bar"})
        assert message == "Default failure: bar"

    def test_get_expected_behavior_uses_custom_when_provided(self):
        """Test that _get_expected_behavior uses custom when provided."""
        validator = MockValidatorWithDefaults()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test rule",
            expected_behavior="Custom expected",
        )

        behavior = validator._get_expected_behavior(rule)
        assert behavior == "Custom expected"

    def test_get_expected_behavior_uses_default_when_none(self):
        """Test that _get_expected_behavior uses default when None."""
        validator = MockValidatorWithDefaults()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test rule",
            expected_behavior=None,
        )

        behavior = validator._get_expected_behavior(rule)
        assert behavior == "Default expected behavior"


class TestFileExistsValidatorDefaultMessages:
    """Tests for FileExistsValidator default messages."""

    @pytest.fixture
    def bundle_with_missing_file(self, tmp_path):
        """Create bundle with a missing file."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=tmp_path,
        )

    def test_file_exists_has_default_message(self):
        """Test that FileExistsValidator has a default failure message."""
        validator = FileExistsValidator()
        assert validator.default_failure_message is not None
        assert (
            "file" in validator.default_failure_message.lower()
            or "exist" in validator.default_failure_message.lower()
        )

    def test_file_exists_has_default_expected_behavior(self):
        """Test that FileExistsValidator has a default expected behavior."""
        validator = FileExistsValidator()
        assert validator.default_expected_behavior is not None
        assert len(validator.default_expected_behavior) > 0

    def test_file_exists_uses_default_message_when_none(self, bundle_with_missing_file):
        """Test that FileExistsValidator uses default message when none provided."""
        validator = FileExistsValidator()
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check file",
            params={"file_path": "missing.txt"},
            failure_message=None,  # No custom message
            expected_behavior=None,  # No custom behavior
        )

        result = validator.validate(rule, bundle_with_missing_file)

        assert result is not None
        # Should use default message
        assert result.observed_issue is not None
        assert "missing.txt" in result.observed_issue
        # Should use default expected behavior
        assert result.expected_quality is not None

    def test_file_exists_uses_custom_message_when_provided(self, bundle_with_missing_file):
        """Test that FileExistsValidator uses custom message when provided."""
        validator = FileExistsValidator()
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check file",
            params={"file_path": "missing.txt"},
            failure_message="Custom: File {file_path} is missing!",
            expected_behavior="Custom: File should exist",
        )

        result = validator.validate(rule, bundle_with_missing_file)

        assert result is not None
        assert result.observed_issue == "Custom: File missing.txt is missing!"
        assert result.expected_quality == "Custom: File should exist"


class TestCircularDependenciesValidatorDefaultMessages:
    """Tests for CircularDependenciesValidator default messages."""

    def test_circular_deps_has_default_message(self):
        """Test that CircularDependenciesValidator has a default message."""
        validator = CircularDependenciesValidator()
        assert validator.default_failure_message is not None
        assert (
            "circular" in validator.default_failure_message.lower()
            or "cycle" in validator.default_failure_message.lower()
        )

    def test_circular_deps_has_default_expected_behavior(self):
        """Test that CircularDependenciesValidator has default expected behavior."""
        validator = CircularDependenciesValidator()
        assert validator.default_expected_behavior is not None
        assert len(validator.default_expected_behavior) > 0

    def test_circular_deps_default_message_has_placeholder(self):
        """Test that default message includes placeholder for circular path."""
        validator = CircularDependenciesValidator()
        assert "{circular_path}" in validator.default_failure_message


class TestValidationRuleOptionalMessages:
    """Tests for ValidationRule with optional failure messages."""

    def test_validation_rule_with_no_messages(self):
        """Test creating ValidationRule with no failure_message or expected_behavior."""
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Test rule",
            file_path="test.txt",
        )

        assert rule.failure_message is None
        assert rule.expected_behavior is None

    def test_validation_rule_with_only_failure_message(self):
        """Test creating ValidationRule with only failure_message."""
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Test rule",
            params={"file_path": "test.txt"},
            failure_message="Custom failure",
        )

        assert rule.failure_message == "Custom failure"
        assert rule.expected_behavior is None

    def test_validation_rule_with_only_expected_behavior(self):
        """Test creating ValidationRule with only expected_behavior."""
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Test rule",
            params={"file_path": "test.txt"},
            expected_behavior="Custom expected",
        )

        assert rule.failure_message is None
        assert rule.expected_behavior == "Custom expected"

    def test_validation_rule_with_both_messages(self):
        """Test creating ValidationRule with both messages."""
        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Test rule",
            params={"file_path": "test.txt"},
            failure_message="Custom failure",
            expected_behavior="Custom expected",
        )

        assert rule.failure_message == "Custom failure"
        assert rule.expected_behavior == "Custom expected"


class TestDefaultMessageTemplateSubstitution:
    """Tests for template substitution in default messages."""

    def test_template_substitution_with_details(self):
        """Test that default messages support template substitution."""
        validator = MockValidatorWithDefaults()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            failure_message=None,  # Use default
        )

        # Default is "Default failure: {detail}"
        message = validator._get_failure_message(rule, {"detail": "test123"})
        assert message == "Default failure: test123"

    def test_template_substitution_without_details(self):
        """Test that templates without details don't break."""
        validator = MockValidatorWithDefaults()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            failure_message=None,
        )

        # Default has {detail} but we don't provide it
        message = validator._get_failure_message(rule, None)
        # Placeholder should remain unchanged
        assert "{detail}" in message

    def test_custom_template_with_multiple_placeholders(self):
        """Test custom message with multiple placeholders."""
        validator = MockValidatorWithDefaults()
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test",
            failure_message="Error in {file} at line {line}",
        )

        message = validator._get_failure_message(rule, {"file": "test.py", "line": "42"})
        assert message == "Error in test.py at line 42"


class TestEndToEndDefaultMessages:
    """End-to-end tests for default message functionality."""

    @pytest.fixture
    def validator(self):
        """Create mock validator instance."""
        return MockValidatorWithDefaults()

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create test document bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            files=[],
            project_path=tmp_path,
        )

    def test_e2e_with_no_custom_messages(self, validator, bundle):
        """Test end-to-end flow with no custom messages."""
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test rule",
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert result.observed_issue == "Default failure: test_value"
        assert result.expected_quality == "Default expected behavior"
        assert result.failure_details == {"detail": "test_value"}

    def test_e2e_with_custom_messages(self, validator, bundle):
        """Test end-to-end flow with custom messages."""
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test rule",
            failure_message="CUSTOM: {detail}",
            expected_behavior="CUSTOM EXPECTED",
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert result.observed_issue == "CUSTOM: test_value"
        assert result.expected_quality == "CUSTOM EXPECTED"

    def test_e2e_with_partial_custom_messages(self, validator, bundle):
        """Test end-to-end flow with only failure_message custom."""
        rule = ValidationRule(
            rule_type="test:mock",
            description="Test rule",
            failure_message="CUSTOM: {detail}",
            # expected_behavior not provided - should use default
        )

        result = validator.validate(rule, bundle)

        assert result is not None
        assert result.observed_issue == "CUSTOM: test_value"
        assert result.expected_quality == "Default expected behavior"  # Uses default


class TestBaseValidatorFallbacks:
    """Test BaseValidator fallback behavior when not overridden."""

    def test_base_validator_default_failure_message_fallback(self, tmp_path):
        """Verify BaseValidator provides generic fallback when not overridden."""

        class MinimalValidator(BaseValidator):
            """Validator that doesn't override default messages."""

            @property
            def validation_type(self) -> str:
                """Return validation type."""
                return "test:minimal"

            @property
            def computation_type(self) -> Literal["programmatic", "llm"]:
                """Return computation type."""
                return "programmatic"

            def validate(self, rule, bundle, all_bundles=None):
                """Fail validation for testing purposes."""
                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[],
                    observed_issue=self._get_failure_message(rule),
                    expected_quality=self._get_expected_behavior(rule),
                    rule_type="",
                    context="Test",
                )

        validator = MinimalValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[],
        )
        rule = ValidationRule(rule_type="test:minimal", description="Test")

        result = validator.validate(rule, bundle)

        # Should use BaseValidator's generic fallbacks
        assert result.observed_issue == "Validation failed for test:minimal"
        assert result.expected_quality == "Should pass test:minimal validation"

    def test_base_validator_fallback_with_custom_message(self, tmp_path):
        """Verify BaseValidator fallback with custom message in rule."""

        class MinimalValidator(BaseValidator):
            """Validator that doesn't override default messages."""

            @property
            def validation_type(self) -> str:
                """Return validation type."""
                return "test:minimal"

            @property
            def computation_type(self) -> Literal["programmatic", "llm"]:
                """Return computation type."""
                return "programmatic"

            def validate(self, rule, bundle, all_bundles=None):
                """Fail validation for testing purposes."""
                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[],
                    observed_issue=self._get_failure_message(rule),
                    expected_quality=self._get_expected_behavior(rule),
                    rule_type="",
                    context="Test",
                )

        validator = MinimalValidator()
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="collection",
            project_path=tmp_path,
            files=[],
        )
        rule = ValidationRule(
            rule_type="test:minimal",
            description="Test",
            failure_message="Custom failure",
            expected_behavior="Custom expected",
        )

        result = validator.validate(rule, bundle)

        # Should use custom messages from rule
        assert result.observed_issue == "Custom failure"
        assert result.expected_quality == "Custom expected"
