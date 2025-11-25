"""Unit tests for output formatters."""

import json
from datetime import datetime

from drift.cli.output.json import JsonFormatter
from drift.cli.output.markdown import MarkdownFormatter
from drift.core.types import (
    AnalysisResult,
    AnalysisSummary,
    CompleteAnalysisResult,
    FrequencyType,
    Learning,
    WorkflowElement,
)


class TestMarkdownFormatter:
    """Tests for MarkdownFormatter."""

    def test_get_format_name(self):
        """Test getting format name."""
        formatter = MarkdownFormatter()
        assert formatter.get_format_name() == "markdown"

    def test_format_empty_results(self):
        """Test formatting empty analysis results."""
        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "# Drift Analysis Results" in output
        assert "## Summary" in output
        assert "Total conversations: 0" in output
        assert "No Drift Detected" in output

    def test_format_no_learnings(self):
        """Test formatting results with conversations but no learnings."""
        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=2,
                total_learnings=0,
                conversations_without_drift=2,
            ),
            results=[],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "Total conversations: 2" in output
        assert "Total learnings: 0" in output
        assert "No Drift Detected" in output

    def test_format_with_learnings(self, sample_learning):
        """Test formatting results with learnings."""
        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/agent-session-123.jsonl",
            project_path="/path/to/project",
            learnings=[sample_learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=1,
                conversations_with_drift=1,
                by_type={"incomplete_work": 1},
                by_agent={"claude-code": 1},
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        # Check header
        assert "# Drift Analysis Results" in output

        # Check summary
        assert "Total conversations: 1" in output
        assert "Total learnings: 1" in output
        assert "incomplete_work (1)" in output
        assert "claude-code (1)" in output

        # Check learnings section (grouped by learning type)
        # incomplete_work is conversation_level scope by default, which maps to WARNING severity
        assert "## Warnings" in output
        assert "### incomplete_work" in output
        assert "**Session:** session-123" in output
        assert "**Agent Tool:** claude-code" in output
        assert f"**Turn:** {sample_learning.turn_number}" in output
        assert f"**Observed:** {sample_learning.observed_behavior}" in output
        assert f"**Expected:** {sample_learning.expected_behavior}" in output

    def test_format_multiple_learnings(self):
        """Test formatting multiple learnings."""
        learning1 = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action 1",
            expected_behavior="Intent 1",
            learning_type="incomplete_work",
        )

        learning2 = Learning(
            turn_number=3,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action 2",
            expected_behavior="Intent 2",
            learning_type="wrong_assumption",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning2, learning1],  # Out of order
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=2,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        # Both learning types should appear as headers
        assert "### incomplete_work" in output
        assert "### wrong_assumption" in output

        # Turn information should be present
        assert "**Turn:** 1" in output
        assert "**Turn:** 3" in output

    def test_format_learning_with_context(self):
        """Test formatting learning with context."""
        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test",
            context="Additional context information",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1, total_learnings=1),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "**Context:** Additional context information" in output

    def test_format_workflow_element(self):
        """Test formatting with workflow element."""
        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test",
            workflow_element=WorkflowElement.DOCUMENTATION,
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1, total_learnings=1),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "**Workflow element:** documentation" in output

    def test_format_frequency(self):
        """Test formatting frequency type."""
        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test",
            frequency=FrequencyType.REPEATED,
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1, total_learnings=1),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "**Frequency:** repeated" in output

    def test_format_with_project_path(self):
        """Test formatting with project path."""
        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            project_path="/home/user/projects/my-project",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1, total_learnings=1),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "(my-project)" in output

    def test_format_with_rules_warned(self):
        """Test formatting with rules that have warnings."""
        from drift.config.models import DriftConfig, DriftLearningType, PhaseDefinition

        config = DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            drift_learning_types={
                "test_type": DriftLearningType(
                    description="Test",
                    scope="conversation_level",
                    context="Test context",
                    requires_project_context=False,
                    phases=[PhaseDefinition(name="test", type="prompt", prompt="test", model="haiku")],
                )
            },
            agent_tools={},
        )

        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test_type",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=1,
                rules_checked=["rule1", "rule2"],
                rules_passed=["rule1"],
                rules_warned=["rule2"],
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        assert "Rules warned:" in output or "- Rules warned:" in output

    def test_format_with_rules_failed(self):
        """Test formatting with rules that have failures."""
        from drift.config.models import DriftConfig, DriftLearningType, PhaseDefinition

        config = DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            drift_learning_types={
                "test_type": DriftLearningType(
                    description="Test",
                    scope="project_level",
                    context="Test context",
                    requires_project_context=False,
                    phases=[PhaseDefinition(name="test", type="prompt", prompt="test", model="haiku")],
                )
            },
            agent_tools={},
        )

        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test_type",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=1,
                rules_checked=["rule1", "rule2"],
                rules_passed=["rule1"],
                rules_failed=["rule2"],
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        assert "Rules failed:" in output or "- Rules failed:" in output

    def test_format_with_rules_errored(self):
        """Test formatting with rules that errored."""
        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=0,
                rules_checked=["rule1", "rule2"],
                rules_passed=["rule1"],
                rules_errored=["rule2"],
                rule_errors={"rule2": "Some error message"},
            ),
            results=[],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "Rules errored:" in output or "- Rules errored:" in output

    def test_format_with_rules_passed_section(self):
        """Test formatting shows rules passed section."""
        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=0,
                rules_checked=["rule1", "rule2"],
                rules_passed=["rule1", "rule2"],
            ),
            results=[],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "## Rules Passed" in output
        assert "rule1" in output
        assert "rule2" in output

    def test_format_with_rules_errored_section(self):
        """Test formatting shows rules errored section."""
        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=0,
                rules_checked=["rule1", "rule2"],
                rules_passed=["rule1"],
                rules_errored=["rule2"],
                rule_errors={"rule2": "Test error"},
            ),
            results=[],
        )

        formatter = MarkdownFormatter()
        output = formatter.format(result)

        assert "## Rules Errored" in output
        assert "rule2" in output
        assert "Test error" in output

    def test_severity_fail_creates_failures_section(self):
        """Test that FAIL severity creates Failures section."""
        from drift.config.models import DriftConfig, DriftLearningType, SeverityLevel, PhaseDefinition

        config = DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            drift_learning_types={
                "test_fail": DriftLearningType(
                    description="Test",
                    scope="conversation_level",
                    context="Test context",
                    requires_project_context=False,
                    severity=SeverityLevel.FAIL,
                    phases=[PhaseDefinition(name="test", type="prompt", prompt="test", model="haiku")],
                )
            },
            agent_tools={},
        )

        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test_fail",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        assert "## Failures" in output
        assert "### test_fail" in output

    def test_severity_warning_creates_warnings_section(self):
        """Test that WARNING severity creates Warnings section."""
        from drift.config.models import DriftConfig, DriftLearningType, SeverityLevel, PhaseDefinition

        config = DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            drift_learning_types={
                "test_warn": DriftLearningType(
                    description="Test",
                    scope="conversation_level",
                    context="Test context",
                    requires_project_context=False,
                    severity=SeverityLevel.WARNING,
                    phases=[PhaseDefinition(name="test", type="prompt", prompt="test", model="haiku")],
                )
            },
            agent_tools={},
        )

        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="test_warn",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        assert "## Warnings" in output
        assert "### test_warn" in output

    def test_severity_defaults_by_scope(self):
        """Test that severity defaults based on scope."""
        from drift.config.models import DriftConfig, DriftLearningType, PhaseDefinition

        config = DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            drift_learning_types={
                "project_type": DriftLearningType(
                    description="Test",
                    scope="project_level",
                    context="Test context",
                    requires_project_context=False,
                    phases=[PhaseDefinition(name="test", type="prompt", prompt="test", model="haiku")],
                ),
                "conv_type": DriftLearningType(
                    description="Test",
                    scope="conversation_level",
                    context="Test context",
                    requires_project_context=False,
                    phases=[PhaseDefinition(name="test", type="prompt", prompt="test", model="haiku")],
                ),
            },
            agent_tools={},
        )

        learning1 = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action",
            expected_behavior="Intent",
            learning_type="project_type",
        )

        learning2 = Learning(
            turn_number=2,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action2",
            expected_behavior="Intent2",
            learning_type="conv_type",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning1, learning2],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=2,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=config)
        output = formatter.format(result)

        # project_level defaults to FAIL
        assert "## Failures" in output
        assert "### project_type" in output

        # conversation_level defaults to WARNING
        assert "## Warnings" in output
        assert "### conv_type" in output

    def test_get_severity_no_config(self):
        """Test _get_severity with no config defaults to WARNING."""
        from drift.config.models import SeverityLevel

        formatter = MarkdownFormatter(config=None)
        severity = formatter._get_severity("any_type")

        assert severity == SeverityLevel.WARNING

    def test_get_severity_unknown_type(self):
        """Test _get_severity with unknown type defaults to WARNING."""
        from drift.config.models import DriftConfig, SeverityLevel

        config = DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            drift_learning_types={},
            agent_tools={},
        )

        formatter = MarkdownFormatter(config=config)
        severity = formatter._get_severity("unknown_type")

        assert severity == SeverityLevel.WARNING


class TestJsonFormatter:
    """Tests for JsonFormatter."""

    def test_get_format_name(self):
        """Test getting format name."""
        formatter = JsonFormatter()
        assert formatter.get_format_name() == "json"

    def test_format_empty_results(self):
        """Test formatting empty analysis results."""
        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        # Parse JSON to verify it's valid
        data = json.loads(output)

        assert "metadata" in data
        assert "summary" in data
        assert "results" in data
        assert data["summary"]["conversations_analyzed"] == 0
        assert data["summary"]["conversations_with_drift"] == 0

    def test_format_with_metadata(self):
        """Test formatting with metadata."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "session_id": "test-123",
                "config_used": {"default_model": "haiku"},
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        data = json.loads(output)

        assert data["metadata"]["generated_at"] == "2024-01-01T10:00:00"
        assert data["metadata"]["session_id"] == "test-123"
        assert data["metadata"]["config_used"]["default_model"] == "haiku"

    def test_format_with_learnings(self, sample_learning):
        """Test formatting results with learnings."""
        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/conversation.jsonl",
            project_path="/path/to/project",
            learnings=[sample_learning],
            analysis_timestamp=datetime(2024, 1, 1, 10, 0, 0),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_learnings=1,
                conversations_with_drift=1,
                by_type={"incomplete_work": 1},
                by_agent={"claude-code": 1},
                by_frequency={"one-time": 1},
            ),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        data = json.loads(output)

        # Check summary
        assert data["summary"]["conversations_analyzed"] == 1
        assert data["summary"]["conversations_with_drift"] == 1
        assert data["summary"]["by_type"]["incomplete_work"] == 1
        assert data["summary"]["by_agent"]["claude-code"] == 1

        # Check results
        assert len(data["results"]) == 1
        conv_data = data["results"][0]
        assert conv_data["session_id"] == "session-123"
        assert conv_data["agent_tool"] == "claude-code"
        assert conv_data["project_path"] == "/path/to/project"

        # Check learnings
        assert len(conv_data["learnings"]) == 1
        learning_data = conv_data["learnings"][0]
        assert learning_data["turn_number"] == sample_learning.turn_number
        assert learning_data["observed_behavior"] == sample_learning.observed_behavior
        assert learning_data["expected_behavior"] == sample_learning.expected_behavior
        assert learning_data["learning_type"] == sample_learning.learning_type

    def test_format_multiple_conversations(self):
        """Test formatting multiple conversations."""
        learning1 = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path1",
            observed_behavior="Action 1",
            expected_behavior="Intent 1",
            learning_type="type1",
        )

        learning2 = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path2",
            observed_behavior="Action 2",
            expected_behavior="Intent 2",
            learning_type="type2",
        )

        result1 = AnalysisResult(
            session_id="session1",
            agent_tool="claude-code",
            conversation_file="/path1",
            learnings=[learning1],
            analysis_timestamp=datetime.now(),
        )

        result2 = AnalysisResult(
            session_id="session2",
            agent_tool="claude-code",
            conversation_file="/path2",
            learnings=[learning2],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=2, total_learnings=2),
            results=[result1, result2],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        data = json.loads(output)

        assert len(data["results"]) == 2
        assert data["results"][0]["session_id"] == "session1"
        assert data["results"][1]["session_id"] == "session2"

    def test_format_learning_details(self):
        """Test that all learning fields are included in JSON."""
        learning = Learning(
            turn_number=5,
            turn_uuid="turn-uuid-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="AI action",
            expected_behavior="User intent",
            learning_type="test_type",
            frequency=FrequencyType.REPEATED,
            workflow_element=WorkflowElement.SKILL,
            turns_to_resolve=3,
            turns_involved=[5, 6, 7],
            context="Test context",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1, total_learnings=1),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        data = json.loads(output)
        learning_data = data["results"][0]["learnings"][0]

        assert learning_data["turn_number"] == 5
        assert learning_data["turn_uuid"] == "turn-uuid-123"
        assert learning_data["frequency"] == "repeated"
        assert learning_data["workflow_element"] == "skill"
        assert learning_data["turns_to_resolve"] == 3
        assert learning_data["turns_involved"] == [5, 6, 7]
        assert learning_data["context"] == "Test context"

    def test_format_timestamp_serialization(self):
        """Test that timestamps are properly serialized."""
        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[],
            analysis_timestamp=datetime(2024, 1, 15, 14, 30, 0),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        data = json.loads(output)

        # Timestamp should be ISO format string
        assert data["results"][0]["analysis_timestamp"] == "2024-01-15T14:30:00"

    def test_format_with_specific_timestamp(self):
        """Test formatting with specific timestamp."""
        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[],
            analysis_timestamp=datetime(2024, 2, 1, 9, 0, 0),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        data = json.loads(output)

        # Timestamp should be in ISO format
        assert data["results"][0]["analysis_timestamp"] == "2024-02-01T09:00:00"

    def test_format_preserves_order(self):
        """Test that JSON output preserves insertion order."""
        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        # Check that keys appear in expected order
        lines = output.split("\n")
        metadata_idx = next(i for i, line in enumerate(lines) if "metadata" in line)
        summary_idx = next(i for i, line in enumerate(lines) if "summary" in line)
        results_idx = next(i for i, line in enumerate(lines) if "results" in line)

        assert metadata_idx < summary_idx < results_idx

    def test_format_unicode_handling(self):
        """Test that unicode characters are handled correctly."""
        learning = Learning(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path",
            observed_behavior="Action with émojis 🚀",
            expected_behavior="Intent with ñ and 中文",
            learning_type="test",
        )

        analysis_result = AnalysisResult(
            session_id="session",
            agent_tool="claude-code",
            conversation_file="/path",
            learnings=[learning],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(total_conversations=1, total_learnings=1),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)

        # Should not escape unicode
        assert "émojis" in output
        assert "🚀" in output
        assert "中文" in output

        # Should still be valid JSON
        data = json.loads(output)
        assert data["results"][0]["learnings"][0]["observed_behavior"] == "Action with émojis 🚀"
