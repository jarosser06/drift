"""Unit tests for rules tracking (passed/failed/checked)."""

from unittest.mock import MagicMock, patch

from drift.core.analyzer import DriftAnalyzer
from drift.core.types import AnalysisResult, Learning


class TestRulesTracking:
    """Tests for rules_checked, rules_passed, and rules_failed tracking."""

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_rules_tracking_all_passed(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
    ):
        """Test rules tracking when all rules pass (no learnings)."""
        # Setup mocks
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = "[]"  # No learnings
        mock_provider_class.return_value = mock_provider

        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        # Run analysis
        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Verify rules tracking
        assert len(result.summary.rules_checked) > 0
        assert len(result.summary.rules_passed) > 0
        assert len(result.summary.rules_failed) == 0
        # All checked rules should have passed
        assert set(result.summary.rules_passed) == set(result.summary.rules_checked)

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_rules_tracking_some_failed(
        self,
        mock_provider_class,
        mock_loader_class,
        sample_drift_config,
        sample_conversation,
        sample_learning,
    ):
        """Test rules tracking when some rules fail (have learnings)."""
        # Add another rule to the config so we have multiple rules
        from drift.config.models import DriftLearningType, PhaseDefinition

        sample_drift_config.drift_learning_types["test_rule"] = DriftLearningType(
            description="Test rule",
            scope="conversation_level",
            context="Test",
            requires_project_context=False,
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Test",
                )
            ],
        )

        # Setup mocks
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        # Return learning for incomplete_work only, not for test_rule
        mock_provider.generate.side_effect = [
            '[{"turn_number": 1, "observed_behavior": "test", '
            '"expected_behavior": "test", "context": "test"}]',
            "[]",  # test_rule returns no learnings
        ]
        mock_provider_class.return_value = mock_provider

        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = [sample_conversation]
        mock_loader_class.return_value = mock_loader

        # Run analysis
        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # Verify rules tracking
        assert len(result.summary.rules_checked) == 2  # incomplete_work and test_rule
        # incomplete_work is conversation_level, so it's warned not failed
        assert len(result.summary.rules_warned) == 1  # incomplete_work
        assert len(result.summary.rules_failed) == 0  # none have project_level scope
        assert len(result.summary.rules_passed) == 1  # test_rule
        # Sum of passed, warned, and failed should equal checked
        assert len(result.summary.rules_passed) + len(result.summary.rules_warned) + len(
            result.summary.rules_failed
        ) == len(result.summary.rules_checked)
        # Warned rules should be in checked rules
        assert all(rule in result.summary.rules_checked for rule in result.summary.rules_warned)
        # Passed rules should be in checked rules
        assert all(rule in result.summary.rules_checked for rule in result.summary.rules_passed)

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    def test_rules_tracking_no_conversations(
        self,
        mock_loader_class,
        sample_drift_config,
    ):
        """Test rules tracking when no conversations are available."""
        # Setup mock with no conversations
        mock_loader = MagicMock()
        mock_loader.load_conversations.return_value = []
        mock_loader_class.return_value = mock_loader

        # Run analysis
        analyzer = DriftAnalyzer(config=sample_drift_config)
        result = analyzer.analyze()

        # When no conversations, no rules should be tracked
        # (because we exit early with empty result)
        assert result.summary.rules_checked == []
        assert result.summary.rules_passed == []
        assert result.summary.rules_failed == []

    def test_generate_summary_tracks_rules(self, sample_learning, sample_drift_config, tmp_path):
        """Test _generate_summary correctly tracks rules."""
        from drift.config.models import DriftLearningType, PhaseDefinition

        # Create mock learning types
        types_checked = {
            "rule1": DriftLearningType(
                description="Test",
                scope="conversation_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="detection",
                        type="prompt",
                        prompt="Test",
                    )
                ],
            ),
            "rule2": DriftLearningType(
                description="Test",
                scope="conversation_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="detection",
                        type="prompt",
                        prompt="Test",
                    )
                ],
            ),
            "rule3": DriftLearningType(
                description="Test",
                scope="conversation_level",
                context="Test",
                requires_project_context=False,
                phases=[
                    PhaseDefinition(
                        name="detection",
                        type="prompt",
                        prompt="Test",
                    )
                ],
            ),
        }

        # Create results with learning from rule1 only
        learning_rule1 = Learning(
            turn_number=1,
            turn_uuid=None,
            agent_tool="claude-code",
            conversation_file="/test",
            observed_behavior="test",
            expected_behavior="test",
            learning_type="rule1",
            context="test",
            resources_consulted=[],
            phases_count=1,
        )

        results = [
            AnalysisResult(
                session_id="test",
                agent_tool="claude-code",
                conversation_file="/test",
                learnings=[learning_rule1],
            )
        ]

        # Generate summary
        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=tmp_path)
        summary = analyzer._generate_summary(results, types_checked)

        # Verify tracking
        assert set(summary.rules_checked) == {"rule1", "rule2", "rule3"}
        # rule1 has conversation_level scope, so it's a warning not a failure
        assert summary.rules_warned == ["rule1"]
        assert summary.rules_failed == []
        assert set(summary.rules_passed) == {"rule2", "rule3"}  # Others passed

    def test_generate_summary_without_types(self, sample_drift_config, tmp_path):
        """Test _generate_summary when types_checked is None."""
        results = [
            AnalysisResult(
                session_id="test",
                agent_tool="claude-code",
                conversation_file="/test",
                learnings=[],
            )
        ]

        # Generate summary without types
        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=tmp_path)
        summary = analyzer._generate_summary(results, None)

        # Should not track rules
        assert summary.rules_checked == []
        assert summary.rules_passed == []
        assert summary.rules_failed == []
