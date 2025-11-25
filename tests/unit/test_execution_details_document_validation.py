"""Tests that execution_details are populated for document-level validation rules."""

import tempfile
from pathlib import Path

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    DriftConfig,
    DriftLearningType,
    ValidationRule,
    ValidationRulesConfig,
)
from drift.core.analyzer import DriftAnalyzer


class TestDocumentValidationExecutionDetails:
    """Test that execution_details are populated for document validation."""

    def test_execution_details_populated_for_document_validation(self):
        """Test that execution_details include document validation rule results."""
        # Create a temporary project directory
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create a .claude.md file so the rule passes
            (project_path / ".claude.md").write_text("# Test Project\n")

            # Create a config with document-level validation
            config = DriftConfig(
                drift_learning_types={
                    "claude_md_missing": DriftLearningType(
                        description="Test if .claude.md exists",
                        scope="project_level",
                        context="Test if .claude.md exists",
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
                                    description="Validates .claude.md files exist",
                                    file_path=".claude.md",
                                    failure_message=".claude.md file is missing",
                                    expected_behavior=(
                                        ".claude.md file should exist in project root"
                                    ),
                                )
                            ],
                        ),
                    )
                }
            )

            # Run analysis with no conversations (document validation only)
            analyzer = DriftAnalyzer(config=config, project_path=str(project_path))
            result = analyzer.analyze_documents()

            # The execution_details should be populated
            assert "execution_details" in result.metadata
            exec_details = result.metadata["execution_details"]

            # Should have at least one execution detail
            assert len(exec_details) > 0, "execution_details should not be empty"

            # Find the claude_md_missing rule
            claude_md_detail = None
            for detail in exec_details:
                if detail.get("rule_name") == "claude_md_missing":
                    claude_md_detail = detail
                    break

            assert (
                claude_md_detail is not None
            ), "Should have execution detail for claude_md_missing rule"

            # Check required fields are present
            assert "status" in claude_md_detail
            assert claude_md_detail["status"] == "passed"

            assert "rule_description" in claude_md_detail
            assert "Validates .claude.md files exist" in claude_md_detail["rule_description"]

            # Check execution context is present
            assert (
                "execution_context" in claude_md_detail
            ), "Should have execution_context explaining what was checked"
            exec_context = claude_md_detail["execution_context"]

            assert "bundle_type" in exec_context
            assert exec_context["bundle_type"] == "project_config"

            assert "files" in exec_context
            assert ".claude.md" in exec_context["files"]

            # Check validation results
            assert "validation_results" in claude_md_detail
            validation = claude_md_detail["validation_results"]

            assert "rule_type" in validation
            assert validation["rule_type"] == "file_exists"

    def test_execution_details_populated_when_no_conversations(self):
        """Test execution_details are populated even when there are 0 conversations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir)

            # Create .claude.md
            (project_path / ".claude.md").write_text("# Test\n")

            config = DriftConfig(
                drift_learning_types={
                    "test_rule": DriftLearningType(
                        description="Test rule",
                        scope="project_level",
                        context="Test rule",
                        requires_project_context=True,
                        validation_rules=ValidationRulesConfig(
                            document_bundle=DocumentBundleConfig(
                                bundle_type="test",
                                bundle_strategy=BundleStrategy.COLLECTION,
                                file_patterns=["*.md"],
                            ),
                            rules=[
                                ValidationRule(
                                    rule_type="file_exists",
                                    description="Test validation",
                                    file_path=".claude.md",
                                    failure_message="Test failure",
                                    expected_behavior="Test should pass",
                                )
                            ],
                        ),
                    )
                }
            )

            analyzer = DriftAnalyzer(config=config, project_path=str(project_path))
            result = analyzer.analyze_documents()

            # Even with 0 conversations, execution_details should be populated
            assert result.summary.total_conversations == 0
            assert "execution_details" in result.metadata
            assert len(result.metadata["execution_details"]) > 0
