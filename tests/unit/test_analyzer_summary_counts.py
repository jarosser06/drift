"""Test analyzer summary statistics calculations."""

from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

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
from drift.core.types import DocumentRule


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
                                rule_type="file_exists",
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
                                rule_type="file_exists",
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
                                rule_type="file_exists",
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
                                rule_type="file_exists",
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
        assert summary.total_rule_violations == 3, \
            f"Expected 3 violations, got {summary.total_rule_violations}"
        
        # - checks_failed should be 2 (rule_fail_1, rule_fail_2)
        assert summary.checks_failed == 2, \
            f"Expected 2 failed checks, got {summary.checks_failed}. rules_failed={summary.rules_failed}"
        
        # - checks_warned should be 1 (rule_warn_1)
        assert summary.checks_warned == 1, \
            f"Expected 1 warned check, got {summary.checks_warned}. rules_warned={summary.rules_warned}"
        
        # - CRITICAL: checks_failed must equal len(rules_failed)
        assert summary.checks_failed == len(summary.rules_failed), \
            f"checks_failed ({summary.checks_failed}) != len(rules_failed) ({len(summary.rules_failed)})"
        
        # - CRITICAL: checks_warned must equal len(rules_warned)
        assert summary.checks_warned == len(summary.rules_warned), \
            f"checks_warned ({summary.checks_warned}) != len(rules_warned) ({len(summary.rules_warned)})"
        
        # - Verify rule lists
        assert "rule_fail_1" in summary.rules_failed
        assert "rule_fail_2" in summary.rules_failed
        assert "rule_warn_1" in summary.rules_warned
        assert "rule_pass" in summary.rules_passed
