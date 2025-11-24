"""Integration tests for rule-based validation."""

import pytest

from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    DriftConfig,
    DriftLearningType,
    ModelConfig,
    ProviderConfig,
    ProviderType,
    ValidationRule,
    ValidationRulesConfig,
    ValidationType,
)
from drift.core.analyzer import DriftAnalyzer


class TestRuleBasedValidation:
    """Integration tests for rule-based validation system."""

    @pytest.fixture
    def test_project(self, tmp_path):
        """Create a test project structure."""
        # Create some test files
        (tmp_path / "README.md").write_text("# Test Project")
        (tmp_path / "CLAUDE.md").write_text("# Claude Instructions")

        # Create skill structure
        skill_dir = tmp_path / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "# Test Skill\n\n## Prerequisites\n\nNone\n\n## Description\n\nTest skill"
        )

        # Create command file
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "test.md").write_text("# Test Command")

        return tmp_path

    @pytest.fixture
    def base_config(self):
        """Create a base configuration."""
        return DriftConfig(
            providers={
                "bedrock": ProviderConfig(
                    provider=ProviderType.BEDROCK,
                    params={"region": "us-east-1"},
                )
            },
            models={
                "haiku": ModelConfig(
                    provider="bedrock",
                    model_id="anthropic.claude-3-haiku-20240307-v1:0",
                )
            },
            default_model="haiku",
            drift_learning_types={},
        )

    def test_file_exists_validation_passes(self, test_project, base_config):
        """Test that file existence validation passes when file exists."""
        # Create learning type with file existence rule
        learning_type_config = DriftLearningType(
            description="Check CLAUDE.md exists",
            detection_prompt="Not used for programmatic",
            analysis_method="programmatic",
            scope="project_level",
            context="CLAUDE.md is required",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                scope="project_level",
                document_bundle=DocumentBundleConfig(
                    bundle_type="configuration",
                    file_patterns=["CLAUDE.md"],
                    bundle_strategy=BundleStrategy.COLLECTION,
                ),
                rules=[
                    ValidationRule(
                        rule_type=ValidationType.FILE_EXISTS,
                        description="CLAUDE.md must exist",
                        file_path="CLAUDE.md",
                        failure_message="CLAUDE.md not found",
                        expected_behavior="CLAUDE.md should exist",
                    )
                ],
            ),
        )

        base_config.drift_learning_types["claude_doc_exists"] = learning_type_config

        # Create analyzer
        analyzer = DriftAnalyzer(config=base_config, project_path=test_project)

        # Analyze documents
        result = analyzer.analyze_documents(learning_types=["claude_doc_exists"])

        # Should have no learnings (file exists, validation passes)
        assert len(result.metadata["document_learnings"]) == 0

    def test_file_exists_validation_fails(self, test_project, base_config):
        """Test that file existence validation fails when file missing."""
        # Create learning type checking for non-existent file
        learning_type_config = DriftLearningType(
            description="Check MISSING.md exists",
            detection_prompt="Not used for programmatic",
            analysis_method="programmatic",
            scope="project_level",
            context="MISSING.md should exist",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                scope="project_level",
                document_bundle=DocumentBundleConfig(
                    bundle_type="configuration",
                    file_patterns=["MISSING.md"],
                    bundle_strategy=BundleStrategy.COLLECTION,
                ),
                rules=[
                    ValidationRule(
                        rule_type=ValidationType.FILE_EXISTS,
                        description="MISSING.md must exist",
                        file_path="MISSING.md",
                        failure_message="MISSING.md not found",
                        expected_behavior="MISSING.md should exist",
                    )
                ],
            ),
        )

        base_config.drift_learning_types["missing_doc"] = learning_type_config

        # Create analyzer
        analyzer = DriftAnalyzer(config=base_config, project_path=test_project)

        # Analyze documents
        result = analyzer.analyze_documents(learning_types=["missing_doc"])

        # Should have one learning (file missing, validation fails)
        assert len(result.metadata["document_learnings"]) == 1

        learning = result.metadata["document_learnings"][0]
        assert learning["learning_type"] == "missing_doc"
        assert learning["observed_issue"] == "MISSING.md not found"
        assert learning["expected_quality"] == "MISSING.md should exist"
        assert "MISSING.md" in learning["file_paths"]

    def test_file_not_exists_validation_inverted(self, test_project, base_config):
        """Test that FILE_NOT_EXISTS correctly inverts the logic."""
        # Create learning type checking that a file should NOT exist
        # CLAUDE.md exists, so this should fail
        learning_type_config = DriftLearningType(
            description="CLAUDE.md should not exist",
            detection_prompt="Not used for programmatic",
            analysis_method="programmatic",
            scope="project_level",
            context="Testing inverted logic",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                scope="project_level",
                document_bundle=DocumentBundleConfig(
                    bundle_type="configuration",
                    file_patterns=["CLAUDE.md"],
                    bundle_strategy=BundleStrategy.COLLECTION,
                ),
                rules=[
                    ValidationRule(
                        rule_type=ValidationType.FILE_NOT_EXISTS,
                        description="CLAUDE.md should not exist",
                        file_path="CLAUDE.md",
                        failure_message="CLAUDE.md exists but should not",
                        expected_behavior="CLAUDE.md should be absent",
                    )
                ],
            ),
        )

        base_config.drift_learning_types["claude_not_exist"] = learning_type_config

        # Create analyzer
        analyzer = DriftAnalyzer(config=base_config, project_path=test_project)

        # Analyze documents
        result = analyzer.analyze_documents(learning_types=["claude_not_exist"])

        # Should have one learning (file exists but shouldn't, validation fails)
        assert len(result.metadata["document_learnings"]) == 1

        learning = result.metadata["document_learnings"][0]
        assert learning["learning_type"] == "claude_not_exist"
        assert learning["observed_issue"] == "CLAUDE.md exists but should not"

    def test_glob_pattern_validation(self, test_project, base_config):
        """Test validation with glob patterns."""
        # Create learning type checking for skill files
        learning_type_config = DriftLearningType(
            description="Check skill files exist",
            detection_prompt="Not used for programmatic",
            analysis_method="programmatic",
            scope="project_level",
            context="Skills are required",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                scope="project_level",
                document_bundle=DocumentBundleConfig(
                    bundle_type="skill",
                    file_patterns=[".claude/skills/*/SKILL.md"],
                    bundle_strategy=BundleStrategy.COLLECTION,
                ),
                rules=[
                    ValidationRule(
                        rule_type=ValidationType.FILE_EXISTS,
                        description="At least one skill must exist",
                        file_path=".claude/skills/*/SKILL.md",
                        failure_message="No skill files found",
                        expected_behavior="At least one SKILL.md should exist",
                    )
                ],
            ),
        )

        base_config.drift_learning_types["skill_exists"] = learning_type_config

        # Create analyzer
        analyzer = DriftAnalyzer(config=base_config, project_path=test_project)

        # Analyze documents
        result = analyzer.analyze_documents(learning_types=["skill_exists"])

        # Should have no learnings (skill files exist)
        assert len(result.metadata["document_learnings"]) == 0

    def test_multiple_rules_execution(self, test_project, base_config):
        """Test that multiple rules are executed."""
        # Create learning type with multiple rules
        learning_type_config = DriftLearningType(
            description="Check multiple requirements",
            detection_prompt="Not used for programmatic",
            analysis_method="programmatic",
            scope="project_level",
            context="Multiple checks",
            requires_project_context=True,
            validation_rules=ValidationRulesConfig(
                scope="project_level",
                document_bundle=DocumentBundleConfig(
                    bundle_type="mixed",
                    file_patterns=["*.md"],
                    bundle_strategy=BundleStrategy.COLLECTION,
                ),
                rules=[
                    ValidationRule(
                        rule_type=ValidationType.FILE_EXISTS,
                        description="README must exist",
                        file_path="README.md",
                        failure_message="README.md not found",
                        expected_behavior="README.md should exist",
                    ),
                    ValidationRule(
                        rule_type=ValidationType.FILE_EXISTS,
                        description="CLAUDE must exist",
                        file_path="CLAUDE.md",
                        failure_message="CLAUDE.md not found",
                        expected_behavior="CLAUDE.md should exist",
                    ),
                    ValidationRule(
                        rule_type=ValidationType.FILE_EXISTS,
                        description="MISSING check (will fail)",
                        file_path="MISSING.md",
                        failure_message="MISSING.md not found",
                        expected_behavior="MISSING.md should exist",
                    ),
                ],
            ),
        )

        base_config.drift_learning_types["multi_check"] = learning_type_config

        # Create analyzer
        analyzer = DriftAnalyzer(config=base_config, project_path=test_project)

        # Analyze documents
        result = analyzer.analyze_documents(learning_types=["multi_check"])

        # Should have one learning (only MISSING.md fails)
        assert len(result.metadata["document_learnings"]) == 1

        learning = result.metadata["document_learnings"][0]
        assert learning["observed_issue"] == "MISSING.md not found"

    def test_programmatic_without_validation_rules_raises_error(self, test_project, base_config):
        """Test that programmatic analysis without validation_rules raises error."""
        # Create learning type with programmatic but no validation_rules
        with pytest.raises(ValueError) as exc_info:
            DriftLearningType(
                description="Bad config",
                detection_prompt="Not used",
                analysis_method="programmatic",
                scope="project_level",
                context="Missing validation rules",
                requires_project_context=True,
                # No validation_rules!
            )

        assert "validation_rules must be provided" in str(exc_info.value)

    def test_ai_analyzed_with_validation_rules_raises_error(self, test_project, base_config):
        """Test that ai_analyzed with validation_rules raises error."""
        # Create learning type with ai_analyzed but validation_rules present
        with pytest.raises(ValueError) as exc_info:
            DriftLearningType(
                description="Bad config",
                detection_prompt="Used for AI",
                analysis_method="ai_analyzed",
                scope="project_level",
                context="Has validation rules",
                requires_project_context=True,
                validation_rules=ValidationRulesConfig(
                    scope="project_level",
                    document_bundle=DocumentBundleConfig(
                        bundle_type="test",
                        file_patterns=["*.md"],
                        bundle_strategy=BundleStrategy.COLLECTION,
                    ),
                    rules=[
                        ValidationRule(
                            rule_type=ValidationType.FILE_EXISTS,
                            description="Test",
                            file_path="test.md",
                            failure_message="Test",
                            expected_behavior="Test",
                        )
                    ],
                ),
            )

        assert "validation_rules should not be provided" in str(exc_info.value)

    def test_backward_compatibility_ai_analysis_unaffected(self, test_project, base_config, mocker):
        """Test that existing AI-based analysis still works."""
        # Mock the provider
        mock_provider = mocker.Mock()
        mock_provider.generate.return_value = "[]"  # Empty response

        # Create traditional AI-based learning type (no validation_rules)
        learning_type_config = DriftLearningType(
            description="AI-based check",
            detection_prompt="Look for issues",
            analysis_method="ai_analyzed",
            scope="project_level",
            context="Testing AI path",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="configuration",
                file_patterns=["*.md"],
                bundle_strategy=BundleStrategy.COLLECTION,
            ),
        )

        base_config.drift_learning_types["ai_check"] = learning_type_config

        # Create analyzer and inject mock provider
        analyzer = DriftAnalyzer(config=base_config, project_path=test_project)
        analyzer.providers["haiku"] = mock_provider

        # Analyze documents
        result = analyzer.analyze_documents(learning_types=["ai_check"])

        # Verify AI provider was called (not validation)
        assert mock_provider.generate.called
        assert len(result.metadata["document_learnings"]) == 0
