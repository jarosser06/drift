"""Integration tests for the custom validation plugin system."""

from pathlib import Path
from typing import List, Literal, Optional
from unittest.mock import MagicMock, patch

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators import BaseValidator, ValidatorRegistry


class CustomSecurityValidator(BaseValidator):
    """Custom security validator for testing plugin system."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "security:vulnerability_scan"

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
        """Scan for security vulnerabilities.

        Checks if a 'vulnerabilities.txt' file exists in the project.
        If it exists and is not empty, fails validation.
        """
        if not rule.file_path:
            rule.file_path = "vulnerabilities.txt"

        vuln_file = bundle.project_path / rule.file_path

        if vuln_file.exists() and vuln_file.is_file():
            content = vuln_file.read_text()
            if content.strip():
                # Found vulnerabilities
                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=[rule.file_path],
                    observed_issue=rule.failure_message,
                    expected_quality=rule.expected_behavior,
                    rule_type="",
                    context=f"Security scan found issues: {content[:100]}",
                )

        # No vulnerabilities found
        return None


class CustomComplianceValidator(BaseValidator):
    """Custom compliance validator for testing."""

    @property
    def validation_type(self) -> str:
        """Return validation type for this validator."""
        return "compliance:license_check"

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
        """Check for required license file."""
        license_file = bundle.project_path / "LICENSE"

        if not license_file.exists():
            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=["LICENSE"],
                observed_issue=rule.failure_message,
                expected_quality=rule.expected_behavior,
                rule_type="",
                context="Compliance check: LICENSE file missing",
            )

        return None


class TestPluginSystemEndToEnd:
    """End-to-end tests for the plugin system."""

    @pytest.fixture
    def project_with_vulnerabilities(self, tmp_path):
        """Create a project with security vulnerabilities."""
        vuln_file = tmp_path / "vulnerabilities.txt"
        vuln_file.write_text("SQL Injection in login.py\nXSS in profile.html")
        return tmp_path

    @pytest.fixture
    def project_without_vulnerabilities(self, tmp_path):
        """Create a project without security vulnerabilities."""
        vuln_file = tmp_path / "vulnerabilities.txt"
        vuln_file.write_text("")  # Empty file = no vulnerabilities
        return tmp_path

    @pytest.fixture
    def project_without_license(self, tmp_path):
        """Create a project without a LICENSE file."""
        (tmp_path / "README.md").write_text("# Test Project")
        return tmp_path

    @pytest.fixture
    def project_with_license(self, tmp_path):
        """Create a project with a LICENSE file."""
        (tmp_path / "LICENSE").write_text("MIT License")
        return tmp_path

    def test_load_and_execute_custom_security_validator(self, project_with_vulnerabilities):
        """Test loading and executing a custom security validator plugin."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            # Mock the module containing the security validator
            mock_module = MagicMock()
            mock_module.SecurityValidator = CustomSecurityValidator
            mock_import.return_value = mock_module

            # Create bundle
            bundle = DocumentBundle(
                bundle_id="security-test",
                bundle_type="project",
                bundle_strategy="collection",
                files=[],
                project_path=project_with_vulnerabilities,
            )

            # Create validation rule
            rule = ValidationRule(
                rule_type="security:vulnerability_scan",
                description="Scan for security vulnerabilities",
                file_path="vulnerabilities.txt",
                failure_message="Security vulnerabilities detected",
                expected_behavior="No security vulnerabilities",
            )

            # Execute validation with plugin
            result = registry.execute_rule(
                rule=rule,
                bundle=bundle,
                provider="security_package.validators:SecurityValidator",
            )

            # Should fail because vulnerabilities exist
            assert result is not None
            assert result.observed_issue == "Security vulnerabilities detected"
            assert "vulnerabilities.txt" in result.file_paths

    def test_custom_validator_passes_when_no_issues(self, project_without_vulnerabilities):
        """Test that custom validator passes when no issues found."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.SecurityValidator = CustomSecurityValidator
            mock_import.return_value = mock_module

            bundle = DocumentBundle(
                bundle_id="security-test",
                bundle_type="project",
                bundle_strategy="collection",
                files=[],
                project_path=project_without_vulnerabilities,
            )

            rule = ValidationRule(
                rule_type="security:vulnerability_scan",
                description="Scan for security vulnerabilities",
                file_path="vulnerabilities.txt",
                failure_message="Security vulnerabilities detected",
                expected_behavior="No security vulnerabilities",
            )

            result = registry.execute_rule(
                rule=rule,
                bundle=bundle,
                provider="security_package.validators:SecurityValidator",
            )

            # Should pass because no vulnerabilities
            assert result is None

    def test_multiple_custom_validators(
        self, project_with_vulnerabilities, project_without_license
    ):
        """Test using multiple custom validators in the same registry."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            # Setup mock to return different validators based on provider
            def mock_import_side_effect(module_path):
                mock_module = MagicMock()
                if "security_package" in module_path:
                    mock_module.SecurityValidator = CustomSecurityValidator
                elif "compliance_package" in module_path:
                    mock_module.ComplianceValidator = CustomComplianceValidator
                return mock_module

            mock_import.side_effect = mock_import_side_effect

            # Combine both project issues for testing
            combined_project = project_without_license
            (combined_project / "vulnerabilities.txt").write_text("SQL Injection")

            bundle = DocumentBundle(
                bundle_id="combined-test",
                bundle_type="project",
                bundle_strategy="collection",
                files=[],
                project_path=combined_project,
            )

            # Test security validator
            security_rule = ValidationRule(
                rule_type="security:vulnerability_scan",
                description="Security scan",
                failure_message="Security issues found",
                expected_behavior="No security issues",
            )

            security_result = registry.execute_rule(
                rule=security_rule,
                bundle=bundle,
                provider="security_package.validators:SecurityValidator",
            )

            # Test compliance validator
            compliance_rule = ValidationRule(
                rule_type="compliance:license_check",
                description="License check",
                failure_message="LICENSE file missing",
                expected_behavior="LICENSE file should exist",
            )

            compliance_result = registry.execute_rule(
                rule=compliance_rule,
                bundle=bundle,
                provider="compliance_package.validators:ComplianceValidator",
            )

            # Both should fail
            assert security_result is not None
            assert compliance_result is not None

    def test_mixing_builtin_and_custom_validators(self, project_without_license):
        """Test mixing built-in core: validators with custom plugin validators."""
        registry = ValidatorRegistry()

        # Create a README.md file
        (project_without_license / "README.md").write_text("# Test")

        bundle = DocumentBundle(
            bundle_id="mixed-test",
            bundle_type="project",
            bundle_strategy="collection",
            files=[],
            project_path=project_without_license,
        )

        # Test built-in core:file_exists validator
        builtin_rule = ValidationRule(
            rule_type="core:file_exists",
            description="Check README exists",
            file_path="README.md",
            failure_message="README.md not found",
            expected_behavior="README.md should exist",
        )

        builtin_result = registry.execute_rule(rule=builtin_rule, bundle=bundle)

        # Test custom compliance validator
        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.ComplianceValidator = CustomComplianceValidator
            mock_import.return_value = mock_module

            custom_rule = ValidationRule(
                rule_type="compliance:license_check",
                description="License check",
                failure_message="LICENSE file missing",
                expected_behavior="LICENSE file should exist",
            )

            custom_result = registry.execute_rule(
                rule=custom_rule,
                bundle=bundle,
                provider="compliance_package.validators:ComplianceValidator",
            )

        # Built-in should pass (README exists)
        assert builtin_result is None

        # Custom should fail (LICENSE doesn't exist)
        assert custom_result is not None

    def test_plugin_validator_receives_correct_parameters(self):
        """Test that plugin validators receive correct parameters."""

        class ParameterTrackingValidator(BaseValidator):
            """Validator that tracks what parameters it receives."""

            received_params = {}

            @property
            def validation_type(self) -> str:
                return "test:param_tracker"

            @property
            def computation_type(self) -> Literal["programmatic", "llm"]:
                return "programmatic"

            def validate(
                self,
                rule: ValidationRule,
                bundle: DocumentBundle,
                all_bundles: Optional[List[DocumentBundle]] = None,
                ignore_patterns: Optional[List[str]] = None,
            ) -> Optional[DocumentRule]:
                # Track received parameters
                ParameterTrackingValidator.received_params = {
                    "rule_type": rule.rule_type,
                    "rule_description": rule.description,
                    "bundle_id": bundle.bundle_id,
                    "all_bundles_count": len(all_bundles) if all_bundles else 0,
                }
                return None

        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.ParamValidator = ParameterTrackingValidator
            mock_import.return_value = mock_module

            bundle = DocumentBundle(
                bundle_id="param-test-bundle",
                bundle_type="test",
                bundle_strategy="collection",
                files=[],
                project_path=Path("/tmp"),
            )

            rule = ValidationRule(
                rule_type="test:param_tracker",
                description="Test parameter passing",
                failure_message="Test failed",
                expected_behavior="Test passed",
            )

            other_bundle = DocumentBundle(
                bundle_id="other-bundle",
                bundle_type="test",
                bundle_strategy="collection",
                files=[],
                project_path=Path("/tmp"),
            )

            # Execute with all_bundles
            registry.execute_rule(
                rule=rule,
                bundle=bundle,
                all_bundles=[bundle, other_bundle],
                provider="test_package:ParamValidator",
            )

            # Check parameters were received correctly
            assert ParameterTrackingValidator.received_params["rule_type"] == "test:param_tracker"
            assert (
                ParameterTrackingValidator.received_params["rule_description"]
                == "Test parameter passing"
            )
            assert ParameterTrackingValidator.received_params["bundle_id"] == "param-test-bundle"
            assert ParameterTrackingValidator.received_params["all_bundles_count"] == 2

    def test_plugin_computation_type_query(self):
        """Test querying computation type for plugin validators."""
        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.SecurityValidator = CustomSecurityValidator
            mock_import.return_value = mock_module

            # Query computation type (this will load the plugin)
            comp_type = registry.get_computation_type(
                "security:vulnerability_scan",
                provider="security_package.validators:SecurityValidator",
            )

            assert comp_type == "programmatic"

            # Query is_programmatic
            is_prog = registry.is_programmatic(
                "security:vulnerability_scan",
                provider="security_package.validators:SecurityValidator",
            )

            assert is_prog is True


class TestPluginErrorHandling:
    """Test error handling in the plugin system."""

    def test_plugin_validation_error_propagates(self, tmp_path):
        """Test that validation errors from plugins propagate correctly."""

        class ErrorValidator(BaseValidator):
            """Validator that raises an error during validation."""

            @property
            def validation_type(self) -> str:
                return "test:error"

            @property
            def computation_type(self) -> Literal["programmatic", "llm"]:
                return "programmatic"

            def validate(
                self,
                rule: ValidationRule,
                bundle: DocumentBundle,
                all_bundles: Optional[List[DocumentBundle]] = None,
                ignore_patterns: Optional[List[str]] = None,
            ) -> Optional[DocumentRule]:
                raise ValueError("Simulated validation error")

        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.ErrorValidator = ErrorValidator
            mock_import.return_value = mock_module

            bundle = DocumentBundle(
                bundle_id="error-test",
                bundle_type="test",
                bundle_strategy="collection",
                files=[],
                project_path=tmp_path,
            )

            rule = ValidationRule(
                rule_type="test:error",
                description="Error test",
                failure_message="Failed",
                expected_behavior="Should pass",
            )

            # Error should propagate
            with pytest.raises(ValueError, match="Simulated validation error"):
                registry.execute_rule(
                    rule=rule,
                    bundle=bundle,
                    provider="test_package:ErrorValidator",
                )

    def test_plugin_missing_required_property(self):
        """Test error when plugin is missing required property."""

        class IncompleteValidator:
            """Validator missing required properties."""

            def __init__(self, loader=None):
                pass

            def validate(self, rule, bundle, all_bundles=None):
                return None

        registry = ValidatorRegistry()

        with patch("importlib.import_module") as mock_import:
            mock_module = MagicMock()
            mock_module.IncompleteValidator = IncompleteValidator
            mock_import.return_value = mock_module

            # Should fail because IncompleteValidator doesn't inherit from BaseValidator
            with pytest.raises(TypeError, match="must inherit from BaseValidator"):
                registry._load_validator(
                    provider="test_package:IncompleteValidator",
                    validation_type="test:incomplete",
                )


class TestPluginCaching:
    """Test plugin caching behavior."""

    def test_plugin_loaded_once_and_cached(self):
        """Test that plugins are loaded once and cached for reuse."""
        # Clear the cache before testing
        ValidatorRegistry._loaded_plugins.clear()

        registry = ValidatorRegistry()
        load_count = 0

        def counting_import(module_path):
            nonlocal load_count
            load_count += 1
            mock_module = MagicMock()
            mock_module.SecurityValidator = CustomSecurityValidator
            return mock_module

        with patch("importlib.import_module", side_effect=counting_import):
            # First call - should import
            registry.get_computation_type(
                "security:vulnerability_scan",
                provider="security_package.validators:SecurityValidator",
            )

            # Second call - should use cache
            registry.get_computation_type(
                "security:vulnerability_scan",
                provider="security_package.validators:SecurityValidator",
            )

            # Third call - should use cache
            registry.is_programmatic(
                "security:vulnerability_scan",
                provider="security_package.validators:SecurityValidator",
            )

            # Should only import once
            assert load_count == 1

    def test_different_plugins_loaded_separately(self):
        """Test that different plugins are loaded separately."""
        # Clear the cache before testing
        ValidatorRegistry._loaded_plugins.clear()

        registry = ValidatorRegistry()
        loaded_modules = set()

        def tracking_import(module_path):
            loaded_modules.add(module_path)
            mock_module = MagicMock()
            if "security" in module_path:
                mock_module.SecurityValidator = CustomSecurityValidator
            else:
                mock_module.ComplianceValidator = CustomComplianceValidator
            return mock_module

        with patch("importlib.import_module", side_effect=tracking_import):
            # Load security validator
            registry.get_computation_type(
                "security:vulnerability_scan",
                provider="security_package.validators:SecurityValidator",
            )

            # Load compliance validator
            registry.get_computation_type(
                "compliance:license_check",
                provider="compliance_package.validators:ComplianceValidator",
            )

            # Both should be loaded
            assert len(loaded_modules) == 2
            assert "security_package.validators" in loaded_modules
            assert "compliance_package.validators" in loaded_modules
