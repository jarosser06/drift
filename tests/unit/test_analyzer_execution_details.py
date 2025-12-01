"""Test that analyzer.analyze_documents() returns execution_details."""

import tempfile
from pathlib import Path

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    DriftConfig,
    RuleDefinition,
    ValidationRule,
    ValidationRulesConfig,
)
from drift.core.analyzer import DriftAnalyzer


class TestAnalyzerExecutionDetails:
    """Test that analyze_documents returns execution_details."""

    def test_analyze_documents_returns_execution_details_for_passed_rule(self):
        """Test that analyze_documents returns execution_details when a rule passes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create .claude.md so rule passes
            (project_path / ".claude.md").write_text("# Test\n")

            config = DriftConfig(
                rule_definitions={
                    "claude_md_missing": RuleDefinition(
                        description="Test rule",
                        scope="project_level",
                        context="Test context",
                        requires_project_context=True,
                        validation_rules=ValidationRulesConfig(
                            document_bundle=DocumentBundleConfig(
                                bundle_type="project_config",
                                bundle_strategy=BundleStrategy.COLLECTION,
                                file_patterns=[".claude.md", "README.md"],
                            ),
                            rules=[
                                ValidationRule(
                                    rule_type="file_exists",
                                    description="Validates .claude.md exists",
                                    file_path=".claude.md",
                                    failure_message="Missing .claude.md",
                                    expected_behavior="Should have .claude.md",
                                )
                            ],
                        ),
                    )
                }
            )

            analyzer = DriftAnalyzer(config=config, project_path=str(project_path))
            result = analyzer.analyze_documents()

            # MUST have execution_details in metadata
            assert (
                "execution_details" in result.metadata
            ), f"execution_details missing from metadata. Keys: {result.metadata.keys()}"

            exec_details = result.metadata["execution_details"]

            # MUST have at least one execution detail
            assert (
                len(exec_details) > 0
            ), "execution_details is empty! Should have 1 detail for claude_md_missing rule"

            # Find the claude_md_missing detail
            detail = None
            for d in exec_details:
                if d.get("rule_name") == "claude_md_missing":
                    detail = d
                    break

            assert (
                detail is not None
            ), f"No execution detail for claude_md_missing. Got: {exec_details}"

            # Check required fields
            assert (
                detail["status"] == "passed"
            ), f"Rule should have passed. Got status: {detail.get('status')}"

            assert (
                "execution_context" in detail
            ), f"Missing execution_context. Got keys: {detail.keys()}"

            exec_context = detail["execution_context"]
            assert "bundle_type" in exec_context
            assert "files" in exec_context
            assert ".claude.md" in exec_context["files"]

            assert "validation_results" in detail
            validation = detail["validation_results"]
            assert "rule_type" in validation
            assert validation["rule_type"] == "file_exists"

    def test_analyze_documents_returns_execution_details_for_failed_rule(self):
        """Test that analyze_documents returns execution_details when a rule fails."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # DON'T create .claude.md so rule fails

            config = DriftConfig(
                rule_definitions={
                    "claude_md_missing": RuleDefinition(
                        description="Test rule",
                        scope="project_level",
                        context="Test context",
                        requires_project_context=True,
                        validation_rules=ValidationRulesConfig(
                            document_bundle=DocumentBundleConfig(
                                bundle_type="project_config",
                                bundle_strategy=BundleStrategy.COLLECTION,
                                file_patterns=[".claude.md", "README.md"],
                            ),
                            rules=[
                                ValidationRule(
                                    rule_type="file_exists",
                                    description="Validates .claude.md exists",
                                    file_path=".claude.md",
                                    failure_message="Missing .claude.md",
                                    expected_behavior="Should have .claude.md",
                                )
                            ],
                        ),
                    )
                }
            )

            analyzer = DriftAnalyzer(config=config, project_path=str(project_path))
            result = analyzer.analyze_documents()

            # MUST have execution_details
            assert "execution_details" in result.metadata
            exec_details = result.metadata["execution_details"]

            # MUST have at least one execution detail
            assert (
                len(exec_details) > 0
            ), "execution_details is empty! Should have 1 detail for claude_md_missing rule"

            # Find the claude_md_missing detail
            detail = None
            for d in exec_details:
                if d.get("rule_name") == "claude_md_missing":
                    detail = d
                    break

            assert (
                detail is not None
            ), f"No execution detail for claude_md_missing. Got: {exec_details}"

            # Check status is failed
            assert (
                detail["status"] == "failed"
            ), f"Rule should have failed. Got status: {detail.get('status')}"

    def test_execute_validation_rules_is_called_during_analyze_documents(self):
        """Test that _execute_validation_rules is actually called during analyze_documents."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)
            (project_path / ".claude.md").write_text("# Test\n")

            config = DriftConfig(
                rule_definitions={
                    "claude_md_missing": RuleDefinition(
                        description="Test rule",
                        scope="project_level",
                        context="Test context",
                        requires_project_context=True,
                        validation_rules=ValidationRulesConfig(
                            document_bundle=DocumentBundleConfig(
                                bundle_type="project_config",
                                bundle_strategy=BundleStrategy.COLLECTION,
                                file_patterns=[".claude.md"],
                            ),
                            rules=[
                                ValidationRule(
                                    rule_type="file_exists",
                                    description="Validates .claude.md exists",
                                    file_path=".claude.md",
                                    failure_message="Missing",
                                    expected_behavior="Should exist",
                                )
                            ],
                        ),
                    )
                }
            )

            analyzer = DriftAnalyzer(config=config, project_path=str(project_path))

            # Spy on _execute_validation_rules to ensure it gets called
            from unittest.mock import patch

            original_validate = analyzer._execute_validation_rules
            call_count = {"count": 0}

            def spy_validate(*args, **kwargs):
                call_count["count"] += 1
                return original_validate(*args, **kwargs)

            with patch.object(analyzer, "_execute_validation_rules", side_effect=spy_validate):
                result = analyzer.analyze_documents()

            # _execute_validation_rules MUST have been called
            assert call_count["count"] > 0, (
                "_execute_validation_rules was NEVER CALLED! "
                "analyze_documents must call it for validation_rules"
            )

            # And execution_details should be populated
            assert (
                len(result.metadata.get("execution_details", [])) > 0
            ), "execution_details is empty even though _execute_validation_rules was called"
