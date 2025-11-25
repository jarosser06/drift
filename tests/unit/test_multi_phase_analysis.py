"""Unit tests for multi-phase analysis functionality."""

from unittest.mock import MagicMock, patch

import pytest

from drift.agent_tools.claude_code import ClaudeCodeLoader
from drift.config.models import DriftConfig
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import Conversation, ResourceRequest, ResourceResponse, Turn


class TestClaudeCodeResourceExtraction:
    """Test resource extraction from Claude Code projects."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Create a ClaudeCodeLoader with a temp directory."""
        loader = ClaudeCodeLoader(str(tmp_path / "conversations"))
        return loader

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a mock project directory structure."""
        project = tmp_path / "test_project"
        project.mkdir()

        # Create .claude structure
        (project / ".claude").mkdir()
        (project / ".claude" / "commands").mkdir()
        (project / ".claude" / "skills").mkdir()
        (project / ".claude" / "agents").mkdir()

        return project

    def test_get_command_found(self, loader, project_root):
        """Test getting an existing command."""
        # Create a command file
        cmd_file = project_root / ".claude" / "commands" / "test-cmd.md"
        cmd_file.write_text("# Test Command\nDo something cool")

        response = loader.get_resource("command", "test-cmd", str(project_root))

        assert response.found is True
        assert response.content == "# Test Command\nDo something cool"
        assert response.file_path == str(cmd_file)
        assert response.error is None
        assert response.request.resource_type == "command"
        assert response.request.resource_id == "test-cmd"

    def test_get_command_with_leading_slash(self, loader, project_root):
        """Test getting command with leading slash in ID."""
        cmd_file = project_root / ".claude" / "commands" / "deploy.md"
        cmd_file.write_text("Deploy the app")

        response = loader.get_resource("command", "/deploy", str(project_root))

        assert response.found is True
        assert response.content == "Deploy the app"

    def test_get_command_not_found(self, loader, project_root):
        """Test getting a non-existent command."""
        response = loader.get_resource("command", "nonexistent", str(project_root))

        assert response.found is False
        assert response.content is None
        assert response.error is not None
        assert "not found" in response.error.lower()

    def test_get_skill_simple_pattern(self, loader, project_root):
        """Test getting skill with simple .md pattern."""
        skill_file = project_root / ".claude" / "skills" / "api-design.md"
        skill_file.write_text("# API Design Skill\nHelp with APIs")

        response = loader.get_resource("skill", "api-design", str(project_root))

        assert response.found is True
        assert response.content == "# API Design Skill\nHelp with APIs"
        assert response.file_path == str(skill_file)

    def test_get_skill_directory_pattern(self, loader, project_root):
        """Test getting skill with directory/SKILL.md pattern."""
        skill_dir = project_root / ".claude" / "skills" / "testing"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("# Testing Skill\nWrite tests")

        response = loader.get_resource("skill", "testing", str(project_root))

        assert response.found is True
        assert response.content == "# Testing Skill\nWrite tests"
        assert response.file_path == str(skill_file)

    def test_get_skill_not_found(self, loader, project_root):
        """Test getting a non-existent skill."""
        response = loader.get_resource("skill", "nonexistent", str(project_root))

        assert response.found is False
        assert response.error is not None
        assert "not found" in response.error.lower()

    def test_get_agent_found(self, loader, project_root):
        """Test getting an existing agent."""
        agent_file = project_root / ".claude" / "agents" / "code-reviewer.md"
        agent_file.write_text("# Code Reviewer\nReview code for issues")

        response = loader.get_resource("agent", "code-reviewer", str(project_root))

        assert response.found is True
        assert response.content == "# Code Reviewer\nReview code for issues"
        assert response.file_path == str(agent_file)

    def test_get_agent_not_found(self, loader, project_root):
        """Test getting a non-existent agent."""
        response = loader.get_resource("agent", "nonexistent", str(project_root))

        assert response.found is False
        assert response.error is not None

    def test_get_main_config_claude_md(self, loader, project_root):
        """Test getting main config from CLAUDE.md."""
        config_file = project_root / "CLAUDE.md"
        config_file.write_text("# Project Config\nSome setup")

        response = loader.get_resource("main_config", "", str(project_root))

        assert response.found is True
        assert response.content == "# Project Config\nSome setup"
        assert response.file_path == str(config_file)

    def test_get_main_config_mcp_json(self, loader, project_root):
        """Test getting main config from .mcp.json."""
        config_file = project_root / ".mcp.json"
        config_file.write_text('{"mcpServers": {}}')

        response = loader.get_resource("main_config", "", str(project_root))

        assert response.found is True
        assert response.content == '{"mcpServers": {}}'
        assert response.file_path == str(config_file)

    def test_get_main_config_not_found(self, loader, project_root):
        """Test getting main config when neither file exists."""
        response = loader.get_resource("main_config", "", str(project_root))

        assert response.found is False
        assert response.error is not None
        assert "no main config" in response.error.lower()

    def test_get_resource_no_project_path(self, loader):
        """Test getting resource without project path."""
        response = loader.get_resource("command", "test", None)

        assert response.found is False
        assert response.error == "No project path provided"

    def test_get_resource_unknown_type(self, loader, project_root):
        """Test getting resource with unknown type."""
        response = loader.get_resource("unknown_type", "test", str(project_root))

        assert response.found is False
        assert "unknown resource type" in response.error.lower()


class TestMultiPhaseEngine:
    """Test the multi-phase analysis engine."""

    @pytest.fixture
    def config(self):
        """Create a minimal drift config."""
        return DriftConfig(
            providers={
                "bedrock": {
                    "provider": "bedrock",
                    "params": {"region": "us-west-2"},
                }
            },
            models={
                "haiku": {
                    "provider": "bedrock",
                    "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
                    "params": {},
                }
            },
            default_model="haiku",
            drift_learning_types={
                "test_multi_phase": {
                    "description": "Test multi-phase analysis",
                    "scope": "conversation_level",
                    "context": "Testing",
                    "requires_project_context": True,
                    "phases": [
                        {
                            "name": "initial",
                            "type": "prompt",
                            "prompt": "Initial analysis",
                            "model": "haiku",
                            "available_resources": ["command", "skill"],
                        },
                        {
                            "name": "verify",
                            "type": "prompt",
                            "prompt": "Verify findings",
                            "model": "haiku",
                            "available_resources": ["command", "skill"],
                        },
                        {
                            "name": "final",
                            "type": "prompt",
                            "prompt": "Final determination",
                            "model": "haiku",
                            "available_resources": ["command", "skill"],
                        },
                    ],
                }
            },
            agent_tools={
                "claude-code": {
                    "conversation_path": "/tmp/conversations",
                    "enabled": True,
                }
            },
        )

    @pytest.fixture
    def conversation(self):
        """Create a sample conversation."""
        return Conversation(
            session_id="test-session",
            agent_tool="claude-code",
            file_path="/tmp/test.jsonl",
            project_path="/tmp/project",
            turns=[
                Turn(
                    number=1,
                    user_message="How do I deploy?",
                    ai_message="Let me check the deploy command...",
                )
            ],
        )

    @pytest.fixture
    def analyzer(self, config):
        """Create an analyzer with mocked provider."""
        analyzer = DriftAnalyzer(config)
        return analyzer

    def test_parse_phase_response_valid_json(self, analyzer):
        """Test parsing a valid phase response."""
        response_text = """Here's my analysis:

```json
{
    "resource_requests": [
        {
            "resource_type": "command",
            "resource_id": "deploy",
            "reason": "Need to see deploy process"
        }
    ],
    "findings": [],
    "final_determination": false
}
```

I need more info."""

        result = analyzer._parse_phase_response(response_text, 1)

        assert result is not None
        assert len(result.resource_requests) == 1
        assert result.resource_requests[0].resource_type == "command"
        assert result.resource_requests[0].resource_id == "deploy"
        assert result.final_determination is False
        assert result.phase_number == 1

    def test_parse_phase_response_final_determination(self, analyzer):
        """Test parsing a response with final determination."""
        response_text = """```json
{
    "resource_requests": [],
    "findings": [
        {
            "turn_number": 1,
            "observed_behavior": "AI guessed",
            "expected_behavior": "AI should check command",
            "learning_type": "missing_command_reference"
        }
    ],
    "final_determination": true
}
```"""

        result = analyzer._parse_phase_response(response_text, 2)

        assert result is not None
        assert len(result.findings) == 1
        assert result.final_determination is True
        assert result.findings[0]["turn_number"] == 1

    def test_parse_phase_response_invalid_json(self, analyzer):
        """Test parsing response with invalid JSON."""
        response_text = "This is not JSON at all"

        result = analyzer._parse_phase_response(response_text, 1)

        # Implementation returns empty result with final_determination=True
        assert result is not None
        assert result.final_determination is True
        assert result.resource_requests == []

    def test_parse_phase_response_missing_fields(self, analyzer):
        """Test parsing response with missing required fields."""
        response_text = """```json
{
    "findings": []
}
```"""

        result = analyzer._parse_phase_response(response_text, 1)

        # Should still parse with defaults
        assert result is not None
        assert result.resource_requests == []
        assert result.final_determination is False

    def test_format_loaded_resources_found(self, analyzer):
        """Test formatting loaded resources."""
        resources = [
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="command",
                    resource_id="deploy",
                    reason="Testing",
                ),
                found=True,
                content="# Deploy\nRun deploy script",
                file_path="/project/.claude/commands/deploy.md",
            )
        ]

        formatted = analyzer._format_loaded_resources(resources)

        assert "command:deploy" in formatted
        assert "# Deploy" in formatted
        assert "Run deploy script" in formatted

    def test_format_loaded_resources_not_found(self, analyzer):
        """Test formatting missing resources."""
        resources = [
            ResourceResponse(
                request=ResourceRequest(
                    resource_type="skill",
                    resource_id="api-design",
                    reason="Testing",
                ),
                found=False,
                error="Skill not found",
            )
        ]

        formatted = analyzer._format_loaded_resources(resources)

        assert "skill:api-design" in formatted
        assert "NOT FOUND" in formatted
        assert "Skill not found" in formatted

    def test_format_previous_findings(self, analyzer):
        """Test formatting previous findings."""
        findings = [
            {
                "turn_number": 1,
                "observed_behavior": "AI did X",
                "expected_behavior": "AI should do Y",
            },
            {
                "turn_number": 2,
                "observed_behavior": "AI did A",
                "expected_behavior": "AI should do B",
            },
        ]

        formatted = analyzer._format_previous_findings(findings)

        assert "Turn 1" in formatted
        assert "AI did X" in formatted
        assert "AI should do Y" in formatted
        assert "Turn 2" in formatted

    @patch("drift.core.analyzer.BedrockProvider")
    def test_run_multi_phase_single_phase(self, mock_provider_class, conversation, config):
        """Test multi-phase with single phase (immediate final determination)."""
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = """```json
{
    "resource_requests": [],
    "findings": [
        {
            "turn_number": 1,
            "observed_behavior": "AI did something",
            "expected_behavior": "AI should do something else",
            "learning_type": "test_issue",
            "frequency": "one-time",
            "workflow_element": "documentation",
            "turns_to_resolve": 1,
            "context": "Test context"
        }
    ],
    "final_determination": true
}
```"""
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=config)

        # Inject mock loader into analyzer
        mock_loader = MagicMock()
        analyzer.agent_loaders["claude-code"] = mock_loader

        learnings, error = analyzer._run_multi_phase_analysis(
            conversation,
            "test_multi_phase",
            config.drift_learning_types["test_multi_phase"],
            None,
        )

        assert error is None
        assert len(learnings) == 1
        assert learnings[0].learning_type == "test_multi_phase"  # Uses parent learning_type
        assert learnings[0].observed_behavior == "AI did something"
        assert learnings[0].phases_count == 1
        assert mock_provider.generate.call_count == 1

    @patch("drift.core.analyzer.BedrockProvider")
    def test_run_multi_phase_multiple_phases(self, mock_provider_class, conversation, config):
        """Test multi-phase with multiple phases."""
        # Mock provider - two responses
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.side_effect = [
            """```json
{
    "resource_requests": [
        {
            "resource_type": "command",
            "resource_id": "deploy",
            "reason": "Check deployment"
        }
    ],
    "findings": [],
    "final_determination": false
}
```""",
            """```json
{
    "resource_requests": [],
    "findings": [
        {
            "turn_number": 1,
            "observed_behavior": "AI guessed",
            "expected_behavior": "AI should check /deploy",
            "learning_type": "missing_command_reference",
            "frequency": "one-time",
            "workflow_element": "command",
            "turns_to_resolve": 1,
            "context": "Deployment question"
        }
    ],
    "final_determination": true
}
```""",
        ]
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=config)

        # Inject mock loader
        mock_loader = MagicMock()
        mock_loader.get_resource.return_value = ResourceResponse(
            request=ResourceRequest(
                resource_type="command",
                resource_id="deploy",
                reason="Check deployment",
            ),
            found=True,
            content="# Deploy\nRun ./deploy.sh",
        )
        analyzer.agent_loaders["claude-code"] = mock_loader

        learnings, error = analyzer._run_multi_phase_analysis(
            conversation,
            "test_multi_phase",
            config.drift_learning_types["test_multi_phase"],
            None,
        )

        assert error is None
        assert len(learnings) == 1
        assert learnings[0].learning_type == "test_multi_phase"  # Uses parent learning_type
        assert learnings[0].observed_behavior == "AI guessed"
        assert learnings[0].phases_count == 2
        assert learnings[0].resources_consulted == ["command:deploy"]
        assert mock_provider.generate.call_count == 2

    @patch("drift.core.analyzer.ClaudeCodeLoader")
    @patch("drift.core.analyzer.BedrockProvider")
    def test_run_multi_phase_max_phases_reached(
        self, mock_provider_class, mock_loader_class, conversation, config
    ):
        """Test multi-phase hitting max phases limit."""
        # Mock loader
        mock_loader = MagicMock()
        mock_loader.get_resource.return_value = ResourceResponse(
            request=ResourceRequest(
                resource_type="command",
                resource_id="test",
                reason="Testing",
            ),
            found=True,
            content="Test",
        )
        mock_loader_class.return_value = mock_loader

        # Mock provider - always request more
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = """```json
{
    "resource_requests": [
        {
            "resource_type": "command",
            "resource_id": "test",
            "reason": "Testing"
        }
    ],
    "findings": [],
    "final_determination": false
}
```"""
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=config)

        learnings, error = analyzer._run_multi_phase_analysis(
            conversation,
            "test_multi_phase",
            config.drift_learning_types["test_multi_phase"],
            None,
        )

        # Should stop at max_phases (3)
        assert mock_provider.generate.call_count == 3
        # No learnings since final_determination never reached
        assert len(learnings) == 0

    @patch("drift.core.analyzer.BedrockProvider")
    def test_run_multi_phase_all_resources_missing(self, mock_provider_class, conversation, config):
        """Test multi-phase when all requested resources are missing."""
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.is_available.return_value = True
        mock_provider.generate.return_value = """```json
{
    "resource_requests": [
        {
            "resource_type": "command",
            "resource_id": "deploy",
            "reason": "Check deployment"
        },
        {
            "resource_type": "skill",
            "resource_id": "api-design",
            "reason": "Check API patterns"
        }
    ],
    "findings": [],
    "final_determination": false
}
```"""
        mock_provider_class.return_value = mock_provider

        analyzer = DriftAnalyzer(config=config)

        # Inject mock loader - all resources not found
        mock_loader = MagicMock()
        mock_loader.get_resource.return_value = ResourceResponse(
            request=ResourceRequest(
                resource_type="command",
                resource_id="test",
                reason="Testing",
            ),
            found=False,
            error="Not found",
        )
        analyzer.agent_loaders["claude-code"] = mock_loader

        learnings, error = analyzer._run_multi_phase_analysis(
            conversation,
            "test_multi_phase",
            config.drift_learning_types["test_multi_phase"],
            None,
        )

        # Should create missing resource learnings
        assert error is None
        assert len(learnings) == 2
        # Both will be "missing_command" because mock returns same response
        assert learnings[0].learning_type == "missing_command"
        assert learnings[1].learning_type == "missing_command"
        assert mock_provider.generate.call_count == 1
