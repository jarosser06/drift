"""Integration tests for ignore patterns functionality via parameter overrides."""

import tempfile
from pathlib import Path

import pytest

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    DriftConfig,
    PhaseDefinition,
    RuleDefinition,
    ValidationRule,
    ValidationRulesConfig,
)
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import DocumentBundle, DocumentFile


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)

        (project_path / "src").mkdir()
        (project_path / "tests").mkdir()
        (project_path / "docs").mkdir()
        (project_path / ".git").mkdir()
        (project_path / "__pycache__").mkdir()

        (project_path / "README.md").write_text("# Project")
        (project_path / "src" / "main.py").write_text("print('hello')")
        (project_path / "src" / "utils.py").write_text("def util(): pass")
        (project_path / "tests" / "test_main.py").write_text("def test(): pass")
        (project_path / "docs" / "guide.md").write_text("# Guide")
        (project_path / ".git" / "config").write_text("[core]")
        (project_path / "__pycache__" / "main.pyc").write_text("compiled")
        (project_path / "temp.tmp").write_text("temporary")
        (project_path / ".env").write_text("SECRET=value")

        yield project_path


class TestValidatorParamOverrides:
    """Tests for validator-level parameter overrides (replaces global_ignore)."""

    def test_validator_param_overrides_filters_files(self, temp_project_dir):
        """Test validator param overrides apply ignore patterns."""
        config = DriftConfig(
            # Use validator_param_overrides instead of global_ignore
            validator_param_overrides={
                "core:file_exists": {
                    "merge": {
                        "ignore_patterns": ["*.tmp", "**/__pycache__/**", ".env"],
                    }
                }
            },
            rule_definitions={
                "test_rule": RuleDefinition(
                    description="Test rule",
                    scope="project_level",
                    context="Testing",
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Files should exist",
                                params={"file_path": "**/*.py"},
                            )
                        ],
                        scope="project_level",
                        document_bundle=DocumentBundleConfig(
                            bundle_type="project",
                            file_patterns=["**/*.py", "**/*.tmp", ".env"],
                            bundle_strategy=BundleStrategy.COLLECTION,
                        ),
                    ),
                )
            },
        )

        analyzer = DriftAnalyzer(config=config, project_path=temp_project_dir)

        bundle_files = [
            DocumentFile(
                file_path=temp_project_dir / "src" / "main.py",
                relative_path="src/main.py",
                content="print('hello')",
            ),
            DocumentFile(
                file_path=temp_project_dir / "temp.tmp",
                relative_path="temp.tmp",
                content="temporary",
            ),
            DocumentFile(
                file_path=temp_project_dir / ".env", relative_path=".env", content="SECRET=value"
            ),
        ]

        # Bundle for testing (unused in this specific test)
        _ = DocumentBundle(
            bundle_id="test",
            bundle_type="project",
            bundle_strategy="collection",
            files=bundle_files,
            project_path=temp_project_dir,
        )

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Files should exist",
            params={"file_path": "**/*.py"},
        )

        # Merge params - should get ignore_patterns from validator overrides
        merged_params = analyzer._merge_params(
            base_params=rule.params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="General",
        )

        # Should have ignore patterns from validator override
        assert "ignore_patterns" in merged_params
        assert "*.tmp" in merged_params["ignore_patterns"]
        assert "**/__pycache__/**" in merged_params["ignore_patterns"]
        assert ".env" in merged_params["ignore_patterns"]


class TestRuleParamOverrides:
    """Tests for rule-specific parameter overrides."""

    def test_rule_param_overrides_add_ignore_patterns(self, temp_project_dir):
        """Test that rule-specific overrides can add additional ignore patterns."""
        config = DriftConfig(
            # Global validator override
            validator_param_overrides={
                "core:file_exists": {
                    "merge": {
                        "ignore_patterns": ["*.tmp"],
                    }
                }
            },
            # Rule-specific override
            rule_param_overrides={
                "test_rule": {
                    "merge": {
                        "ignore_patterns": [".env"],
                    }
                }
            },
            rule_definitions={
                "test_rule": RuleDefinition(
                    description="Test rule",
                    scope="project_level",
                    context="Testing",
                    requires_project_context=False,
                    validation_rules=ValidationRulesConfig(
                        rules=[
                            ValidationRule(
                                rule_type="core:file_exists",
                                description="Files should exist",
                                params={"file_path": "**/*.py"},
                            )
                        ],
                        scope="project_level",
                        document_bundle=DocumentBundleConfig(
                            bundle_type="project",
                            file_patterns=["**/*.py"],
                            bundle_strategy=BundleStrategy.COLLECTION,
                        ),
                    ),
                )
            },
        )

        analyzer = DriftAnalyzer(config=config, project_path=temp_project_dir)

        rule = ValidationRule(
            rule_type="core:file_exists",
            description="Files should exist",
            params={"file_path": "**/*.py"},
        )

        merged_params = analyzer._merge_params(
            base_params=rule.params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="General",
        )

        # Should have both validator and rule-level ignore patterns
        assert "ignore_patterns" in merged_params
        assert "*.tmp" in merged_params["ignore_patterns"]
        assert ".env" in merged_params["ignore_patterns"]


class TestPhaseParamOverrides:
    """Tests for phase-specific parameter overrides."""

    def test_phase_param_overrides_most_specific(self, temp_project_dir):
        """Test that phase-level overrides take precedence."""
        config = DriftConfig(
            validator_param_overrides={
                "core:file_exists": {
                    "merge": {
                        "ignore_patterns": ["*.tmp"],
                    }
                }
            },
            rule_param_overrides={
                "test_rule": {
                    "merge": {
                        "ignore_patterns": [".env"],
                    }
                },
                "General::test_rule::check_files": {
                    "merge": {
                        "ignore_patterns": ["*.log"],
                    }
                },
            },
            rule_definitions={
                "test_rule": RuleDefinition(
                    description="Test rule",
                    scope="project_level",
                    context="Testing",
                    requires_project_context=False,
                    phases=[
                        PhaseDefinition(
                            name="check_files",
                            type="core:file_exists",
                            params={"file_path": "**/*.py"},
                        )
                    ],
                )
            },
        )

        analyzer = DriftAnalyzer(config=config, project_path=temp_project_dir)

        merged_params = analyzer._merge_params(
            base_params={"file_path": "**/*.py"},
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="General",
            phase_name="check_files",
        )

        # Should have all levels of ignore patterns
        assert "ignore_patterns" in merged_params
        assert "*.tmp" in merged_params["ignore_patterns"]
        assert ".env" in merged_params["ignore_patterns"]
        assert "*.log" in merged_params["ignore_patterns"]
