"""Tests for rule group formatting in output."""

from datetime import datetime

from drift.cli.output.markdown import MarkdownFormatter
from drift.config.models import DriftConfig, RuleDefinition
from drift.core.types import AnalysisResult, AnalysisSummary, CompleteAnalysisResult, Rule


class TestMarkdownFormatterGroups:
    """Tests for group-based formatting in MarkdownFormatter."""

    def test_format_rules_grouped_by_group_name(self):
        """Test that rules are grouped by group_name in output."""
        # Create config with rules in different groups
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "rule_one": RuleDefinition(
                    description="Rule one",
                    scope="project_level",
                    context="Context one",
                    requires_project_context=True,
                    group_name="Group A",
                ),
                "rule_two": RuleDefinition(
                    description="Rule two",
                    scope="project_level",
                    context="Context two",
                    requires_project_context=True,
                    group_name="Group B",
                ),
            },
            agent_tools={},
        )

        # Create rules in different groups
        rule_one = Rule(
            turn_number=1,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Issue one",
            expected_behavior="Expected one",
            rule_type="rule_one",
            group_name="Group A",
        )

        rule_two = Rule(
            turn_number=2,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Issue two",
            expected_behavior="Expected two",
            rule_type="rule_two",
            group_name="Group B",
        )

        analysis_result = AnalysisResult(
            session_id="test-session",
            agent_tool="test",
            conversation_file="/test/file",
            rules=[rule_one, rule_two],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
                conversations_with_drift=1,
            ),
            results=[analysis_result],
        )

        # Format output
        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Check that groups appear as headers
        assert "### Group A" in output
        assert "### Group B" in output

        # Check that rules appear under their groups
        assert "#### rule_one" in output
        assert "#### rule_two" in output

    def test_format_passed_rules_grouped(self):
        """Test that passed rules are grouped by group_name."""
        # Create config with rules in different groups
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "rule_one": RuleDefinition(
                    description="Rule one",
                    scope="project_level",
                    context="Context one",
                    requires_project_context=True,
                    group_name="Group A",
                ),
                "rule_two": RuleDefinition(
                    description="Rule two",
                    scope="project_level",
                    context="Context two",
                    requires_project_context=True,
                    group_name="Group B",
                ),
            },
            agent_tools={},
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=0,
                conversations_without_drift=1,
                rules_passed=["rule_one", "rule_two"],
            ),
            results=[],
        )

        # Format output
        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Check that groups appear in passed section
        assert "## Checks Passed" in output
        assert "### Group A" in output
        assert "### Group B" in output

    def test_rules_without_group_use_default(self):
        """Test that rules without group_name use default group."""
        # Create config with one rule having no group
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="Default Group",
            rule_definitions={
                "rule_one": RuleDefinition(
                    description="Rule one",
                    scope="project_level",
                    context="Context one",
                    requires_project_context=True,
                    # No group_name - should use default
                ),
            },
            agent_tools={},
        )

        rule_one = Rule(
            turn_number=1,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Issue one",
            expected_behavior="Expected one",
            rule_type="rule_one",
            group_name=None,  # Should be populated with default by analyzer
        )

        analysis_result = AnalysisResult(
            session_id="test-session",
            agent_tool="test",
            conversation_file="/test/file",
            rules=[rule_one],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
                conversations_with_drift=1,
            ),
            results=[analysis_result],
        )

        # Format output
        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Should use "General" as fallback if group_name is None
        # (formatter's _format_by_type handles this)
        assert "### General" in output or "### Default Group" in output

    def test_multiple_rules_in_same_group(self):
        """Test that multiple rules in same group are grouped together."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "rule_one": RuleDefinition(
                    description="Rule one",
                    scope="project_level",
                    context="Context one",
                    requires_project_context=True,
                    group_name="Shared Group",
                ),
                "rule_two": RuleDefinition(
                    description="Rule two",
                    scope="project_level",
                    context="Context two",
                    requires_project_context=True,
                    group_name="Shared Group",
                ),
            },
            agent_tools={},
        )

        rule_one = Rule(
            turn_number=1,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Issue one",
            expected_behavior="Expected one",
            rule_type="rule_one",
            group_name="Shared Group",
        )

        rule_two = Rule(
            turn_number=2,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Issue two",
            expected_behavior="Expected two",
            rule_type="rule_two",
            group_name="Shared Group",
        )

        analysis_result = AnalysisResult(
            session_id="test-session",
            agent_tool="test",
            conversation_file="/test/file",
            rules=[rule_one, rule_two],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
                conversations_with_drift=1,
            ),
            results=[analysis_result],
        )

        # Format output
        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Should have one group header for both rules
        group_count = output.count("### Shared Group")
        assert group_count == 1  # Only one group header

        # Both rules should appear
        assert "#### rule_one" in output
        assert "#### rule_two" in output


class TestMarkdownFormatterGroupsWarningsAndFailures:
    """Tests for grouping warnings vs failures."""

    def test_warnings_and_failures_grouped_separately(self):
        """Test that warnings and failures are grouped separately."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "warning_rule": RuleDefinition(
                    description="Warning rule",
                    scope="conversation_level",  # Defaults to WARNING
                    context="Warning context",
                    requires_project_context=False,
                    group_name="Test Group",
                ),
                "failure_rule": RuleDefinition(
                    description="Failure rule",
                    scope="project_level",  # Defaults to FAIL
                    context="Failure context",
                    requires_project_context=True,
                    group_name="Test Group",
                ),
            },
            agent_tools={},
        )

        warning_rule = Rule(
            turn_number=1,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Warning issue",
            expected_behavior="Expected warning",
            rule_type="warning_rule",
            group_name="Test Group",
        )

        failure_rule = Rule(
            turn_number=2,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Failure issue",
            expected_behavior="Expected failure",
            rule_type="failure_rule",
            group_name="Test Group",
        )

        analysis_result = AnalysisResult(
            session_id="test-session",
            agent_tool="test",
            conversation_file="/test/file",
            rules=[warning_rule, failure_rule],
            analysis_timestamp=datetime.now(),
        )

        from drift.core.types import AnalysisSummary, CompleteAnalysisResult

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
                conversations_with_drift=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Should have separate Warnings and Failures sections
        assert "## Warnings" in output
        assert "## Failures" in output

        # Both should have Test Group
        # Count occurrences - should appear in both sections
        test_group_count = output.count("### Test Group")
        assert test_group_count == 2


class TestMarkdownFormatterGroupsSorting:
    """Tests for group sorting in output."""

    def test_groups_sorted_alphabetically(self):
        """Test that groups are sorted alphabetically."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "rule_z": RuleDefinition(
                    description="Rule Z",
                    scope="project_level",
                    context="Context Z",
                    requires_project_context=True,
                    group_name="Z Group",
                ),
                "rule_a": RuleDefinition(
                    description="Rule A",
                    scope="project_level",
                    context="Context A",
                    requires_project_context=True,
                    group_name="A Group",
                ),
                "rule_m": RuleDefinition(
                    description="Rule M",
                    scope="project_level",
                    context="Context M",
                    requires_project_context=True,
                    group_name="M Group",
                ),
            },
            agent_tools={},
        )

        rules = [
            Rule(
                turn_number=1,
                agent_tool="test",
                conversation_file="/test/file",
                observed_behavior="Issue Z",
                expected_behavior="Expected Z",
                rule_type="rule_z",
                group_name="Z Group",
            ),
            Rule(
                turn_number=2,
                agent_tool="test",
                conversation_file="/test/file",
                observed_behavior="Issue A",
                expected_behavior="Expected A",
                rule_type="rule_a",
                group_name="A Group",
            ),
            Rule(
                turn_number=3,
                agent_tool="test",
                conversation_file="/test/file",
                observed_behavior="Issue M",
                expected_behavior="Expected M",
                rule_type="rule_m",
                group_name="M Group",
            ),
        ]

        analysis_result = AnalysisResult(
            session_id="test-session",
            agent_tool="test",
            conversation_file="/test/file",
            rules=rules,
            analysis_timestamp=datetime.now(),
        )

        from drift.core.types import AnalysisSummary, CompleteAnalysisResult

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=3,
                conversations_with_drift=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Find positions of groups in output
        a_pos = output.find("### A Group")
        m_pos = output.find("### M Group")
        z_pos = output.find("### Z Group")

        # Should be in alphabetical order
        assert a_pos < m_pos < z_pos


class TestMarkdownFormatterGroupsPassedRules:
    """Tests for grouping of passed rules."""

    def test_passed_rules_grouped_and_sorted(self):
        """Test that passed rules are grouped and sorted."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "rule_b": RuleDefinition(
                    description="Rule B",
                    scope="project_level",
                    context="Context B",
                    requires_project_context=True,
                    group_name="Group Y",
                ),
                "rule_a": RuleDefinition(
                    description="Rule A",
                    scope="project_level",
                    context="Context A",
                    requires_project_context=True,
                    group_name="Group X",
                ),
            },
            agent_tools={},
        )

        from drift.core.types import AnalysisSummary, CompleteAnalysisResult

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=0,
                conversations_without_drift=1,
                rules_passed=["rule_a", "rule_b"],
            ),
            results=[],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Should have passed section
        assert "## Checks Passed" in output

        # Groups should be sorted
        x_pos = output.find("### Group X")
        y_pos = output.find("### Group Y")
        assert x_pos < y_pos

        # Rules should appear under their groups
        assert "- **rule_a**: No issues found" in output
        assert "- **rule_b**: No issues found" in output


class TestMarkdownFormatterGroupsWithDefaultFallback:
    """Tests for formatter fallback to 'General' when group is None."""

    def test_formatter_fallback_when_group_none(self):
        """Test that formatter uses 'General' when rule.group_name is None."""
        # No config - formatter should use fallback
        formatter = MarkdownFormatter(config=None)

        rule = Rule(
            turn_number=1,
            agent_tool="test",
            conversation_file="/test/file",
            observed_behavior="Issue",
            expected_behavior="Expected",
            rule_type="test_rule",
            group_name=None,
        )

        analysis_result = AnalysisResult(
            session_id="test-session",
            agent_tool="test",
            conversation_file="/test/file",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        from drift.core.types import AnalysisSummary, CompleteAnalysisResult

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
                conversations_with_drift=1,
            ),
            results=[analysis_result],
        )

        output = formatter.format(result)

        # Should use "General" as fallback
        assert "### General" in output

    def test_formatter_uses_config_default_for_passed_rules(self):
        """Test that formatter uses config default for passed rules with no group."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="Custom Default",
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

        from drift.core.types import AnalysisSummary, CompleteAnalysisResult

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=0,
                conversations_without_drift=1,
                rules_passed=["test_rule"],
            ),
            results=[],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Should use custom default
        assert "### Custom Default" in output


class TestMarkdownFormatterGroupsWithDocumentRules:
    """Tests for formatting document rules with groups."""

    def test_document_rules_grouped_correctly(self):
        """Test that document-sourced rules are grouped correctly."""
        config = DriftConfig(
            providers={},
            models={},
            default_model="test",
            default_group_name="General",
            rule_definitions={
                "doc_rule": RuleDefinition(
                    description="Document rule",
                    scope="project_level",
                    context="Document context",
                    requires_project_context=True,
                    group_name="Documentation",
                )
            },
            agent_tools={},
        )

        rule = Rule(
            turn_number=0,
            agent_tool="documents",
            conversation_file="N/A",
            observed_behavior="Missing docs",
            expected_behavior="Complete docs",
            rule_type="doc_rule",
            group_name="Documentation",
            source_type="document",
            affected_files=["README.md", "CONTRIBUTING.md"],
        )

        analysis_result = AnalysisResult(
            session_id="document_analysis",
            agent_tool="documents",
            conversation_file="N/A",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        from drift.core.types import AnalysisSummary, CompleteAnalysisResult

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=1,
                conversations_with_drift=0,
                conversations_without_drift=0,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # Should have Documentation group
        assert "### Documentation" in output

        # Should show affected files
        assert "README.md" in output
        assert "CONTRIBUTING.md" in output

        # Should show document source
        assert "**Source:** document_analysis" in output
