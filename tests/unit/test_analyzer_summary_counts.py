"""Test analyzer summary statistics calculations."""

import tempfile
from pathlib import Path

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    DriftConfig,
    RuleDefinition,
    SeverityLevel,
    ValidationRule,
    ValidationRulesConfig,
)
from drift.core.analyzer import DriftAnalyzer


def test_summary_counts_consistency_with_severity():
    """Test that checks_failed/warned counts match number of failed/warned rule types."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Create test files
        (project_path / "file1.md").write_text("# File 1\n")
        (project_path / "file4.md").write_text("# File 4\n")
        # file2.md and file3.md intentionally missing

        # Config with:
        # - 2 FAIL severity rules (rule_fail_1, rule_fail_2) - missing files
        # - 1 WARNING severity rule (rule_warn_1) - missing file
        # - 1 FAIL severity rule (rule_pass) - file exists, will pass
        config = DriftConfig(
            rule_definitions={
                "rule_fail_1": RuleDefinition(
                    description="First fail rule",
                    scope="project_level",
                    context="Test context",
                    severity=SeverityLevel.FAIL,
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        document_bundle=DocumentBundleConfig(
                            bundle_type="test",
                            bundle_strategy=BundleStrategy.COLLECTION,
                            file_patterns=["*.md"],
                        ),
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Check file2.md exists",
                                file_path="file2.md",
                                failure_message="file2.md missing",
                                expected_behavior="file2.md should exist",
                            ),
                        ],
                    ),
                ),
                "rule_fail_2": RuleDefinition(
                    description="Second fail rule",
                    scope="project_level",
                    context="Test context",
                    severity=SeverityLevel.FAIL,
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        document_bundle=DocumentBundleConfig(
                            bundle_type="test",
                            bundle_strategy=BundleStrategy.COLLECTION,
                            file_patterns=["*.md"],
                        ),
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Check file3.md exists",
                                file_path="file3.md",
                                failure_message="file3.md missing",
                                expected_behavior="file3.md should exist",
                            ),
                        ],
                    ),
                ),
                "rule_warn_1": RuleDefinition(
                    description="First warning rule",
                    scope="project_level",
                    context="Test context",
                    severity=SeverityLevel.WARNING,
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        document_bundle=DocumentBundleConfig(
                            bundle_type="test",
                            bundle_strategy=BundleStrategy.COLLECTION,
                            file_patterns=["*.md"],
                        ),
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Check file5.md exists",
                                file_path="file5.md",
                                failure_message="file5.md missing",
                                expected_behavior="file5.md should exist",
                            ),
                        ],
                    ),
                ),
                "rule_pass": RuleDefinition(
                    description="Passing rule",
                    scope="project_level",
                    context="Test context",
                    severity=SeverityLevel.FAIL,
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        document_bundle=DocumentBundleConfig(
                            bundle_type="test",
                            bundle_strategy=BundleStrategy.COLLECTION,
                            file_patterns=["*.md"],
                        ),
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Check file4.md exists",
                                file_path="file4.md",
                                failure_message="file4.md missing",
                                expected_behavior="file4.md should exist",
                            ),
                        ],
                    ),
                ),
            }
        )

        # Run document analysis
        analyzer = DriftAnalyzer(config=config, project_path=project_path)
        result = analyzer.analyze_documents()

        summary = result.summary

        # Assertions:
        # - 3 total violations (rule_fail_1, rule_fail_2, rule_warn_1 - all missing files)
        assert (
            summary.total_rule_violations == 3
        ), f"Expected 3 violations, got {summary.total_rule_violations}"

        # - 4 rules total (3 fail/warn + 1 pass)
        assert len(summary.rules_checked) == 4, "Expected 4 rules checked"

        # - 2 rules failed (rule_fail_1, rule_fail_2)
        assert len(summary.rules_failed) == 2, "Expected 2 failed rules"

        # - 1 rule warned (rule_warn_1)
        assert len(summary.rules_warned) == 1, "Expected 1 warned rule"

        # - 1 rule passed (rule_pass)
        assert len(summary.rules_passed) == 1, "Expected 1 passed rule"

        # - checks_failed counts actual check executions (from execution_details)
        # Note: This is based on how many times validators ran, not number of rules
        # In COLLECTION strategy, each rule runs once per bundle
        assert summary.checks_failed >= len(summary.rules_failed), (
            f"checks_failed ({summary.checks_failed}) should be >= "
            f"len(rules_failed) ({len(summary.rules_failed)})"
        )

        # - checks_warned counts actual check executions
        assert summary.checks_warned >= len(summary.rules_warned), (
            f"checks_warned ({summary.checks_warned}) should be >= "
            f"len(rules_warned) ({len(summary.rules_warned)})"
        )

        # - CRITICAL: Math must be consistent
        # total_checks = passed + failed + warned + errored
        computed_total = (
            summary.checks_passed
            + summary.checks_failed
            + summary.checks_warned
            + summary.checks_errored
        )
        assert summary.total_checks == computed_total, (
            f"Math error! total_checks ({summary.total_checks}) != "
            f"checks_passed ({summary.checks_passed}) + "
            f"checks_failed ({summary.checks_failed}) + "
            f"checks_warned ({summary.checks_warned}) + "
            f"checks_errored ({summary.checks_errored}) = {computed_total}"
        )

        # - Verify rule lists
        assert "rule_fail_1" in summary.rules_failed
        assert "rule_fail_2" in summary.rules_failed
        assert "rule_warn_1" in summary.rules_warned
        assert "rule_pass" in summary.rules_passed


def test_summary_counts_math_consistency():
    """Test that total_checks equals checks_passed + checks_failed + checks_errored.

    This is a critical invariant that must always hold. The bug reported showed:
    - Total checks: 74
    - Checks passed: 73
    - Checks failed: 2
    - 73 + 2 = 75, not 74 (math error!)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir)

        # Create test files
        (project_path / "file1.md").write_text("# File 1\n")
        (project_path / "file2.md").write_text("# File 2\n")
        # file3.md intentionally missing

        # Config with 3 rules: 2 pass, 1 fails
        config = DriftConfig(
            rule_definitions={
                "rule_pass_1": RuleDefinition(
                    description="First passing rule",
                    scope="project_level",
                    context="Test context",
                    severity=SeverityLevel.FAIL,
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        document_bundle=DocumentBundleConfig(
                            bundle_type="test",
                            bundle_strategy=BundleStrategy.COLLECTION,
                            file_patterns=["*.md"],
                        ),
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Check file1.md exists",
                                file_path="file1.md",
                                failure_message="file1.md missing",
                                expected_behavior="file1.md should exist",
                            ),
                        ],
                    ),
                ),
                "rule_pass_2": RuleDefinition(
                    description="Second passing rule",
                    scope="project_level",
                    context="Test context",
                    severity=SeverityLevel.FAIL,
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        document_bundle=DocumentBundleConfig(
                            bundle_type="test",
                            bundle_strategy=BundleStrategy.COLLECTION,
                            file_patterns=["*.md"],
                        ),
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Check file2.md exists",
                                file_path="file2.md",
                                failure_message="file2.md missing",
                                expected_behavior="file2.md should exist",
                            ),
                        ],
                    ),
                ),
                "rule_fail": RuleDefinition(
                    description="Failing rule",
                    scope="project_level",
                    context="Test context",
                    severity=SeverityLevel.FAIL,
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        document_bundle=DocumentBundleConfig(
                            bundle_type="test",
                            bundle_strategy=BundleStrategy.COLLECTION,
                            file_patterns=["*.md"],
                        ),
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Check file3.md exists",
                                file_path="file3.md",
                                failure_message="file3.md missing",
                                expected_behavior="file3.md should exist",
                            ),
                        ],
                    ),
                ),
            }
        )

        # Run document analysis
        analyzer = DriftAnalyzer(config=config, project_path=project_path)
        result = analyzer.analyze_documents()

        summary = result.summary

        # CRITICAL: total_checks MUST equal the sum of all check counts
        computed_total = (
            summary.checks_passed
            + summary.checks_failed
            + summary.checks_warned
            + summary.checks_errored
        )
        assert summary.total_checks == computed_total, (
            f"Math error! total_checks ({summary.total_checks}) != "
            f"checks_passed ({summary.checks_passed}) + "
            f"checks_failed ({summary.checks_failed}) + "
            f"checks_warned ({summary.checks_warned}) + "
            f"checks_errored ({summary.checks_errored}) = {computed_total}"
        )

        # Verify actual counts
        assert summary.checks_passed == 2, f"Expected 2 passed, got {summary.checks_passed}"
        assert summary.checks_failed == 1, f"Expected 1 failed, got {summary.checks_failed}"
        assert summary.checks_errored == 0, f"Expected 0 errored, got {summary.checks_errored}"
        assert summary.total_checks == 3, f"Expected total 3, got {summary.total_checks}"
