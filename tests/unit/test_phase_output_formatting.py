"""Tests for phase information in rule failure output (Issue #53)."""

from datetime import datetime

import pytest

from drift.cli.output.json import JsonFormatter
from drift.cli.output.markdown import MarkdownFormatter
from drift.config.models import DriftConfig, PhaseDefinition, RuleDefinition
from drift.core.types import AnalysisResult, AnalysisSummary, CompleteAnalysisResult, Rule


class TestPhaseInformationOutput:
    """Test phase information appears in rule failure output."""

    @pytest.fixture
    def single_phase_rule_config(self):
        """Config with single-phase rule."""
        return DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            rule_definitions={
                "single_phase_rule": RuleDefinition(
                    description="Single phase test",
                    scope="project_level",
                    context="Testing single phase output",
                    requires_project_context=False,
                    phases=[
                        PhaseDefinition(
                            name="detection",
                            type="prompt",
                            prompt="Detect issues",
                            model="haiku",
                        )
                    ],
                )
            },
            agent_tools={},
        )

    @pytest.fixture
    def multi_phase_rule_config(self):
        """Config with multi-phase rule."""
        return DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            rule_definitions={
                "multi_phase_rule": RuleDefinition(
                    description="Multi phase test",
                    scope="project_level",
                    context="Testing multi-phase output",
                    requires_project_context=False,
                    phases=[
                        PhaseDefinition(
                            name="detection",
                            type="prompt",
                            prompt="Detect issues",
                            model="haiku",
                        ),
                        PhaseDefinition(
                            name="analysis",
                            type="prompt",
                            prompt="Analyze issues",
                            model="haiku",
                        ),
                        PhaseDefinition(
                            name="validation",
                            type="prompt",
                            prompt="Validate findings",
                            model="haiku",
                        ),
                    ],
                )
            },
            agent_tools={},
        )

    def test_single_phase_rule_no_phase_field_markdown(self, single_phase_rule_config):
        """Test that single-phase rules don't show phase information in markdown."""
        rule = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue detected",
            expected_behavior="Should be correct",
            rule_type="single_phase_rule",
            phase_name=None,  # Single-phase rules should not have phase_name
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=single_phase_rule_config)
        output = formatter.format(result)

        # Phase field should NOT appear for single-phase rules
        assert "**Phase:**" not in output
        # But other fields should still be present
        assert "**Session:**" in output
        assert "**Observed:**" in output
        assert "**Expected:**" in output

    def test_multi_phase_rule_shows_phase_markdown(self, multi_phase_rule_config):
        """Test that multi-phase rules show phase information in markdown."""
        rule = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue detected in analysis phase",
            expected_behavior="Should pass analysis",
            rule_type="multi_phase_rule",
            phase_name="analysis",  # Multi-phase rule with phase name
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=multi_phase_rule_config)
        output = formatter.format(result)

        # Phase field SHOULD appear for multi-phase rules
        assert "**Phase:** analysis" in output
        # And other fields should still be present
        assert "**Session:**" in output
        assert "**Observed:**" in output
        assert "**Expected:**" in output

    def test_multi_phase_different_phases_markdown(self, multi_phase_rule_config):
        """Test multiple failures from different phases in markdown."""
        rule1 = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue in detection",
            expected_behavior="Should pass detection",
            rule_type="multi_phase_rule",
            phase_name="detection",
        )

        rule2 = Rule(
            turn_number=2,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue in validation",
            expected_behavior="Should pass validation",
            rule_type="multi_phase_rule",
            phase_name="validation",
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule1, rule2],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=multi_phase_rule_config)
        output = formatter.format(result)

        # Both phase names should appear
        assert "**Phase:** detection" in output
        assert "**Phase:** validation" in output
        # Verify they're associated with correct behaviors
        lines = output.split("\n")
        for i, line in enumerate(lines):
            if "**Phase:** detection" in line:
                # Look ahead for the observed behavior
                subsequent_lines = "\n".join(lines[i : i + 5])
                assert "Issue in detection" in subsequent_lines
            if "**Phase:** validation" in line:
                subsequent_lines = "\n".join(lines[i : i + 5])
                assert "Issue in validation" in subsequent_lines

    def test_phase_appears_before_session_markdown(self, multi_phase_rule_config):
        """Test that phase appears before session info in markdown output."""
        rule = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue detected",
            expected_behavior="Should be correct",
            rule_type="multi_phase_rule",
            phase_name="analysis",
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=multi_phase_rule_config)
        output = formatter.format(result)

        # Find positions of phase and session in output
        phase_pos = output.find("**Phase:** analysis")
        session_pos = output.find("**Session:**")

        # Phase should come before session
        assert phase_pos < session_pos
        assert phase_pos > 0
        assert session_pos > 0

    def test_single_phase_rule_no_phase_field_json(self, single_phase_rule_config):
        """Test that single-phase rules don't show phase information in JSON."""
        import json

        rule = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue detected",
            expected_behavior="Should be correct",
            rule_type="single_phase_rule",
            phase_name=None,
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)
        data = json.loads(output)

        rule_data = data["results"][0]["rules"][0]

        # Phase field should NOT be present for single-phase rules
        assert "phase_name" not in rule_data
        # But other fields should still be present
        assert "observed_behavior" in rule_data
        assert "expected_behavior" in rule_data

    def test_multi_phase_rule_shows_phase_json(self, multi_phase_rule_config):
        """Test that multi-phase rules show phase information in JSON."""
        import json

        rule = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue detected in analysis phase",
            expected_behavior="Should pass analysis",
            rule_type="multi_phase_rule",
            phase_name="analysis",
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)
        data = json.loads(output)

        rule_data = data["results"][0]["rules"][0]

        # Phase field SHOULD be present for multi-phase rules
        assert "phase_name" in rule_data
        assert rule_data["phase_name"] == "analysis"
        # And other fields should still be present
        assert rule_data["observed_behavior"] == "Issue detected in analysis phase"
        assert rule_data["expected_behavior"] == "Should pass analysis"

    def test_multi_phase_different_phases_json(self, multi_phase_rule_config):
        """Test multiple failures from different phases in JSON."""
        import json

        rule1 = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue in detection",
            expected_behavior="Should pass detection",
            rule_type="multi_phase_rule",
            phase_name="detection",
        )

        rule2 = Rule(
            turn_number=2,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue in validation",
            expected_behavior="Should pass validation",
            rule_type="multi_phase_rule",
            phase_name="validation",
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule1, rule2],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
            ),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)
        data = json.loads(output)

        rules_data = data["results"][0]["rules"]

        # Should have both rules with their phase names
        assert len(rules_data) == 2
        assert rules_data[0]["phase_name"] == "detection"
        assert rules_data[0]["observed_behavior"] == "Issue in detection"
        assert rules_data[1]["phase_name"] == "validation"
        assert rules_data[1]["observed_behavior"] == "Issue in validation"

    def test_document_rule_with_phase_markdown(self, multi_phase_rule_config):
        """Test document rules with phase information in markdown."""
        rule = Rule(
            turn_number=0,
            agent_tool="documents",
            conversation_file="N/A",
            observed_behavior="Documentation issue detected",
            expected_behavior="Should have proper docs",
            rule_type="multi_phase_rule",
            source_type="document",
            affected_files=[".claude/skills/testing/SKILL.md"],
            bundle_id="testing_skill",
            phase_name="validation",
        )

        analysis_result = AnalysisResult(
            session_id="document_analysis",
            agent_tool="documents",
            conversation_file="N/A",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=multi_phase_rule_config)
        output = formatter.format(result)

        # Phase should appear for document rules too
        assert "**Phase:** validation" in output
        # And document-specific fields
        assert "**File:** .claude/skills/testing/SKILL.md" in output
        assert "**Source:** document_analysis" in output

    def test_document_rule_with_phase_json(self, multi_phase_rule_config):
        """Test document rules with phase information in JSON."""
        import json

        rule = Rule(
            turn_number=0,
            agent_tool="documents",
            conversation_file="N/A",
            observed_behavior="Documentation issue detected",
            expected_behavior="Should have proper docs",
            rule_type="multi_phase_rule",
            source_type="document",
            affected_files=[".claude/skills/testing/SKILL.md"],
            bundle_id="testing_skill",
            phase_name="validation",
        )

        analysis_result = AnalysisResult(
            session_id="document_analysis",
            agent_tool="documents",
            conversation_file="N/A",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)
        data = json.loads(output)

        rule_data = data["results"][0]["rules"][0]

        # Phase should be present for document rules too
        assert rule_data["phase_name"] == "validation"
        # And document-specific fields
        assert rule_data["affected_files"] == [".claude/skills/testing/SKILL.md"]
        assert rule_data["bundle_id"] == "testing_skill"

    def test_phase_name_matches_config_definition(self, multi_phase_rule_config):
        """Test that phase names match the phase definitions in config."""
        # Use all three phase names from the config
        phase_names = ["detection", "analysis", "validation"]

        rules = [
            Rule(
                turn_number=i + 1,
                agent_tool="claude-code",
                conversation_file="/path/to/file",
                observed_behavior=f"Issue in {phase}",
                expected_behavior=f"Should pass {phase}",
                rule_type="multi_phase_rule",
                phase_name=phase,
            )
            for i, phase in enumerate(phase_names)
        ]

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=rules,
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=len(rules),
            ),
            results=[analysis_result],
        )

        # Test markdown output
        formatter_md = MarkdownFormatter(config=multi_phase_rule_config)
        output_md = formatter_md.format(result)

        for phase in phase_names:
            assert f"**Phase:** {phase}" in output_md

        # Test JSON output
        import json

        formatter_json = JsonFormatter()
        output_json = formatter_json.format(result)
        data = json.loads(output_json)

        rules_data = data["results"][0]["rules"]
        for i, phase in enumerate(phase_names):
            assert rules_data[i]["phase_name"] == phase

    def test_mixed_single_and_multi_phase_rules(
        self, single_phase_rule_config, multi_phase_rule_config
    ):
        """Test output when both single and multi-phase rules are present."""
        # Create a combined config
        combined_config = DriftConfig(
            providers={},
            models={},
            default_model="haiku",
            rule_definitions={
                **single_phase_rule_config.rule_definitions,
                **multi_phase_rule_config.rule_definitions,
            },
            agent_tools={},
        )

        rule1 = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Single phase issue",
            expected_behavior="Should be correct",
            rule_type="single_phase_rule",
            phase_name=None,
        )

        rule2 = Rule(
            turn_number=2,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Multi phase issue",
            expected_behavior="Should be correct",
            rule_type="multi_phase_rule",
            phase_name="analysis",
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule1, rule2],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
            ),
            results=[analysis_result],
        )

        # Test markdown
        formatter_md = MarkdownFormatter(config=combined_config)
        output_md = formatter_md.format(result)

        # Single phase rule should not show phase
        lines = output_md.split("\n")
        single_phase_section_start = None
        multi_phase_section_start = None

        for i, line in enumerate(lines):
            if "#### single_phase_rule" in line:
                single_phase_section_start = i
            if "#### multi_phase_rule" in line:
                multi_phase_section_start = i

        # Check single phase section doesn't have phase
        if single_phase_section_start:
            single_section = "\n".join(
                lines[single_phase_section_start : single_phase_section_start + 10]
            )
            assert "**Phase:**" not in single_section
            assert "Single phase issue" in single_section

        # Check multi phase section has phase
        if multi_phase_section_start:
            multi_section = "\n".join(
                lines[multi_phase_section_start : multi_phase_section_start + 10]
            )
            assert "**Phase:** analysis" in multi_section
            assert "Multi phase issue" in multi_section

    def test_output_format_consistency_with_phase(self, multi_phase_rule_config):
        """Test that output format remains consistent when phase is present."""
        rule = Rule(
            turn_number=5,
            turn_uuid="turn-uuid-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Complex issue detected",
            expected_behavior="Should be handled correctly",
            rule_type="multi_phase_rule",
            phase_name="validation",
            context="Additional context about the issue",
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/project",
            project_path="/path/to/project",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        formatter = MarkdownFormatter(config=multi_phase_rule_config)
        output = formatter.format(result)

        # Verify all expected fields are present in correct order
        lines = output.split("\n")
        field_positions = {}

        for i, line in enumerate(lines):
            if "**Phase:**" in line:
                field_positions["Phase"] = i
            if "**Session:**" in line:
                field_positions["Session"] = i
            if "**Agent Tool:**" in line:
                field_positions["Agent Tool"] = i
            if "**Turn:**" in line:
                field_positions["Turn"] = i
            if "**Observed:**" in line:
                field_positions["Observed"] = i
            if "**Expected:**" in line:
                field_positions["Expected"] = i
            if "**Context:**" in line:
                field_positions["Context"] = i

        # Verify order: Phase → Session → Agent Tool → Turn → Observed → Expected → Context
        assert field_positions["Phase"] < field_positions["Session"]
        assert field_positions["Session"] < field_positions["Agent Tool"]
        assert field_positions["Agent Tool"] < field_positions["Turn"]
        assert field_positions["Turn"] < field_positions["Observed"]
        assert field_positions["Observed"] < field_positions["Expected"]
        assert field_positions["Expected"] < field_positions["Context"]

    def test_empty_phase_name_treated_as_single_phase(self, multi_phase_rule_config):
        """Test that empty string phase_name is treated like None (no phase shown)."""
        rule = Rule(
            turn_number=1,
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            observed_behavior="Issue detected",
            expected_behavior="Should be correct",
            rule_type="multi_phase_rule",
            phase_name="",  # Empty string should be treated like None
        )

        analysis_result = AnalysisResult(
            session_id="session-123",
            agent_tool="claude-code",
            conversation_file="/path/to/file",
            rules=[rule],
            analysis_timestamp=datetime.now(),
        )

        result = CompleteAnalysisResult(
            metadata={},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
            ),
            results=[analysis_result],
        )

        # Markdown should not show phase for empty string
        formatter_md = MarkdownFormatter(config=multi_phase_rule_config)
        output_md = formatter_md.format(result)
        assert "**Phase:**" not in output_md

        # JSON should not include phase_name for empty string
        import json

        formatter_json = JsonFormatter()
        output_json = formatter_json.format(result)
        data = json.loads(output_json)
        rule_data = data["results"][0]["rules"][0]
        # Empty string is falsy, so it won't be added
        assert "phase_name" not in rule_data
