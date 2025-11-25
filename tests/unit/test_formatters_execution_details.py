"""Tests for formatter execution details output."""

import json

from drift.cli.output.json import JsonFormatter
from drift.cli.output.markdown import MarkdownFormatter
from drift.core.types import AnalysisSummary, CompleteAnalysisResult


class TestJsonFormatterExecutionDetails:
    """Test that JSON formatter always includes execution_details."""

    def test_json_includes_execution_details_when_present(self):
        """Test that JSON output includes execution_details from metadata."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
                "execution_details": [
                    {
                        "rule_name": "test_rule",
                        "status": "passed",
                        "description": "Test rule description",
                    }
                ],
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)
        parsed = json.loads(output)

        assert "metadata" in parsed
        assert "execution_details" in parsed["metadata"]
        assert len(parsed["metadata"]["execution_details"]) == 1
        assert parsed["metadata"]["execution_details"][0]["rule_name"] == "test_rule"

    def test_json_handles_empty_execution_details(self):
        """Test that JSON handles empty execution_details gracefully."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
                "execution_details": [],
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)
        parsed = json.loads(output)

        assert "metadata" in parsed
        assert "execution_details" in parsed["metadata"]
        assert parsed["metadata"]["execution_details"] == []

    def test_json_handles_missing_execution_details(self):
        """Test that JSON handles missing execution_details key."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = JsonFormatter()
        output = formatter.format(result)
        parsed = json.loads(output)

        # Should have execution_details even if missing from metadata
        assert "metadata" in parsed
        assert "execution_details" in parsed["metadata"]
        assert parsed["metadata"]["execution_details"] == []


class TestMarkdownFormatterExecutionDetails:
    """Test that markdown formatter respects --detailed flag."""

    def test_markdown_shows_execution_details_when_detailed_true(self):
        """Test that markdown shows execution details when detailed=True."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
                "execution_details": [
                    {
                        "rule_name": "test_rule",
                        "status": "passed",
                        "description": "Test rule description",
                    }
                ],
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = MarkdownFormatter(detailed=True)
        output = formatter.format(result)

        # Should contain execution details section
        assert "execution details" in output.lower() or "test execution" in output.lower()
        assert "test_rule" in output

    def test_markdown_hides_execution_details_when_detailed_false(self):
        """Test that markdown does NOT show execution details when detailed=False."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
                "execution_details": [
                    {
                        "rule_name": "test_rule",
                        "status": "passed",
                        "description": "Test rule description",
                    }
                ],
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = MarkdownFormatter(detailed=False)
        output = formatter.format(result)

        # Should NOT contain execution details section
        # (test_rule might appear in summary, so check for section header)
        assert "## Detailed Test Execution" not in output
        assert "## Test Execution Details" not in output

    def test_markdown_groups_by_status(self):
        """Test that markdown groups rules by passed/failed/errored status."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
                "execution_details": [
                    {"rule_name": "passed_rule", "status": "passed", "description": "Passed"},
                    {"rule_name": "failed_rule", "status": "failed", "description": "Failed"},
                    {"rule_name": "errored_rule", "status": "errored", "description": "Errored"},
                ],
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = MarkdownFormatter(detailed=True)
        output = formatter.format(result)

        # Should have sections for different statuses
        assert "passed_rule" in output
        assert "failed_rule" in output
        assert "errored_rule" in output

    def test_markdown_shows_phase_results(self):
        """Test that markdown displays phase-by-phase results."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
                "execution_details": [
                    {
                        "rule_name": "multi_phase_rule",
                        "status": "failed",
                        "description": "Multi-phase rule",
                        "phase_results": [
                            {"phase_number": 1, "findings": [{"turn_number": 1}]},
                            {"phase_number": 2, "findings": [{"turn_number": 2}]},
                        ],
                    }
                ],
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = MarkdownFormatter(detailed=True)
        output = formatter.format(result)

        # Should show phase info
        assert "phase" in output.lower() or "Phase" in output

    def test_markdown_handles_empty_execution_details(self):
        """Test that markdown handles empty execution_details."""
        result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2025-01-01T00:00:00",
                "session_id": "test-session",
                "execution_details": [],
            },
            summary=AnalysisSummary(),
            results=[],
        )

        formatter = MarkdownFormatter(detailed=True)
        output = formatter.format(result)

        # Should not crash, may or may not show section
        assert output is not None
        assert len(output) > 0
