"""Tests for prompt generation in multi-phase analysis."""

import pytest

from drift.config.models import DriftConfig, PhaseDefinition, RuleDefinition
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import Conversation, ResourceRequest, ResourceResponse, Turn


class TestPromptGeneration:
    """Tests for multi-phase analysis prompt generation."""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer with minimal config."""
        config = DriftConfig()
        return DriftAnalyzer(config=config, project_path=tmp_path)

    @pytest.fixture
    def sample_conversation(self, tmp_path):
        """Create a sample conversation with turns."""
        return Conversation(
            session_id="test-123",
            agent_tool="claude-code",
            file_path=str(tmp_path / "test.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(
                    number=1,
                    user_message="Run the /test command",
                    ai_message="Running tests now...",
                ),
                Turn(
                    number=2,
                    user_message="What were the results?",
                    ai_message="All tests passed!",
                ),
            ],
        )

    @pytest.fixture
    def command_activation_rule(self):
        """Create command_activation_required rule."""
        return RuleDefinition(
            description="AI failed to activate required skills",
            scope="conversation_level",
            context="Commands require skill activation first",
            requires_project_context=True,
            supported_clients=["claude-code"],
            phases=[
                PhaseDefinition(
                    name="initial_analysis",
                    type="prompt",
                    model="haiku",
                    prompt="Analyze conversation for slash commands",
                    available_resources=["command", "skill"],
                ),
                PhaseDefinition(
                    name="verify_dependencies",
                    type="prompt",
                    model="haiku",
                    prompt="Check if command has Required skills",
                    available_resources=["command", "skill"],
                ),
            ],
        )

    def test_phase_1_prompt_includes_conversation(
        self, analyzer, sample_conversation, command_activation_rule
    ):
        """Test that phase 1 prompt includes the full conversation."""
        phase_def = command_activation_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must include the conversation turns
        assert "Run the /test command" in prompt
        assert "Running tests now..." in prompt
        assert "What were the results?" in prompt
        assert "All tests passed!" in prompt

        # Must include analysis instructions
        assert "Analyze conversation for slash commands" in prompt

        # Must include context
        assert "Commands require skill activation first" in prompt

        # Must NOT ask for conversation turns (already provided)
        assert "request" not in prompt.lower() or (
            "requesting all conversation turns" not in prompt.lower()
        )

    def test_phase_1_prompt_structure(self, analyzer, sample_conversation, command_activation_rule):
        """Test that phase 1 prompt has correct structure."""
        phase_def = command_activation_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must have clear sections
        assert "command_activation_required" in prompt
        assert "initial_analysis" in prompt
        assert "AI failed to activate required skills" in prompt  # Description
        assert "Commands require skill activation first" in prompt  # Context
        assert "Analyze conversation for slash commands" in prompt  # Instructions
        assert "[Turn" in prompt  # Conversation

    def test_phase_2_prompt_includes_previous_findings(
        self, analyzer, sample_conversation, command_activation_rule
    ):
        """Test that phase 2 includes findings from phase 1."""
        phase_def = command_activation_rule.phases[1]

        previous_findings = [
            {
                "turn_number": 1,
                "observed_behavior": "User executed /test slash command",
                "expected_behavior": "Should activate skills first",
                "context": "Command requires code-review skill",
            }
        ]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=1,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=previous_findings,
        )

        # Must include previous findings
        assert "User executed /test slash command" in prompt
        assert "Command requires code-review skill" in prompt

        # Must still include conversation
        assert "Run the /test command" in prompt

    def test_phase_2_prompt_includes_loaded_resources(
        self, analyzer, sample_conversation, command_activation_rule
    ):
        """Test that phase 2 includes resources loaded from phase 1."""
        phase_def = command_activation_rule.phases[1]

        resources_loaded = [
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="command", resource_id="test", reason="Testing"
                ),
                found=True,
                content="# Test Command\n\nRequired skills:\n- code-review\n",
            ),
        ]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=1,
            phase_def=phase_def,
            resources_loaded=resources_loaded,
            previous_findings=[],
        )

        # Must include loaded resource content
        assert "Test Command" in prompt
        assert "Required skills:" in prompt
        assert "code-review" in prompt

        # Must identify the resource type
        assert "command" in prompt.lower()

    def test_prompt_includes_all_conversation_turns(
        self, analyzer, sample_conversation, command_activation_rule
    ):
        """Test that prompt includes ALL conversation turns, not just first."""
        # Add more turns
        sample_conversation.turns.extend(
            [
                Turn(number=3, user_message="Turn 3 user", ai_message="Turn 3 ai"),
                Turn(number=4, user_message="Turn 4 user", ai_message="Turn 4 ai"),
            ]
        )

        phase_def = command_activation_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must include ALL turns
        assert "Turn 1" in prompt
        assert "Turn 2" in prompt
        assert "Turn 3" in prompt
        assert "Turn 4" in prompt
        assert "Turn 3 user" in prompt
        assert "Turn 4 ai" in prompt

    def test_prompt_does_not_request_conversation_when_already_provided(
        self, analyzer, sample_conversation, command_activation_rule
    ):
        """Test that prompt doesn't ask LLM to request conversation turns."""
        phase_def = command_activation_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must NOT suggest requesting conversation
        bad_phrases = [
            "request conversation",
            "need conversation",
            "access to conversation",
            "request all conversation turns",
            "cannot make final determination without",
        ]

        prompt_lower = prompt.lower()
        for phrase in bad_phrases:
            assert phrase not in prompt_lower, f"Prompt should not contain '{phrase}'"

    def test_prompt_with_empty_conversation(self, analyzer, tmp_path, command_activation_rule):
        """Test prompt generation with conversation that has no turns."""
        empty_conversation = Conversation(
            session_id="empty",
            agent_tool="claude-code",
            file_path=str(tmp_path / "empty.jsonl"),
            project_path=str(tmp_path),
            turns=[],
        )

        phase_def = command_activation_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=empty_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Should handle empty conversation gracefully
        assert "**Conversation**:" in prompt
        # Should still have structure even with no turns
        assert "command_activation_required" in prompt

    def test_prompt_escapes_special_characters(self, analyzer, tmp_path, command_activation_rule):
        """Test that special characters in conversation are properly included."""
        special_conversation = Conversation(
            session_id="special",
            agent_tool="claude-code",
            file_path=str(tmp_path / "special.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(
                    number=1,
                    user_message='Run command with "quotes" and $variables',
                    ai_message="Response with <html> & special chars",
                ),
            ],
        )

        phase_def = command_activation_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=special_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must preserve special characters
        assert '"quotes"' in prompt
        assert "$variables" in prompt
        assert "<html>" in prompt
        assert "&" in prompt

    def test_all_phases_include_conversation(
        self, analyzer, sample_conversation, command_activation_rule
    ):
        """Test that EVERY phase includes the conversation."""
        for phase_idx, phase_def in enumerate(command_activation_rule.phases):
            prompt = analyzer._build_multi_phase_prompt(
                conversation=sample_conversation,
                rule_type="command_activation_required",
                type_config=command_activation_rule,
                phase_idx=phase_idx,
                phase_def=phase_def,
                resources_loaded=[],
                previous_findings=[],
            )

            # EVERY phase must include conversation
            assert "Run the /test command" in prompt, f"Phase {phase_idx + 1} missing conversation"
            assert "Running tests now..." in prompt, f"Phase {phase_idx + 1} missing conversation"

    def test_prompt_format_is_llm_friendly(
        self, analyzer, sample_conversation, command_activation_rule
    ):
        """Test that prompt format is clear and unambiguous for LLM."""
        phase_def = command_activation_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            rule_type="command_activation_required",
            type_config=command_activation_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must have clear structure with headers
        assert "**" in prompt or "##" in prompt or "Analysis Type" in prompt
        # Must separate conversation turns clearly
        assert "[Turn" in prompt or "Turn 1" in prompt
        # Must have clear instructions
        assert "Analyze" in prompt or "Analysis Instructions" in prompt


class TestSinglePhasePromptGeneration:
    """Tests for single-phase (non-multi-phase) prompt generation."""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer with minimal config."""
        config = DriftConfig()
        return DriftAnalyzer(config=config, project_path=tmp_path)

    @pytest.fixture
    def sample_conversation(self, tmp_path):
        """Create a sample conversation."""
        return Conversation(
            session_id="test-456",
            agent_tool="claude-code",
            file_path=str(tmp_path / "test.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(
                    number=1,
                    user_message="Help me fix this bug",
                    ai_message="Let me investigate...",
                ),
                Turn(
                    number=2,
                    user_message="Did you find it?",
                    ai_message="Yes, found the issue!",
                ),
            ],
        )

    @pytest.fixture
    def single_phase_rule(self):
        """Create a single-phase learning type."""
        return RuleDefinition(
            description="Work left incomplete",
            scope="conversation_level",
            context="Work should be completed",
            requires_project_context=False,
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    model="haiku",
                    prompt="Identify incomplete work in the conversation",
                ),
            ],
        )

    def test_single_phase_prompt_includes_conversation(
        self, analyzer, sample_conversation, single_phase_rule
    ):
        """Test single-phase prompt includes full conversation."""
        prompt = analyzer._build_analysis_prompt(
            sample_conversation, "incomplete_work", single_phase_rule
        )

        # Must include ALL turns
        assert "Help me fix this bug" in prompt
        assert "Let me investigate..." in prompt
        assert "Did you find it?" in prompt
        assert "Yes, found the issue!" in prompt

    def test_single_phase_prompt_includes_context(
        self, analyzer, sample_conversation, single_phase_rule
    ):
        """Test single-phase prompt includes learning type context."""
        prompt = analyzer._build_analysis_prompt(
            sample_conversation, "incomplete_work", single_phase_rule
        )

        # Must include description and instructions
        assert "Work left incomplete" in prompt  # Description
        assert "Identify incomplete work" in prompt  # Phase prompt/instructions

    def test_single_phase_prompt_structure(self, analyzer, sample_conversation, single_phase_rule):
        """Test single-phase prompt has proper structure."""
        prompt = analyzer._build_analysis_prompt(
            sample_conversation, "incomplete_work", single_phase_rule
        )

        # Must have clear sections
        assert "incomplete_work" in prompt
        assert "Work left incomplete" in prompt  # Description
        assert "[Turn" in prompt  # Conversation


class TestMultiPhaseScenarios:
    """Tests for multiple multi-phase scenarios."""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer."""
        config = DriftConfig()
        return DriftAnalyzer(config=config, project_path=tmp_path)

    @pytest.fixture
    def three_phase_rule(self):
        """Create a 3-phase learning type."""
        return RuleDefinition(
            description="Documentation drift",
            scope="conversation_level",
            context="Docs should match behavior",
            requires_project_context=True,
            phases=[
                PhaseDefinition(
                    name="identify_behavior",
                    type="prompt",
                    model="haiku",
                    prompt="Identify what the AI did",
                    available_resources=["command", "skill"],
                ),
                PhaseDefinition(
                    name="check_documentation",
                    type="prompt",
                    model="haiku",
                    prompt="Check if behavior matches docs",
                    available_resources=["command", "skill", "main_config"],
                ),
                PhaseDefinition(
                    name="final_determination",
                    type="prompt",
                    model="haiku",
                    prompt="Make final determination",
                    available_resources=[],
                ),
            ],
        )

    def test_scenario_all_resources_found(self, analyzer, tmp_path, three_phase_rule):
        """Test scenario where all requested resources are found."""
        conversation = Conversation(
            session_id="scenario-1",
            agent_tool="claude-code",
            file_path=str(tmp_path / "s1.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(number=1, user_message="Do something", ai_message="Done"),
            ],
        )

        # Phase 2 with loaded resources
        phase_def = three_phase_rule.phases[1]
        resources = [
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="command", resource_id="test", reason="Check"
                ),
                found=True,
                content="# Test\nDoes things",
            ),
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="skill", resource_id="review", reason="Check"
                ),
                found=True,
                content="# Review\nReviews code",
            ),
        ]

        previous_findings = [
            {
                "turn_number": 1,
                "observed_behavior": "AI executed test command",
                "expected_behavior": "Should verify command requirements",
                "context": "Command execution without verification",
            }
        ]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=conversation,
            rule_type="documentation_drift",
            type_config=three_phase_rule,
            phase_idx=1,
            phase_def=phase_def,
            resources_loaded=resources,
            previous_findings=previous_findings,
        )

        # Must include conversation
        assert "Do something" in prompt
        # Must include previous findings
        assert "AI executed test command" in prompt
        # Must include all loaded resources
        assert "Test" in prompt
        assert "Does things" in prompt
        assert "Review" in prompt
        assert "Reviews code" in prompt

    def test_scenario_some_resources_not_found(self, analyzer, tmp_path, three_phase_rule):
        """Test scenario where some resources were not found."""
        conversation = Conversation(
            session_id="scenario-2",
            agent_tool="claude-code",
            file_path=str(tmp_path / "s2.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(number=1, user_message="Test", ai_message="Testing"),
            ],
        )

        phase_def = three_phase_rule.phases[1]
        resources = [
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="command", resource_id="test", reason="Check"
                ),
                found=True,
                content="# Test command",
            ),
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="skill", resource_id="missing", reason="Check"
                ),
                found=False,
                content="",
            ),
        ]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=conversation,
            rule_type="documentation_drift",
            type_config=three_phase_rule,
            phase_idx=1,
            phase_def=phase_def,
            resources_loaded=resources,
            previous_findings=[],
        )

        # Must include found resource
        assert "Test command" in prompt
        # Must indicate missing resource
        assert "missing" in prompt.lower() or "not found" in prompt.lower()

    def test_scenario_final_phase_no_resources(self, analyzer, tmp_path, three_phase_rule):
        """Test final phase that doesn't request resources."""
        conversation = Conversation(
            session_id="scenario-3",
            agent_tool="claude-code",
            file_path=str(tmp_path / "s3.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(number=1, user_message="Q", ai_message="A"),
            ],
        )

        # Final phase
        phase_def = three_phase_rule.phases[2]
        previous_findings = [
            {
                "turn_number": 1,
                "observed_behavior": "Finding from phase 1",
                "expected_behavior": "Expected 1",
                "context": "Context 1",
            },
            {
                "turn_number": 2,
                "observed_behavior": "Finding from phase 2",
                "expected_behavior": "Expected 2",
                "context": "Context 2",
            },
        ]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=conversation,
            rule_type="documentation_drift",
            type_config=three_phase_rule,
            phase_idx=2,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=previous_findings,
        )

        # Must include conversation
        assert "Q" in prompt and "A" in prompt
        # Must include ALL previous findings
        assert "Finding from phase 1" in prompt
        assert "Finding from phase 2" in prompt
        # Must have final determination instructions
        assert "final determination" in prompt.lower()

    def test_scenario_long_conversation(self, analyzer, tmp_path, three_phase_rule):
        """Test with a long conversation with many turns."""
        turns = [
            Turn(number=i, user_message=f"User {i}", ai_message=f"AI {i}")
            for i in range(1, 21)  # 20 turns
        ]

        conversation = Conversation(
            session_id="scenario-long",
            agent_tool="claude-code",
            file_path=str(tmp_path / "long.jsonl"),
            project_path=str(tmp_path),
            turns=turns,
        )

        phase_def = three_phase_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=conversation,
            rule_type="documentation_drift",
            type_config=three_phase_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must include ALL 20 turns
        for i in range(1, 21):
            assert f"User {i}" in prompt, f"Missing turn {i}"
            assert f"AI {i}" in prompt, f"Missing turn {i}"

    def test_scenario_complex_conversation_content(self, analyzer, tmp_path, three_phase_rule):
        """Test with complex conversation containing code, commands, etc."""
        conversation = Conversation(
            session_id="scenario-complex",
            agent_tool="claude-code",
            file_path=str(tmp_path / "complex.jsonl"),
            project_path=str(tmp_path),
            turns=[
                Turn(
                    number=1,
                    user_message="Run /test with --coverage flag",
                    ai_message="Running: `pytest --cov`\nOutput:\n```\nAll tests passed\n```",
                ),
                Turn(
                    number=2,
                    user_message="Check code in src/main.py:42",
                    ai_message=(
                        "Found issue at line 42:\n```python\ndef foo():\n" '    return "bar"\n```'
                    ),
                ),
            ],
        )

        phase_def = three_phase_rule.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=conversation,
            rule_type="documentation_drift",
            type_config=three_phase_rule,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Must preserve all content
        assert "/test" in prompt
        assert "--coverage" in prompt
        assert "pytest --cov" in prompt
        assert "All tests passed" in prompt
        assert "src/main.py:42" in prompt
        assert 'return "bar"' in prompt or "return" in prompt
