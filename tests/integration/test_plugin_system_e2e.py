"""True end-to-end test for custom validation plugin system.

This test creates an actual Python package in a temporary directory,
adds it to sys.path, and loads it as a real 3rd party plugin without mocks.
"""

import sys
from pathlib import Path

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle
from drift.validation.validators import ValidatorRegistry


@pytest.fixture
def plugin_package(tmp_path):
    """Create a real 3rd party plugin package in a temporary directory.

    This creates:
        my_security_plugin/
            __init__.py
            validators.py  (contains SecurityScanValidator)
    """
    # Create package directory
    package_dir = tmp_path / "my_security_plugin"
    package_dir.mkdir()

    # Create __init__.py
    init_file = package_dir / "__init__.py"
    init_file.write_text('"""My custom security validation plugin."""\n')

    # Create validators.py with a real validator
    validators_file = package_dir / "validators.py"
    validators_file.write_text(
        '''"""Custom security validators."""

from typing import List, Literal, Optional

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class SecurityScanValidator(BaseValidator):
    """Custom security scanner that checks for common issues."""

    validation_type = "security:vulnerability_scan"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type."""
        return "programmatic"

    @property
    def supported_clients(self) -> List[str]:
        """Return supported client types."""
        return ["all"]

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check for security vulnerabilities.

        Looks for a vulnerabilities.txt file. If it exists and contains
        content, validation fails.
        """
        vuln_file = bundle.project_path / "vulnerabilities.txt"

        if vuln_file.exists() and vuln_file.is_file():
            content = vuln_file.read_text().strip()
            if content:
                # Found vulnerabilities - return failure
                vulns = content.split("\\n")
                return DocumentRule(
                    bundle_id=bundle.bundle_id,
                    bundle_type=bundle.bundle_type,
                    file_paths=["vulnerabilities.txt"],
                    observed_issue=f"Security scan failed: {content}",
                    expected_quality=rule.expected_behavior,
                    rule_type=rule.rule_type,
                    context=f"Found {len(vulns)} vulnerabilities",
                    failure_details={"vulnerabilities_found": vulns},
                )

        # No vulnerabilities found - validation passes
        return None


class ComplianceValidator(BaseValidator):
    """Custom compliance checker."""

    validation_type = "security:compliance_check"

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type."""
        return "programmatic"

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Check for required compliance files."""
        required_files = rule.params.get("required_files", ["LICENSE", "SECURITY.md"])

        missing = []
        for filename in required_files:
            if not (bundle.project_path / filename).exists():
                missing.append(filename)

        if missing:
            return DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=missing,
                observed_issue=f"Missing required compliance files: {', '.join(missing)}",
                expected_quality=rule.expected_behavior,
                rule_type=rule.rule_type,
                context=f"Missing {len(missing)} compliance files",
                failure_details={"missing_files": missing},
            )

        return None
'''
    )

    # Add the parent directory to sys.path so we can import the package
    sys.path.insert(0, str(tmp_path))

    yield package_dir

    # Cleanup: remove from sys.path
    if str(tmp_path) in sys.path:
        sys.path.remove(str(tmp_path))


@pytest.fixture
def vulnerable_project(tmp_path):
    """Create a test project with security vulnerabilities."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # Create vulnerabilities file
    vuln_file = project_dir / "vulnerabilities.txt"
    vuln_file.write_text(
        "SQL Injection in auth.py line 42\n"
        "XSS vulnerability in templates/profile.html\n"
        "Hardcoded credentials in config.py"
    )

    return project_dir


@pytest.fixture
def secure_project(tmp_path):
    """Create a test project without security vulnerabilities."""
    project_dir = tmp_path / "secure_project"
    project_dir.mkdir()

    # Create empty vulnerabilities file (or no file at all)
    vuln_file = project_dir / "vulnerabilities.txt"
    vuln_file.write_text("")

    return project_dir


@pytest.fixture
def non_compliant_project(tmp_path):
    """Create a project missing compliance files."""
    project_dir = tmp_path / "non_compliant_project"
    project_dir.mkdir()

    # Create a README but no LICENSE or SECURITY.md
    (project_dir / "README.md").write_text("# Test Project")

    return project_dir


class TestRealPluginE2E:
    """True end-to-end tests with real plugin loading (no mocks)."""

    def test_load_real_plugin_and_detect_vulnerabilities(self, plugin_package, vulnerable_project):
        """E2E: Load a real plugin package and execute validation.

        This test:
        1. Creates a real Python package with a validator
        2. Adds it to sys.path
        3. Loads it via ValidatorRegistry WITHOUT mocks
        4. Executes validation on a real project directory
        """
        registry = ValidatorRegistry()

        # Create a bundle representing the vulnerable project
        bundle = DocumentBundle(
            bundle_id="vulnerable-project",
            bundle_type="project",
            bundle_strategy="collection",
            files=[],
            project_path=vulnerable_project,
        )

        # Create validation rule that uses our custom plugin
        rule = ValidationRule(
            rule_type="security:vulnerability_scan",
            description="Scan for security vulnerabilities using custom plugin",
            failure_message="Security vulnerabilities detected by scanner",
            expected_behavior="No security vulnerabilities should exist",
        )

        # Execute validation - this will ACTUALLY import the plugin
        result = registry.execute_rule(
            rule=rule,
            bundle=bundle,
            provider="my_security_plugin.validators:SecurityScanValidator",
        )

        # Assertions
        assert result is not None, "Should detect vulnerabilities"
        assert result.bundle_id == "vulnerable-project"
        assert "SQL Injection" in result.observed_issue
        assert result.failure_details is not None
        assert "vulnerabilities_found" in result.failure_details

    def test_load_real_plugin_passes_on_secure_project(self, plugin_package, secure_project):
        """E2E: Plugin validation passes on secure project."""
        registry = ValidatorRegistry()

        bundle = DocumentBundle(
            bundle_id="secure-project",
            bundle_type="project",
            bundle_strategy="collection",
            files=[],
            project_path=secure_project,
        )

        rule = ValidationRule(
            rule_type="security:vulnerability_scan",
            description="Security scan",
            failure_message="Vulnerabilities found",
            expected_behavior="No vulnerabilities",
        )

        # Execute validation - loads real plugin
        result = registry.execute_rule(
            rule=rule,
            bundle=bundle,
            provider="my_security_plugin.validators:SecurityScanValidator",
        )

        # Should pass (no vulnerabilities)
        assert result is None

    def test_load_multiple_validators_from_same_package(
        self, plugin_package, non_compliant_project
    ):
        """E2E: Load multiple validators from the same plugin package."""
        registry = ValidatorRegistry()

        # Add some files to the project
        (non_compliant_project / "vulnerabilities.txt").write_text("XSS in app.py")

        bundle = DocumentBundle(
            bundle_id="non-compliant",
            bundle_type="project",
            bundle_strategy="collection",
            files=[],
            project_path=non_compliant_project,
        )

        # Test first validator - security scan
        security_rule = ValidationRule(
            rule_type="security:vulnerability_scan",
            description="Security scan",
            failure_message="Security issues",
            expected_behavior="No issues",
        )

        security_result = registry.execute_rule(
            rule=security_rule,
            bundle=bundle,
            provider="my_security_plugin.validators:SecurityScanValidator",
        )

        # Test second validator from SAME package - compliance check
        compliance_rule = ValidationRule(
            rule_type="security:compliance_check",
            description="Compliance check",
            failure_message="Missing compliance files",
            expected_behavior="All compliance files present",
            params={"required_files": ["LICENSE", "SECURITY.md"]},
        )

        compliance_result = registry.execute_rule(
            rule=compliance_rule,
            bundle=bundle,
            provider="my_security_plugin.validators:ComplianceValidator",
        )

        # Both should fail
        assert security_result is not None, "Should detect security issue"
        assert compliance_result is not None, "Should detect missing compliance files"
        assert "LICENSE" in compliance_result.observed_issue
        assert "SECURITY.md" in compliance_result.observed_issue

    def test_plugin_caching_works_correctly(self, plugin_package, secure_project):
        """E2E: Verify that loaded plugins are cached correctly."""
        registry = ValidatorRegistry()

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="project",
            bundle_strategy="collection",
            files=[],
            project_path=secure_project,
        )

        rule = ValidationRule(
            rule_type="security:vulnerability_scan",
            description="Security scan",
            failure_message="Issues found",
            expected_behavior="No issues",
        )

        # Load plugin first time
        result1 = registry.execute_rule(
            rule=rule,
            bundle=bundle,
            provider="my_security_plugin.validators:SecurityScanValidator",
        )

        # Load same plugin second time - should use cache
        result2 = registry.execute_rule(
            rule=rule,
            bundle=bundle,
            provider="my_security_plugin.validators:SecurityScanValidator",
        )

        # Both should work and return None (passing)
        assert result1 is None
        assert result2 is None

        # Verify plugin is in cache
        cache_key = (
            "security:vulnerability_scan:my_security_plugin.validators:SecurityScanValidator"
        )
        assert cache_key in registry._loaded_plugins

    def test_plugin_error_handling_module_not_found(self):
        """E2E: Test error handling when plugin module doesn't exist."""
        registry = ValidatorRegistry()

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="project",
            bundle_strategy="collection",
            files=[],
            project_path=Path("/tmp"),
        )

        rule = ValidationRule(
            rule_type="fake:validator",
            description="Test",
            failure_message="Failed",
            expected_behavior="Pass",
        )

        # Try to load non-existent plugin
        with pytest.raises(ModuleNotFoundError) as exc_info:
            registry.execute_rule(
                rule=rule,
                bundle=bundle,
                provider="nonexistent_package.validators:FakeValidator",
            )

        assert "Provider module not found" in str(exc_info.value)
        assert "nonexistent_package" in str(exc_info.value)

    def test_plugin_error_handling_class_not_found(self, plugin_package):
        """E2E: Test error handling when class doesn't exist in module."""
        registry = ValidatorRegistry()

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="project",
            bundle_strategy="collection",
            files=[],
            project_path=Path("/tmp"),
        )

        rule = ValidationRule(
            rule_type="fake:validator",
            description="Test",
            failure_message="Failed",
            expected_behavior="Pass",
        )

        # Try to load non-existent class from existing module
        with pytest.raises(AttributeError) as exc_info:
            registry.execute_rule(
                rule=rule,
                bundle=bundle,
                provider="my_security_plugin.validators:NonExistentValidator",
            )

        assert "Provider class not found" in str(exc_info.value)
        assert "NonExistentValidator" in str(exc_info.value)
