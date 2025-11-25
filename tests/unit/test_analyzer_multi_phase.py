"""Tests for multi-phase analysis in DriftAnalyzer."""

import json
from unittest.mock import patch

import pytest

from drift.config.models import DriftLearningType, PhaseDefinition
from drift.core.analyzer import DriftAnalyzer
from tests.mock_provider import MockProvider


class TestMultiPhaseAnalysis:
    """Test multi-phase analysis functionality."""

    @pytest.fixture
    def multi_phase_learning_type(self):
        """Create a multi-phase learning type."""
        return DriftLearningType(
            description="Multi-phase test",
            scope="conversation_level",
            context="Testing multi-phase",
            requires_project_context=True,
            supported_clients=["claude-code"],
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Detect issues",
                    model="haiku",
                    available_resources=["command:test"],
                ),
                PhaseDefinition(
                    name="analysis",
                    type="prompt",
                    prompt="Analyze issues",
                    model="haiku",
                    available_resources=[],
                ),
            ],
        )

    @pytest.fixture
    def config_with_multi_phase(self, sample_drift_config, multi_phase_learning_type):
        """Config with multi-phase learning type."""
        config = sample_drift_config
        config.drift_learning_types["multi_phase_test"] = multi_phase_learning_type
        return config

    @pytest.fixture
    def project_with_resources(self, temp_dir):
        """Project with resources."""
        project = temp_dir / "test_project"
        project.mkdir()

        commands_dir = project / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "test.md").write_text("# Test Command")

        return project

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_multi_phase_basic_execution(
        self, config_with_multi_phase, sample_conversation_jsonl, project_with_resources
    ):
        """Test basic multi-phase analysis."""
        # Set up conversation with project path
        sample_conversation_jsonl.parent.mkdir(parents=True, exist_ok=True)

        mock_provider = MockProvider()
        mock_provider.set_response(json.dumps([]))

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=config_with_multi_phase)

            # Get conversations
            conversations = analyzer.agent_loaders["claude-code"].load_conversations()

            if conversations:
                conversation = conversations[0]
                conversation.project_path = str(project_with_resources)

                # Run multi-phase analysis
                learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                    conversation=conversation,
                    learning_type="multi_phase_test",
                    type_config=config_with_multi_phase.drift_learning_types["multi_phase_test"],
                    model_override=None,
                )

                # Should complete without fatal error
                assert isinstance(learnings, list)
                assert isinstance(phase_results, list)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_multi_phase_no_phases_error(self, sample_drift_config, sample_conversation):
        """Test multi-phase with no phases configured."""
        bad_type = DriftLearningType(
            description="No phases",
            scope="conversation_level",
            context="Test",
            requires_project_context=False,
            supported_clients=None,
            phases=[],
        )

        config = sample_drift_config
        config.drift_learning_types["bad"] = bad_type

        analyzer = DriftAnalyzer(config=config)

        with pytest.raises(ValueError, match="no phases configured"):
            analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="bad",
                type_config=bad_type,
                model_override=None,
            )

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_multi_phase_no_agent_loader(self, config_with_multi_phase, sample_conversation):
        """Test multi-phase when agent loader missing."""
        conversation = sample_conversation
        conversation.agent_tool = "unsupported"

        analyzer = DriftAnalyzer(config=config_with_multi_phase)

        learnings, error, phase_results = analyzer._run_multi_phase_analysis(
            conversation=conversation,
            learning_type="multi_phase_test",
            type_config=config_with_multi_phase.drift_learning_types["multi_phase_test"],
            model_override=None,
        )

        assert error is not None
        assert "No agent loader" in error
        assert len(learnings) == 0

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_build_multi_phase_prompt(
        self, config_with_multi_phase, sample_conversation, project_with_resources
    ):
        """Test building multi-phase prompt."""
        sample_conversation.project_path = str(project_with_resources)

        analyzer = DriftAnalyzer(config=config_with_multi_phase)

        type_config = config_with_multi_phase.drift_learning_types["multi_phase_test"]
        phase_def = type_config.phases[0]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            learning_type="multi_phase_test",
            type_config=type_config,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_build_multi_phase_prompt_with_resources(
        self, config_with_multi_phase, sample_conversation, project_with_resources
    ):
        """Test building prompt with resources."""
        sample_conversation.project_path = str(project_with_resources)

        analyzer = DriftAnalyzer(config=config_with_multi_phase)

        type_config = config_with_multi_phase.drift_learning_types["multi_phase_test"]
        phase_def = type_config.phases[0]

        resources = [{"type": "command", "id": "test", "content": "Test"}]

        prompt = analyzer._build_multi_phase_prompt(
            conversation=sample_conversation,
            learning_type="multi_phase_test",
            type_config=type_config,
            phase_idx=0,
            phase_def=phase_def,
            resources_loaded=resources,
            previous_findings=[],
        )

        assert isinstance(prompt, str)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_multi_phase_with_provider_error(
        self, config_with_multi_phase, sample_conversation, project_with_resources
    ):
        """Test multi-phase when provider fails."""
        sample_conversation.project_path = str(project_with_resources)

        analyzer = DriftAnalyzer(config=config_with_multi_phase)

        # Should raise error when model not found
        analyzer.providers.clear()

        with pytest.raises(ValueError, match="Model.*not found"):
            analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="multi_phase_test",
                type_config=config_with_multi_phase.drift_learning_types["multi_phase_test"],
                model_override=None,
            )

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_multi_phase_with_resource_loading_flow(
        self, config_with_multi_phase, sample_conversation, project_with_resources
    ):
        """Test complete multi-phase flow with resource loading."""
        sample_conversation.project_path = str(project_with_resources)

        # Phase 1: Request resources
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command", "resource_id": "test", "reason": "Need command"}
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        # Phase 2: After resources loaded, return final findings
        phase2_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {
                        "observed_behavior": "Found issue after checking command",
                        "expected_behavior": "Should be correct",
                    }
                ],
                "final_determination": True,
            }
        )

        responses = [phase1_response, phase2_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                # Still call original to track calls
                original_generate(prompt, **kwargs)
                # But return our custom response
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=config_with_multi_phase)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="multi_phase_test",
                type_config=config_with_multi_phase.drift_learning_types["multi_phase_test"],
                model_override=None,
            )

            # Debug: Check what actually happened
            print(f"Number of calls: {len(mock_provider.calls)}")
            print(f"Number of phase results: {len(phase_results)}")
            print(f"Error: {error}")
            for i, result in enumerate(phase_results):
                print(
                    f"Phase {i+1}: {len(result.resource_requests)} requests, "
                    f"{len(result.findings)} findings, final={result.final_determination}"
                )

            # Verify both phases executed
            assert (
                len(mock_provider.calls) == 2
            ), f"Both phases should have been called, got {len(mock_provider.calls)}"
            assert len(phase_results) == 2, "Should have results from both phases"

            # Verify phase 2 prompt includes loaded resource
            phase2_prompt = mock_provider.calls[1]["prompt"]
            assert (
                "Test Command" in phase2_prompt
            ), "Phase 2 prompt should include loaded resource content"

            # Verify final learnings were created
            assert error is None or error == ""
            assert isinstance(learnings, list)
            assert len(learnings) > 0, "Should have learnings from phase 2 findings"
            assert learnings[0].observed_behavior == "Found issue after checking command"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_multi_phase_analysis_no_resource_requests(
        self, config_with_multi_phase, sample_conversation, project_with_resources
    ):
        """Test multi-phase analysis where first phase returns no resource requests."""
        sample_conversation.project_path = str(project_with_resources)

        # First phase returns no resource requests (ends analysis early)
        phase1_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {"observed_behavior": "Found issue", "expected_behavior": "Should be correct"}
                ],
                "final_determination": True,
            }
        )

        mock_provider = MockProvider()
        mock_provider.set_response(phase1_response)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=config_with_multi_phase)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="multi_phase_test",
                type_config=config_with_multi_phase.drift_learning_types["multi_phase_test"],
                model_override=None,
            )

            # Should complete with findings from first phase
            assert error is None or error == ""
            assert isinstance(learnings, list)
            assert len(phase_results) == 1


class TestResourceLoading:
    """Test resource loading for multi-phase."""

    @pytest.fixture
    def project_with_resources(self, temp_dir):
        """Project with various resources."""
        project = temp_dir / "project"
        project.mkdir()

        # Commands
        commands_dir = project / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "deploy.md").write_text("# Deploy")

        # Skills
        skills_dir = project / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing.md").write_text("# Testing")

        return project

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_load_command_resource(self, sample_drift_config, project_with_resources):
        """Test loading command resource."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        loader = analyzer.agent_loaders.get("claude-code")
        assert loader is not None

        response = loader.get_resource(
            "command", "deploy", project_path=str(project_with_resources)
        )

        assert response.found is True
        assert "Deploy" in response.content

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_load_skill_resource(self, sample_drift_config, project_with_resources):
        """Test loading skill resource."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        loader = analyzer.agent_loaders.get("claude-code")

        response = loader.get_resource("skill", "testing", project_path=str(project_with_resources))

        assert response.found is True
        assert "Testing" in response.content

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_load_nonexistent_resource(self, sample_drift_config, project_with_resources):
        """Test loading nonexistent resource."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        loader = analyzer.agent_loaders.get("claude-code")

        response = loader.get_resource(
            "command", "nonexistent", project_path=str(project_with_resources)
        )

        assert response.found is False
        assert response.error is not None

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_parse_phase_response_with_resource_requests(self, sample_drift_config):
        """Test parsing phase response with resource requests."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        response_with_requests = json.dumps(
            {
                "resource_requests": [
                    {
                        "resource_type": "command",
                        "resource_id": "test",
                        "reason": "Need to see command",
                    },
                    {"type": "skill", "name": "testing", "reason": "Need skill info"},
                ],
                "findings": [{"finding": "Found something"}],
                "final_determination": False,
            }
        )

        result = analyzer._parse_phase_response(response_with_requests, phase=1)

        assert len(result.resource_requests) == 2
        assert result.resource_requests[0].resource_type == "command"
        assert result.resource_requests[0].resource_id == "test"
        assert result.resource_requests[1].resource_type == "skill"
        assert result.resource_requests[1].resource_id == "testing"
        assert result.phase_number == 1
        assert not result.final_determination

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_parse_phase_response_with_invalid_json(self, sample_drift_config):
        """Test parsing phase response with invalid JSON."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        result = analyzer._parse_phase_response("not valid json", phase=2)

        assert result.phase_number == 2
        assert len(result.resource_requests) == 0
        assert result.final_determination is True

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_parse_phase_response_skips_incomplete_requests(self, sample_drift_config):
        """Test that incomplete resource requests are skipped."""
        analyzer = DriftAnalyzer(config=sample_drift_config)

        response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command"},  # Missing ID
                    {"resource_id": "test"},  # Missing type
                    {"resource_type": "skill", "resource_id": "valid"},  # Valid
                ],
                "findings": [],
            }
        )

        result = analyzer._parse_phase_response(response, phase=1)

        # Only the valid request should be included
        assert len(result.resource_requests) == 1
        assert result.resource_requests[0].resource_type == "skill"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_create_missing_resource_learnings(
        self, sample_drift_config, sample_conversation, temp_dir
    ):
        """Test creating learnings for missing resources."""
        from drift.core.types import PhaseAnalysisResult, ResourceRequest, ResourceResponse

        analyzer = DriftAnalyzer(config=sample_drift_config)
        sample_conversation.project_path = str(temp_dir)

        # Create phase results with resource requests
        phase_results = [
            PhaseAnalysisResult(
                phase_number=1,
                resource_requests=[
                    ResourceRequest(resource_type="command", resource_id="test", reason="Need it")
                ],
                findings=[],
                final_determination=False,
            )
        ]

        # Create resources that weren't found
        resources_loaded = [
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="command", resource_id="test", reason="Need it"
                ),
                found=False,
                content=None,
                file_path=None,
                error="Command not found",
            )
        ]

        learnings, error, results = analyzer._create_missing_resource_learnings(
            conversation=sample_conversation,
            learning_type="test_type",
            resources_loaded=resources_loaded,
            phase_results=phase_results,
        )

        # Should create learnings for missing resources
        assert len(learnings) > 0
        assert learnings[0].learning_type == "missing_command"
        assert "not found" in learnings[0].observed_behavior.lower()

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_finalize_multi_phase_learnings_with_findings(
        self, sample_drift_config, sample_conversation
    ):
        """Test finalizing multi-phase learnings with valid findings."""
        from drift.core.types import PhaseAnalysisResult

        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Create phase results with findings
        phase_results = [
            PhaseAnalysisResult(
                phase_number=1,
                resource_requests=[],
                findings=[
                    {
                        "observed_behavior": "Agent did something wrong",
                        "expected_behavior": "Agent should do it right",
                        "context": "During testing",
                        "turn_number": 1,
                    }
                ],
                final_determination=True,
            )
        ]

        learnings, error = analyzer._finalize_multi_phase_learnings(
            conversation=sample_conversation,
            learning_type="test_type",
            phase_results=phase_results,
            resources_consulted=[],
        )

        # Should create learnings from findings
        assert len(learnings) > 0
        assert learnings[0].learning_type == "test_type"
        assert learnings[0].observed_behavior == "Agent did something wrong"
        assert learnings[0].expected_behavior == "Agent should do it right"
        assert learnings[0].context == "During testing"
        assert learnings[0].phases_count == 1

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_finalize_multi_phase_learnings_with_malformed_findings(
        self, sample_drift_config, sample_conversation
    ):
        """Test finalizing learnings with malformed findings (missing fields)."""
        from drift.core.types import PhaseAnalysisResult

        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Create phase results with malformed findings
        phase_results = [
            PhaseAnalysisResult(
                phase_number=1,
                resource_requests=[],
                findings=[
                    {
                        "observed_behavior": "",  # Empty - should be skipped
                        "expected_behavior": "Should exist",
                    },
                    {
                        "observed_behavior": "Has observed",
                        "expected_behavior": "",  # Empty - should be skipped
                    },
                    {
                        "observed_behavior": "   ",  # Whitespace only - should be skipped
                        "expected_behavior": "   ",
                    },
                    {
                        "observed_behavior": "Valid observation",
                        "expected_behavior": "Valid expectation",
                    },
                ],
                final_determination=True,
            )
        ]

        learnings, error = analyzer._finalize_multi_phase_learnings(
            conversation=sample_conversation,
            learning_type="test_type",
            phase_results=phase_results,
            resources_consulted=[],
        )

        # Should only create learning for valid finding
        assert len(learnings) == 1
        assert learnings[0].observed_behavior == "Valid observation"
        assert learnings[0].expected_behavior == "Valid expectation"

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_finalize_multi_phase_learnings_with_resources_consulted(
        self, sample_drift_config, sample_conversation
    ):
        """Test finalizing learnings includes resources consulted."""
        from drift.core.types import PhaseAnalysisResult, ResourceRequest

        analyzer = DriftAnalyzer(config=sample_drift_config)

        # Create resources consulted
        resources_consulted = ["command:test", "skill:testing"]

        # Create phase results with findings
        phase_results = [
            PhaseAnalysisResult(
                phase_number=1,
                resource_requests=[
                    ResourceRequest(resource_type="command", resource_id="test", reason="Need it")
                ],
                findings=[
                    {
                        "observed_behavior": "Issue found",
                        "expected_behavior": "Should be correct",
                    }
                ],
                final_determination=True,
            )
        ]

        learnings, error = analyzer._finalize_multi_phase_learnings(
            conversation=sample_conversation,
            learning_type="test_type",
            phase_results=phase_results,
            resources_consulted=resources_consulted,
        )

        # Should include resources consulted
        assert len(learnings) > 0
        assert learnings[0].resources_consulted is not None
        assert "command:test" in learnings[0].resources_consulted


class TestMultiPhaseEdgeCases:
    """Test edge cases in multi-phase analysis."""

    @pytest.fixture
    def three_phase_config(self, sample_drift_config):
        """Create config with 3 phases."""
        three_phase_type = DriftLearningType(
            description="Three phase test",
            scope="conversation_level",
            context="Testing three phases",
            requires_project_context=True,
            supported_clients=["claude-code"],
            phases=[
                PhaseDefinition(
                    name="detection",
                    type="prompt",
                    prompt="Detect issues",
                    model="haiku",
                    available_resources=["command"],
                ),
                PhaseDefinition(
                    name="analysis",
                    type="prompt",
                    prompt="Analyze issues",
                    model="haiku",
                    available_resources=["skill"],
                ),
                PhaseDefinition(
                    name="recommendations",
                    type="prompt",
                    prompt="Recommend fixes",
                    model="haiku",
                    available_resources=["agent"],
                ),
            ],
        )
        config = sample_drift_config
        config.drift_learning_types["three_phase"] = three_phase_type
        return config

    @pytest.fixture
    def project_with_all_resources(self, temp_dir):
        """Project with all resource types."""
        project = temp_dir / "full_project"
        project.mkdir()

        commands_dir = project / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "test.md").write_text("# Test Command")
        (commands_dir / "deploy.md").write_text("# Deploy Command")

        skills_dir = project / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing.md").write_text("# Testing Skill")
        (skills_dir / "review.md").write_text("# Review Skill")

        agents_dir = project / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "qa.md").write_text("# QA Agent")

        return project

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_three_phase_flow(
        self,
        three_phase_config,
        sample_conversation,
        project_with_all_resources,
    ):
        """Test analysis that goes through 3 phases."""
        sample_conversation.project_path = str(project_with_all_resources)

        # Phase 1: Request command
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command", "resource_id": "test", "reason": "Need command"}
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        # Phase 2: Request skill
        phase2_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "skill", "resource_id": "testing", "reason": "Need skill"}
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        # Phase 3: Final with findings
        phase3_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {
                        "observed_behavior": "Found issue after 3 phases",
                        "expected_behavior": "Should be correct",
                    }
                ],
                "final_determination": True,
            }
        )

        responses = [phase1_response, phase2_response, phase3_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                original_generate(prompt, **kwargs)
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=three_phase_config)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="three_phase",
                type_config=three_phase_config.drift_learning_types["three_phase"],
                model_override=None,
            )

            # Verify all 3 phases executed
            num_calls = len(mock_provider.calls)
            assert num_calls == 3, f"Expected 3 phases, got {num_calls}"
            assert len(phase_results) == 3

            # Verify resources were requested in each phase
            assert len(phase_results[0].resource_requests) == 1
            assert phase_results[0].resource_requests[0].resource_type == "command"

            assert len(phase_results[1].resource_requests) == 1
            assert phase_results[1].resource_requests[0].resource_type == "skill"

            assert len(phase_results[2].resource_requests) == 0
            assert phase_results[2].final_determination is True

            # Verify final learnings
            assert len(learnings) > 0
            assert learnings[0].phases_count == 3

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_multiple_resources_same_type(
        self, three_phase_config, sample_conversation, project_with_all_resources
    ):
        """Test requesting multiple resources of the same type in one phase."""
        sample_conversation.project_path = str(project_with_all_resources)

        # Phase 1: Request multiple commands
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command", "resource_id": "test", "reason": "Need test"},
                    {"resource_type": "command", "resource_id": "deploy", "reason": "Need deploy"},
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        # Phase 2: Final with findings
        phase2_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {
                        "observed_behavior": "Found issue after checking both commands",
                        "expected_behavior": "Both commands should be correct",
                    }
                ],
                "final_determination": True,
            }
        )

        responses = [phase1_response, phase2_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                original_generate(prompt, **kwargs)
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=three_phase_config)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="three_phase",
                type_config=three_phase_config.drift_learning_types["three_phase"],
                model_override=None,
            )

            # Verify both resources were requested
            assert len(phase_results[0].resource_requests) == 2
            assert phase_results[0].resource_requests[0].resource_id == "test"
            assert phase_results[0].resource_requests[1].resource_id == "deploy"

            # Verify phase 2 prompt includes both resources
            phase2_prompt = mock_provider.calls[1]["prompt"]
            assert "Test Command" in phase2_prompt
            assert "Deploy Command" in phase2_prompt

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_mixed_resource_types_in_phase(
        self, sample_drift_config, sample_conversation, project_with_all_resources
    ):
        """Test requesting different resource types in same phase."""
        sample_conversation.project_path = str(project_with_all_resources)

        # Create config that allows multiple resource types
        multi_type = DriftLearningType(
            description="Multi-resource test",
            scope="conversation_level",
            context="Testing multiple resource types",
            requires_project_context=True,
            supported_clients=["claude-code"],
            phases=[
                PhaseDefinition(
                    name="gather",
                    type="prompt",
                    prompt="Gather resources",
                    model="haiku",
                    available_resources=["command", "skill", "agent"],
                ),
                PhaseDefinition(
                    name="analyze",
                    type="prompt",
                    prompt="Analyze",
                    model="haiku",
                    available_resources=[],
                ),
            ],
        )

        config = sample_drift_config
        config.drift_learning_types["multi_type"] = multi_type

        # Phase 1: Request command, skill, and agent
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command", "resource_id": "test", "reason": "Need command"},
                    {"resource_type": "skill", "resource_id": "testing", "reason": "Need skill"},
                    {"resource_type": "agent", "resource_id": "qa", "reason": "Need agent"},
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        # Phase 2: Final
        phase2_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {
                        "observed_behavior": "Checked all resource types",
                        "expected_behavior": "All should be correct",
                    }
                ],
                "final_determination": True,
            }
        )

        responses = [phase1_response, phase2_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                original_generate(prompt, **kwargs)
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=config)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="multi_type",
                type_config=config.drift_learning_types["multi_type"],
                model_override=None,
            )

            # Verify all 3 resource types were requested
            assert len(phase_results[0].resource_requests) == 3
            types = [r.resource_type for r in phase_results[0].resource_requests]
            assert "command" in types
            assert "skill" in types
            assert "agent" in types

            # Verify phase 2 prompt includes all resources
            phase2_prompt = mock_provider.calls[1]["prompt"]
            assert "Test Command" in phase2_prompt
            assert "Testing Skill" in phase2_prompt
            assert "QA Agent" in phase2_prompt

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_partial_resource_loading(
        self, three_phase_config, sample_conversation, project_with_all_resources
    ):
        """Test when some resources found, others not (should continue)."""
        sample_conversation.project_path = str(project_with_all_resources)

        # Phase 1: Request one that exists and one that doesn't
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command", "resource_id": "test", "reason": "Exists"},
                    {
                        "resource_type": "command",
                        "resource_id": "nonexistent",
                        "reason": "Doesn't exist",
                    },
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        # Phase 2: Should continue because one resource was found
        phase2_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {
                        "observed_behavior": "One resource found, one missing",
                        "expected_behavior": "Should handle gracefully",
                    }
                ],
                "final_determination": True,
            }
        )

        responses = [phase1_response, phase2_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                original_generate(prompt, **kwargs)
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=three_phase_config)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="three_phase",
                type_config=three_phase_config.drift_learning_types["three_phase"],
                model_override=None,
            )

            # Should continue to phase 2 (not all resources missing)
            assert len(phase_results) == 2
            assert len(learnings) > 0

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_max_phases_without_final_determination(
        self, three_phase_config, sample_conversation, project_with_all_resources
    ):
        """Test when we exhaust all phases without final_determination."""
        sample_conversation.project_path = str(project_with_all_resources)

        # All phases keep requesting resources, never finalize
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command", "resource_id": "test", "reason": "Need it"}
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        phase2_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "skill", "resource_id": "testing", "reason": "Need it"}
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        phase3_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "agent", "resource_id": "qa", "reason": "Need it"}
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        responses = [phase1_response, phase2_response, phase3_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                original_generate(prompt, **kwargs)
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=three_phase_config)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="three_phase",
                type_config=three_phase_config.drift_learning_types["three_phase"],
                model_override=None,
            )

            # Should execute all 3 phases even without final_determination
            assert len(phase_results) == 3

            # Should still attempt to finalize learnings
            # (May be empty if no findings in any phase)
            assert isinstance(learnings, list)

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_type_only_available_resources(
        self, sample_drift_config, sample_conversation, project_with_all_resources
    ):
        """Test when available_resources contains type-only (not full specs)."""
        sample_conversation.project_path = str(project_with_all_resources)

        # Config with type-only available_resources
        type_only = DriftLearningType(
            description="Type-only test",
            scope="conversation_level",
            context="Testing type-only matching",
            requires_project_context=True,
            supported_clients=["claude-code"],
            phases=[
                PhaseDefinition(
                    name="check",
                    type="prompt",
                    prompt="Check",
                    model="haiku",
                    available_resources=["command"],  # Type-only, not "command:test"
                ),
                PhaseDefinition(
                    name="finalize",
                    type="prompt",
                    prompt="Finalize",
                    model="haiku",
                    available_resources=[],
                ),
            ],
        )

        config = sample_drift_config
        config.drift_learning_types["type_only"] = type_only

        # Phase 1: Request specific command
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {
                        "resource_type": "command",
                        "resource_id": "test",
                        "reason": "Should match type-only",
                    }
                ],
                "findings": [],
                "final_determination": False,
            }
        )

        # Phase 2: Final
        phase2_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {
                        "observed_behavior": "Type-only matching works",
                        "expected_behavior": "Should allow any command",
                    }
                ],
                "final_determination": True,
            }
        )

        responses = [phase1_response, phase2_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                original_generate(prompt, **kwargs)
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=config)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="type_only",
                type_config=config.drift_learning_types["type_only"],
                model_override=None,
            )

            # Should match type-only and proceed to phase 2
            assert len(phase_results) == 2
            phase2_prompt = mock_provider.calls[1]["prompt"]
            assert "Test Command" in phase2_prompt

    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_empty_findings_intermediate_phase(
        self, three_phase_config, sample_conversation, project_with_all_resources
    ):
        """Test phase with no findings but requests resources (should continue)."""
        sample_conversation.project_path = str(project_with_all_resources)

        # Phase 1: No findings, just resource request
        phase1_response = json.dumps(
            {
                "resource_requests": [
                    {"resource_type": "command", "resource_id": "test", "reason": "Need to check"}
                ],
                "findings": [],  # Empty findings
                "final_determination": False,
            }
        )

        # Phase 2: After checking resource, find issue
        phase2_response = json.dumps(
            {
                "resource_requests": [],
                "findings": [
                    {
                        "observed_behavior": "Found issue after checking resource",
                        "expected_behavior": "Should be correct",
                    }
                ],
                "final_determination": True,
            }
        )

        responses = [phase1_response, phase2_response]
        call_idx = [0]

        def mock_generate_with_tracking(original_generate):
            def wrapper(prompt, **kwargs):
                idx = call_idx[0]
                call_idx[0] += 1
                original_generate(prompt, **kwargs)
                return responses[min(idx, len(responses) - 1)]

            return wrapper

        mock_provider = MockProvider()
        original_generate = mock_provider.generate
        mock_provider.generate = mock_generate_with_tracking(original_generate)

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            analyzer = DriftAnalyzer(config=three_phase_config)

            learnings, error, phase_results = analyzer._run_multi_phase_analysis(
                conversation=sample_conversation,
                learning_type="three_phase",
                type_config=three_phase_config.drift_learning_types["three_phase"],
                model_override=None,
            )

            # Should continue to phase 2 even though phase 1 had no findings
            assert len(phase_results) == 2
            assert len(phase_results[0].findings) == 0
            assert len(phase_results[1].findings) == 1
            assert len(learnings) > 0
