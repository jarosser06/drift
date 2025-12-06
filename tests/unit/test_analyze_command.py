"""Unit tests for analyze command functions."""

from drift.cli.commands.analyze import _merge_results
from drift.core.types import AnalysisSummary, CompleteAnalysisResult


class TestMergeResults:
    """Tests for the _merge_results function."""

    def test_merge_empty_results(self):
        """Test merging two empty results."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert merged.summary.total_conversations == 0
        assert merged.summary.total_rule_violations == 0
        assert merged.results == []
        assert merged.metadata["analysis_scopes"] == ["conversations", "documents"]

    def test_merge_with_learnings(self):
        """Test merging results with rules."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
                by_type={"incomplete_work": 2},
                by_group={"Workflow": 2},
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=1,
                by_type={"claude_md_missing": 1},
                by_group={"Documentation": 1},
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert merged.summary.total_rule_violations == 3
        assert merged.summary.by_type["incomplete_work"] == 2
        assert merged.summary.by_type["claude_md_missing"] == 1
        assert merged.summary.by_group["Workflow"] == 2
        assert merged.summary.by_group["Documentation"] == 1

    def test_merge_by_type_with_overlapping_types(self):
        """Test merging when both results have the same learning type."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=2,
                by_type={"incomplete_work": 2},
                by_group={"Workflow": 2},
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=3,
                by_type={"incomplete_work": 3},
                by_group={"Workflow": 3},
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert merged.summary.total_rule_violations == 5
        assert merged.summary.by_type["incomplete_work"] == 5
        assert merged.summary.by_group["Workflow"] == 5

    def test_merge_document_learnings_metadata(self):
        """Test that document_rules metadata is preserved."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "document_rules": [{"type": "claude_md_missing", "count": 1}],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=1,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert "document_rules" in merged.metadata
        assert merged.metadata["document_rules"] == [{"type": "claude_md_missing", "count": 1}]

    def test_merge_skipped_rules_both_empty(self):
        """Test merging when neither result has skipped rules."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert "skipped_rules" not in merged.metadata

    def test_merge_skipped_rules_only_conv(self):
        """Test merging when only conversation result has skipped rules."""
        conv_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "skipped_rules": ["rule1", "rule2"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert "skipped_rules" in merged.metadata
        assert set(merged.metadata["skipped_rules"]) == {"rule1", "rule2"}

    def test_merge_skipped_rules_only_doc(self):
        """Test merging when only document result has skipped rules."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "skipped_rules": ["rule3", "rule4"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert "skipped_rules" in merged.metadata
        assert set(merged.metadata["skipped_rules"]) == {"rule3", "rule4"}

    def test_merge_skipped_rules_both_have(self):
        """Test merging when both results have skipped rules."""
        conv_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "skipped_rules": ["rule1", "rule2"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "skipped_rules": ["rule3", "rule4"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert "skipped_rules" in merged.metadata
        assert set(merged.metadata["skipped_rules"]) == {"rule1", "rule2", "rule3", "rule4"}

    def test_merge_skipped_rules_with_duplicates(self):
        """Test merging when both results have overlapping skipped rules."""
        conv_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "skipped_rules": ["rule1", "rule2"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "skipped_rules": ["rule2", "rule3"],
            },
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert "skipped_rules" in merged.metadata
        # Should deduplicate rule2
        assert set(merged.metadata["skipped_rules"]) == {"rule1", "rule2", "rule3"}

    def test_merge_rules_checked_both_empty(self):
        """Test merging when neither result has rules_checked."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=[],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=[],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert merged.summary.rules_checked == []

    def test_merge_rules_checked_only_conv(self):
        """Test merging when only conversation result has rules_checked."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=["rule1", "rule2"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=[],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        # Should preserve conv rules_checked when doc is empty
        assert set(merged.summary.rules_checked) == {"rule1", "rule2"}

    def test_merge_rules_checked_only_doc(self):
        """Test merging when only document result has rules_checked."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=[],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=["rule3", "rule4"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        # Should use doc rules_checked when conv is empty
        assert set(merged.summary.rules_checked) == {"rule3", "rule4"}

    def test_merge_rules_checked_both_have(self):
        """Test merging when both results have rules_checked."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=["rule1", "rule2"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=["rule3", "rule4"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert set(merged.summary.rules_checked) == {"rule1", "rule2", "rule3", "rule4"}

    def test_merge_rules_checked_with_duplicates(self):
        """Test merging when both results have overlapping rules_checked."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=["rule1", "rule2"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_checked=["rule2", "rule3"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        # Should deduplicate rule2
        assert set(merged.summary.rules_checked) == {"rule1", "rule2", "rule3"}

    def test_merge_rules_passed(self):
        """Test merging rules_passed from both results."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_passed=["rule1", "rule2"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_passed=["rule3", "rule4"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert set(merged.summary.rules_passed) == {"rule1", "rule2", "rule3", "rule4"}

    def test_merge_rules_warned(self):
        """Test merging rules_warned from both results."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_warned=["rule1"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_warned=["rule2"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert set(merged.summary.rules_warned) == {"rule1", "rule2"}

    def test_merge_rules_failed(self):
        """Test merging rules_failed from both results."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_failed=["rule1"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_failed=["rule2"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert set(merged.summary.rules_failed) == {"rule1", "rule2"}

    def test_merge_rules_errored(self):
        """Test merging rules_errored from both results."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_errored=["rule1"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                rules_errored=["rule2"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert set(merged.summary.rules_errored) == {"rule1", "rule2"}

    def test_merge_all_rule_stats_together(self):
        """Test merging all rule statistics at once."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=1,
                rules_checked=["rule1", "rule2", "rule3"],
                rules_passed=["rule1"],
                rules_warned=["rule2"],
                rules_failed=["rule3"],
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=1,
                rules_checked=["rule4", "rule5"],
                rules_passed=["rule4"],
                rules_errored=["rule5"],
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        assert set(merged.summary.rules_checked) == {"rule1", "rule2", "rule3", "rule4", "rule5"}
        assert set(merged.summary.rules_passed) == {"rule1", "rule4"}
        assert set(merged.summary.rules_warned) == {"rule2"}
        assert set(merged.summary.rules_failed) == {"rule3"}
        assert set(merged.summary.rules_errored) == {"rule5"}

    def test_merge_preserves_conv_metadata(self):
        """Test that conversation metadata is preserved in merged result."""
        conv_result = CompleteAnalysisResult(
            metadata={
                "generated_at": "2024-01-01T10:00:00",
                "custom_field": "custom_value",
                "agent_tool": "claude-code",
            },
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00"},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        # Should preserve conv metadata fields
        assert merged.metadata["custom_field"] == "custom_value"
        assert merged.metadata["agent_tool"] == "claude-code"
        assert merged.metadata["generated_at"] == "2024-01-01T10:00:00"

    def test_merge_check_counts(self):
        """Test that check counts are properly merged from both results."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00", "execution_details": []},
            summary=AnalysisSummary(
                total_conversations=2,
                total_rule_violations=1,
                total_checks=5,
                checks_passed=3,
                checks_failed=1,
                checks_warned=1,
                checks_errored=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00", "execution_details": []},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                total_checks=3,
                checks_passed=2,
                checks_failed=0,
                checks_warned=1,
                checks_errored=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        # Check counts should be summed
        assert merged.summary.total_checks == 8  # 5 + 3
        assert merged.summary.checks_passed == 5  # 3 + 2
        assert merged.summary.checks_failed == 1  # 1 + 0
        assert merged.summary.checks_warned == 2  # 1 + 1
        assert merged.summary.checks_errored == 0  # 0 + 0

    def test_merge_check_counts_with_zeros(self):
        """Test merging check counts when one result has no checks."""
        conv_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00", "execution_details": []},
            summary=AnalysisSummary(
                total_conversations=1,
                total_rule_violations=0,
                total_checks=0,
                checks_passed=0,
                checks_failed=0,
                checks_warned=0,
                checks_errored=0,
            ),
            results=[],
        )
        doc_result = CompleteAnalysisResult(
            metadata={"generated_at": "2024-01-01T10:00:00", "execution_details": []},
            summary=AnalysisSummary(
                total_conversations=0,
                total_rule_violations=0,
                total_checks=2,
                checks_passed=2,
                checks_failed=0,
                checks_warned=0,
                checks_errored=0,
            ),
            results=[],
        )

        merged = _merge_results(conv_result, doc_result)

        # Should properly handle zero values
        assert merged.summary.total_checks == 2
        assert merged.summary.checks_passed == 2
        assert merged.summary.checks_failed == 0
        assert merged.summary.checks_warned == 0
        assert merged.summary.checks_errored == 0
