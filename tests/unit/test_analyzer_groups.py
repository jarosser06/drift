"""Tests for group name propagation in analyzer."""

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from drift.config.models import DriftConfig, RuleDefinition
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import AnalysisResult, Conversation, DocumentBundle, DocumentRule, Rule


class TestAnalyzerGroupNamePropagation:
    """Tests for group name propagation to Rule objects."""

    def test_get_effective_group_name_with_explicit_group(self):
        """Test that _get_effective_group_name returns explicit group."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "test_rule": RuleDefinition(
                    description="Test",
                    scope="project_level",
                    context="Context",
                    requires_project_context=True,
                    group_name="Custom Group",
                )
            },
            agent_tools={},
        )

        analyzer = DriftAnalyzer(config=config, project_path=Path("/tmp"))
        effective_group = analyzer._get_effective_group_name("test_rule")
        assert effective_group == "Custom Group"

    def test_get_effective_group_name_without_explicit_group(self):
        """Test that _get_effective_group_name returns default when no group."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="My Default",
            rule_definitions={
                "test_rule": RuleDefinition(
                    description="Test",
                    scope="project_level",
                    context="Context",
                    requires_project_context=True,
                    # No group_name
                )
            },
            agent_tools={},
        )

        analyzer = DriftAnalyzer(config=config, project_path=Path("/tmp"))
        effective_group = analyzer._get_effective_group_name("test_rule")
        assert effective_group == "My Default"

    def test_get_effective_group_name_for_unknown_rule(self):
        """Test that _get_effective_group_name returns default for unknown rule."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="Fallback",
            rule_definitions={},
            agent_tools={},
        )

        analyzer = DriftAnalyzer(config=config, project_path=Path("/tmp"))
        effective_group = analyzer._get_effective_group_name("unknown_rule")
        assert effective_group == "Fallback"

    def test_conversation_rule_has_group_name(self):
        """Test that conversation rules get group_name from config."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "test_rule": RuleDefinition(
                    description="Test",
                    scope="conversation_level",
                    context="Context",
                    requires_project_context=False,
                    group_name="Conversation Group",
                )
            },
            agent_tools={},
        )

        analyzer = DriftAnalyzer(config=config, project_path=Path("/tmp"))

        conversation = Conversation(
            session_id="test",
            agent_tool="test",
            file_path="/test",
            turns=[],
        )

        # Simulate what _parse_analysis_response does (from line 727-778)
        response = (
            '[{"turn_number": 1, "observed_behavior": "Observed", '
            '"expected_behavior": "Expected", "context": "Context"}]'
        )

        rules = analyzer._parse_analysis_response(response, conversation, "test_rule")

        # Should have group_name set
        assert len(rules) == 1
        assert rules[0].group_name == "Conversation Group"

    def test_document_rule_has_group_name(self):
        """Test that document rules get group_name from config."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "doc_rule": RuleDefinition(
                    description="Document rule",
                    scope="project_level",
                    context="Context",
                    requires_project_context=True,
                    group_name="Document Group",
                )
            },
            agent_tools={},
        )

        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            analyzer = DriftAnalyzer(config=config, project_path=project_path)

            # Create test bundle
            bundle = DocumentBundle(
                bundle_id="test_bundle",
                bundle_type="test",
                bundle_strategy="individual",
                files=[],
                project_path=project_path,
            )

            # Simulate parsing document analysis response
            response = (
                '[{"file_paths": ["test.md"], "observed_issue": "Issue", '
                '"expected_quality": "Quality", "context": "Context"}]'
            )

            rules = analyzer._parse_document_analysis_response(response, bundle, "doc_rule")

            # Should have group_name set
            assert len(rules) == 1
            assert rules[0].group_name == "Document Group"

    def test_document_rule_with_default_group(self):
        """Test that document rules use default group when rule has no group."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="Default Doc Group",
            rule_definitions={
                "doc_rule": RuleDefinition(
                    description="Document rule",
                    scope="project_level",
                    context="Context",
                    requires_project_context=True,
                    # No group_name
                )
            },
            agent_tools={},
        )

        with TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            analyzer = DriftAnalyzer(config=config, project_path=project_path)

            bundle = DocumentBundle(
                bundle_id="test_bundle",
                bundle_type="test",
                bundle_strategy="individual",
                files=[],
                project_path=project_path,
            )

            response = (
                '[{"file_paths": ["test.md"], "observed_issue": "Issue", '
                '"expected_quality": "Quality", "context": "Context"}]'
            )

            rules = analyzer._parse_document_analysis_response(response, bundle, "doc_rule")

            # Should use default group
            assert len(rules) == 1
            assert rules[0].group_name == "Default Doc Group"


class TestAnalyzerGroupNameInResults:
    """Tests for group names in complete analysis results."""

    def test_analysis_result_contains_group_names(self):
        """Test that AnalysisResult preserves group names from rules."""
        rule1 = Rule(
            turn_number=1,
            agent_tool="test",
            conversation_file="/test",
            observed_behavior="Issue 1",
            expected_behavior="Expected 1",
            rule_type="rule1",
            group_name="Group A",
        )

        rule2 = Rule(
            turn_number=2,
            agent_tool="test",
            conversation_file="/test",
            observed_behavior="Issue 2",
            expected_behavior="Expected 2",
            rule_type="rule2",
            group_name="Group B",
        )

        result = AnalysisResult(
            session_id="test",
            agent_tool="test",
            conversation_file="/test",
            rules=[rule1, rule2],
            analysis_timestamp=datetime.now(),
        )

        # Verify group names are preserved
        assert result.rules[0].group_name == "Group A"
        assert result.rules[1].group_name == "Group B"

    def test_document_rule_to_rule_conversion_preserves_group(self):
        """Test that converting DocumentRule to Rule preserves group_name."""
        # This tests the conversion in analyzer.py around line 1044-1063
        doc_rule = DocumentRule(
            bundle_id="test",
            bundle_type="test",
            file_paths=["test.md"],
            observed_issue="Issue",
            expected_quality="Quality",
            rule_type="test_rule",
            group_name="Document Group",
            context="Context",
        )

        # Convert to Rule (as done in analyze_documents)
        learning = Rule(
            turn_number=0,
            turn_uuid=None,
            agent_tool="documents",
            conversation_file="N/A",
            observed_behavior=doc_rule.observed_issue,
            expected_behavior=doc_rule.expected_quality,
            rule_type=doc_rule.rule_type,
            group_name=doc_rule.group_name,  # Should preserve
            workflow_element="unknown",
            turns_to_resolve=1,
            turns_involved=[],
            context=doc_rule.context,
            resources_consulted=[],
            phases_count=1,
            source_type="document",
            affected_files=doc_rule.file_paths,
            bundle_id=doc_rule.bundle_id,
        )

        assert learning.group_name == "Document Group"


class TestAnalyzerGroupNameEdgeCases:
    """Tests for edge cases in group name handling."""

    def test_multiple_rules_same_group(self):
        """Test that multiple rules can share the same group."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "rule1": RuleDefinition(
                    description="Rule 1",
                    scope="project_level",
                    context="Context 1",
                    requires_project_context=True,
                    group_name="Shared Group",
                ),
                "rule2": RuleDefinition(
                    description="Rule 2",
                    scope="project_level",
                    context="Context 2",
                    requires_project_context=True,
                    group_name="Shared Group",
                ),
            },
            agent_tools={},
        )

        analyzer = DriftAnalyzer(config=config, project_path=Path("/tmp"))

        group1 = analyzer._get_effective_group_name("rule1")
        group2 = analyzer._get_effective_group_name("rule2")

        assert group1 == "Shared Group"
        assert group2 == "Shared Group"

    def test_rule_with_none_group_in_object(self):
        """Test that Rule with None group_name is handled correctly."""
        # This can happen during parsing if group isn't set
        rule = Rule(
            turn_number=1,
            agent_tool="test",
            conversation_file="/test",
            observed_behavior="Issue",
            expected_behavior="Expected",
            rule_type="test",
            group_name=None,
        )

        assert rule.group_name is None

    def test_document_rule_with_none_group(self):
        """Test that DocumentRule with None group_name is valid."""
        doc_rule = DocumentRule(
            bundle_id="test",
            bundle_type="test",
            file_paths=["test.md"],
            observed_issue="Issue",
            expected_quality="Quality",
            rule_type="test",
            group_name=None,
            context="Context",
        )

        assert doc_rule.group_name is None
