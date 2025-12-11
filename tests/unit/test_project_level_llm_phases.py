"""Test that LLM-based prompt phases execute for project-level rules."""

import json
from unittest.mock import patch

import pytest

from drift.config.models import PhaseDefinition, RuleDefinition
from drift.core.analyzer import DriftAnalyzer
from tests.mock_provider import MockProvider


class TestProjectLevelLLMPhases:
    """Test LLM-based phases in project-level rules."""

    @pytest.fixture
    def project_with_claude_md(self, temp_dir):
        """Project with CLAUDE.md file containing junk content."""
        project = temp_dir / "test_project"
        project.mkdir()

        # Create CLAUDE.md with junk placeholder content
        claude_md = project / "CLAUDE.md"
        junk_content = """# Test Project

## Commands

```bash
# Line 1
# Line 2
# Line 3
# Line 4
# Line 5
# Line 6
# Line 7
# Line 8
# Line 9
# Line 10
# Line 11
# Line 12
# Line 13
# Line 14
# Line 15
# Line 16
# Line 17
# Line 18
# Line 19
# Line 20
# Line 21
```

## Tech Stack
Python 3.10+
"""
        claude_md.write_text(junk_content)

        return project

    @pytest.fixture
    def two_phase_rule(self, sample_drift_config):
        """Rule with 2 phases: 1 programmatic + 1 LLM."""
        rule = RuleDefinition(
            description="Two-phase validation",
            scope="project_level",
            context="Test two-phase execution",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=None,
            phases=[
                PhaseDefinition(
                    name="check_file_exists",
                    type="core:file_exists",
                    file_path="CLAUDE.md",
                    failure_message="CLAUDE.md missing",
                    expected_behavior="File should exist",
                ),
                PhaseDefinition(
                    name="check_content",
                    type="prompt",
                    prompt="Check if CLAUDE.md has junk content like 'Line 1, Line 2'.",
                    available_resources=[],
                ),
            ],
        )
        config = sample_drift_config
        config.rule_definitions["two_phase"] = rule
        return config

    @pytest.fixture
    def five_phase_rule(self, sample_drift_config):
        """Rule with 5 phases: mixed programmatic and LLM."""
        rule = RuleDefinition(
            description="Five-phase validation",
            scope="project_level",
            context="Test five-phase execution",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=None,
            phases=[
                PhaseDefinition(
                    name="phase1_file_check",
                    type="core:file_exists",
                    file_path="CLAUDE.md",
                    failure_message="File missing",
                    expected_behavior="File exists",
                ),
                PhaseDefinition(
                    name="phase2_llm_structure",
                    type="prompt",
                    prompt="Check if CLAUDE.md has proper structure (headers, sections).",
                    available_resources=[],
                ),
                PhaseDefinition(
                    name="phase3_llm_junk",
                    type="prompt",
                    prompt="Check if CLAUDE.md has junk/placeholder content.",
                    available_resources=[],
                ),
                PhaseDefinition(
                    name="phase4_line_count",
                    type="core:file_size",
                    params={"file_path": "CLAUDE.md", "max_count": 300},
                    failure_message="File too large",
                    expected_behavior="File under 300 lines",
                ),
                PhaseDefinition(
                    name="phase5_llm_final",
                    type="prompt",
                    prompt="Final review: does CLAUDE.md meet all quality standards?",
                    available_resources=[],
                ),
            ],
        )
        config = sample_drift_config
        config.rule_definitions["five_phase"] = rule
        return config

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_two_phase_all_phases_execute(self, two_phase_rule, project_with_claude_md):
        """Test that both phases execute: programmatic + LLM."""
        # Mock LLM to return no issues (pass)
        mock_provider = MockProvider()
        mock_provider.set_response(json.dumps([]))

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=two_phase_rule)
            analyzer.project_path = str(project_with_claude_md)

            result = analyzer.analyze_documents(rule_types=["two_phase"])

            # Verify LLM was called for phase 2
            assert (
                len(mock_provider.calls) == 1
            ), f"Expected 1 LLM call for phase 2 (prompt), got {len(mock_provider.calls)}"

            # Verify execution details includes both phases
            exec_details = result.metadata.get("execution_details", [])
            assert (
                len(exec_details) == 2
            ), f"Expected 2 execution details (one per phase), got {len(exec_details)}"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_five_phase_all_phases_execute(self, five_phase_rule, project_with_claude_md):
        """Test that all 5 phases execute: 2 programmatic + 3 LLM."""
        # Mock LLM to return no issues for all 3 LLM phases
        mock_provider = MockProvider()
        mock_provider.set_response(json.dumps([]))

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=five_phase_rule)
            analyzer.project_path = str(project_with_claude_md)

            result = analyzer.analyze_documents(rule_types=["five_phase"])

            # Verify LLM was called 3 times (phases 2, 3, 5)
            assert (
                len(mock_provider.calls) == 3
            ), f"Expected 3 LLM calls for phases 2, 3, 5 (prompts), got {len(mock_provider.calls)}"

            # Verify execution details includes all 5 phases
            exec_details = result.metadata.get("execution_details", [])
            assert (
                len(exec_details) == 5
            ), f"Expected 5 execution details (one per phase), got {len(exec_details)}"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_two_phase_first_phase_fails_stops_chain(self, two_phase_rule, temp_dir):
        """Test that when phase 1 fails, phase 2 doesn't execute."""
        # Create project WITHOUT CLAUDE.md (phase 1 will fail)
        project = temp_dir / "no_claude_md"
        project.mkdir()

        mock_provider = MockProvider()
        mock_provider.set_response(json.dumps([]))

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=two_phase_rule)
            analyzer.project_path = str(project)

            result = analyzer.analyze_documents(rule_types=["two_phase"])

            # Verify LLM was NOT called (chain stopped after phase 1 failure)
            assert len(mock_provider.calls) == 0, (
                f"Phase 1 failed, so phase 2 should not execute. "
                f"Expected 0 LLM calls, got {len(mock_provider.calls)}"
            )

            # Verify only phase 1 in execution details (phase 2 never ran)
            exec_details = result.metadata.get("execution_details", [])
            assert len(exec_details) == 1, (
                f"Expected 1 execution detail (phase 1 only, "
                f"phase 2 skipped), got {len(exec_details)}"
            )

            # Verify phase 1 status is failed
            assert exec_details[0]["status"] == "failed", "Phase 1 should have failed status"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_five_phase_third_phase_fails_stops_chain(
        self, five_phase_rule, project_with_claude_md
    ):
        """Test that when phase 3 (LLM) fails, phases 4 and 5 don't execute."""
        call_count = [0]

        def mock_generate_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                call_count[0] += 1
                original_generate(prompt, **kwargs)

                # Phase 2: pass (return no issues)
                if call_count[0] == 1:
                    return json.dumps([])

                # Phase 3: fail (return an issue)
                if call_count[0] == 2:
                    return json.dumps(
                        [
                            {
                                "observed_issue": "Found junk placeholder content",
                                "expected_quality": "Should have real content",
                                "context": "Line 1, Line 2, Line 3 detected",
                            }
                        ]
                    )

                # Should not reach phase 5
                return json.dumps([])

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=five_phase_rule)
            analyzer.project_path = str(project_with_claude_md)

            result = analyzer.analyze_documents(rule_types=["five_phase"])

            # Verify LLM was called exactly 2 times (phases 2 and 3)
            # Phase 5 should NOT execute because phase 3 failed
            assert call_count[0] == 2, (
                f"Expected 2 LLM calls (phases 2, 3), phase 5 should not execute. "
                f"Got {call_count[0]} calls"
            )

            # Verify execution details includes phases 1, 2, 3 only (not 4, 5)
            exec_details = result.metadata.get("execution_details", [])
            assert len(exec_details) == 3, (
                f"Expected 3 execution details (phases 1-3, "
                f"stopped at 3), got {len(exec_details)}"
            )

            # Verify phase 3 has failed status
            # Note: phase names might not be in execution details, check by position
            # The 3rd execution detail should be phase 3
            if len(exec_details) >= 3:
                assert exec_details[2]["status"] == "failed", "Phase 3 should have failed status"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_five_phase_all_pass_all_execute(self, five_phase_rule, project_with_claude_md):
        """Test that when all phases pass, all 5 execute."""
        mock_provider = MockProvider()
        # All LLM phases return no issues
        mock_provider.set_response(json.dumps([]))

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=five_phase_rule)
            analyzer.project_path = str(project_with_claude_md)

            result = analyzer.analyze_documents(rule_types=["five_phase"])

            # Verify all 3 LLM phases were called
            assert (
                len(mock_provider.calls) == 3
            ), f"Expected 3 LLM calls (phases 2, 3, 5), got {len(mock_provider.calls)}"

            # Verify all 5 phases in execution details
            exec_details = result.metadata.get("execution_details", [])
            assert len(exec_details) == 5, (
                f"Expected 5 execution details (all phases), " f"got {len(exec_details)}"
            )

            # Verify all passed
            for ed in exec_details:
                assert (
                    ed["status"] == "passed"
                ), f"All phases should pass, but got status: {ed['status']}"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_prompt_only_phases_execute(self, sample_drift_config, project_with_claude_md):
        """Test rule with ONLY prompt phases (no programmatic phases)."""
        prompt_only_rule = RuleDefinition(
            description="LLM-only validation",
            scope="project_level",
            context="Test prompt-only",
            requires_project_context=True,
            supported_clients=["claude-code"],
            document_bundle=None,
            phases=[
                PhaseDefinition(
                    name="llm_check_1",
                    type="prompt",
                    prompt="Check structure.",
                    available_resources=[],
                ),
                PhaseDefinition(
                    name="llm_check_2",
                    type="prompt",
                    prompt="Check content quality.",
                    available_resources=[],
                ),
            ],
        )

        config = sample_drift_config
        config.rule_definitions["prompt_only"] = prompt_only_rule

        mock_provider = MockProvider()
        mock_provider.set_response(json.dumps([]))

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=config)
            analyzer.project_path = str(project_with_claude_md)

            result = analyzer.analyze_documents(rule_types=["prompt_only"])

            # Verify both LLM calls executed
            assert (
                len(mock_provider.calls) == 2
            ), f"Expected 2 LLM calls for prompt-only rule, got {len(mock_provider.calls)}"

            exec_details = result.metadata.get("execution_details", [])
            assert (
                len(exec_details) == 2
            ), f"Expected 2 execution details for prompt-only rule, got {len(exec_details)}"
