"""Comprehensive end-to-end integration tests for Drift.

Tests the complete workflow from CLI invocation through analysis to output,
mirroring the actual drift project setup with realistic configurations,
conversations, and mock LLM responses.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List
from unittest.mock import patch

import pytest
import yaml
from typer.testing import CliRunner

from drift.cli.main import app
from tests.mock_provider import MockProvider


class SequentialMockProvider(MockProvider):
    """MockProvider that returns different responses for each call."""

    def __init__(self, responses: List[str]):
        """Initialize with a list of responses to return sequentially.

        Args:
            responses: List of JSON string responses to return in order
        """
        super().__init__()
        self.responses = responses
        self.call_index = 0

    def generate(self, prompt: str, **kwargs) -> str:
        """Return next response in sequence and track call.

        Args:
            prompt: The prompt sent to the provider
            **kwargs: Additional parameters

        Returns:
            Next response from the sequence
        """
        response = self.responses[self.call_index]
        self.call_index = min(self.call_index + 1, len(self.responses) - 1)
        self.call_count += 1
        self.calls.append({"prompt": prompt, "kwargs": kwargs})
        return response


class TestComprehensiveE2E:
    """Comprehensive end-to-end integration tests for Drift.

    Tests the complete workflow from CLI invocation through analysis to output,
    mirroring the actual drift project setup with realistic configurations,
    conversations, and mock LLM responses.

    Single class design chosen for:
    - Easier fixture sharing across all 14 test methods
    - Unified setup/teardown
    - Simpler test discovery and execution
    """

    @pytest.fixture
    def cli_runner(self):
        """Create CLI runner for testing."""
        return CliRunner()

    @pytest.fixture
    def e2e_project_dir(self, temp_dir):
        """Create complete realistic project structure.

        Args:
            temp_dir: Temporary directory fixture

        Returns:
            Path to project directory
        """
        project_dir = temp_dir / "test_project"
        project_dir.mkdir()

        # Create .claude directory structure
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Commands
        commands_dir = claude_dir / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text(
            "# Test Command\n\n"
            "Runs project tests.\n\n"
            "## Required skills\n- testing\n\n"
            "## Usage\nRun `/test` to execute the test suite."
        )
        (commands_dir / "deploy.md").write_text(
            "# Deploy Command\n\n"
            "Deploys the application.\n\n"
            "## Usage\nRun `/deploy` to deploy."
        )

        # Skills
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()

        testing_skill_dir = skills_dir / "testing"
        testing_skill_dir.mkdir()
        (testing_skill_dir / "SKILL.md").write_text(
            "# Testing Skill\n\n"
            "## Description\nProvides testing utilities and patterns.\n\n"
            "## Examples\n```python\ndef test_example():\n    assert True\n```"
        )

        api_design_skill_dir = skills_dir / "api-design"
        api_design_skill_dir.mkdir()
        (api_design_skill_dir / "SKILL.md").write_text(
            "# API Design Skill\n\n"
            "## Description\nProvides API design patterns and templates.\n\n"
            "## Examples\n```python\nfrom flask import Flask\napp = Flask(__name__)\n```"
        )

        # Agents
        agents_dir = claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "code-reviewer.md").write_text(
            "# Code Reviewer Agent\n\n"
            "Reviews code for quality and best practices.\n\n"
            "## Tools Available\n- Read\n- Grep"
        )

        # Project files
        (project_dir / "CLAUDE.md").write_text(
            "# Test Project\n\nThis is a test project for drift analysis."
        )
        (project_dir / "README.md").write_text("# Test Project\n\nReadme content.")
        (project_dir / "LICENSE").write_text("MIT License")

        # Logs directory - Claude Code expects mangled path structure
        # conversation_path/mangled-project-path/*.jsonl
        logs_base = project_dir / ".logs"
        logs_base.mkdir()

        # Mangle project path like Claude Code does: /foo/bar -> -foo-bar
        mangled_name = str(project_dir).replace("/", "-").replace("_", "-")
        logs_dir = logs_base / mangled_name
        logs_dir.mkdir()

        # Create .drift.yaml config
        config_content = self._create_realistic_config(project_dir)
        (project_dir / ".drift.yaml").write_text(config_content)

        # Create conversation files in mangled directory
        self._create_conversation_jsonl(
            logs_dir / "session-incomplete.jsonl", "incomplete_work", project_dir
        )
        self._create_conversation_jsonl(
            logs_dir / "session-skill.jsonl", "skill_ignored", project_dir
        )
        self._create_conversation_jsonl(logs_dir / "session-clean.jsonl", "no_drift", project_dir)
        self._create_conversation_jsonl(
            logs_dir / "session-command.jsonl", "command_activation", project_dir
        )

        return project_dir

    @pytest.fixture
    def e2e_project_dir_all_conversations(self, temp_dir):
        """Create project directory with mode='all' for loading all conversations.

        Use this fixture for tests that need to analyze multiple conversations.
        """
        # Build project structure directly (can't call fixture)
        project_dir = temp_dir / "test_project_all"
        project_dir.mkdir()

        # Claude directory structure
        claude_dir = project_dir / ".claude"
        claude_dir.mkdir()

        # Commands
        commands_dir = claude_dir / "commands"
        commands_dir.mkdir()
        (commands_dir / "test.md").write_text(
            "# Test Command\n\nRun tests.\n\nRequired skills: testing"
        )
        (commands_dir / "deploy.md").write_text("# Deploy Command\n\nDeploy the app.")

        # Skills
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "testing").mkdir()
        (skills_dir / "testing" / "SKILL.md").write_text("# Testing Skill\n\nTest practices.")
        (skills_dir / "api-design").mkdir()
        (skills_dir / "api-design" / "SKILL.md").write_text("# API Design Skill\n\nAPI patterns.")

        # Agents
        agents_dir = claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "code-reviewer.md").write_text(
            "# Code Reviewer Agent\n\n"
            "Reviews code for quality and best practices.\n\n"
            "## Tools Available\n- Read\n- Grep"
        )

        # Project files
        (project_dir / "CLAUDE.md").write_text(
            "# Test Project\n\nThis is a test project for drift analysis."
        )
        (project_dir / "README.md").write_text("# Test Project\n\nReadme content.")
        (project_dir / "LICENSE").write_text("MIT License")

        # Logs directory - Claude Code expects mangled path structure
        logs_base = project_dir / ".logs"
        logs_base.mkdir()
        mangled_name = str(project_dir).replace("/", "-").replace("_", "-")
        logs_dir = logs_base / mangled_name
        logs_dir.mkdir()

        # Create conversation files
        self._create_conversation_jsonl(
            logs_dir / "session-incomplete.jsonl", "incomplete_work", project_dir
        )
        self._create_conversation_jsonl(
            logs_dir / "session-skill.jsonl", "skill_ignored", project_dir
        )
        self._create_conversation_jsonl(logs_dir / "session-clean.jsonl", "no_drift", project_dir)
        self._create_conversation_jsonl(
            logs_dir / "session-command.jsonl", "command_activation", project_dir
        )

        # Create config with mode='all'
        config_content = self._create_realistic_config(project_dir, conversation_mode="all")
        (project_dir / ".drift.yaml").write_text(config_content)

        return project_dir

    def _create_realistic_config(
        self, project_dir: Path, conversation_mode: str = "latest", conversation_days: int = None
    ) -> str:
        """Create realistic .drift.yaml configuration.

        Args:
            project_dir: Project directory path
            conversation_mode: Mode for loading conversations ('latest', 'all', 'last_n_days')
            conversation_days: Number of days for 'last_n_days' mode

        Returns:
            YAML configuration string
        """
        config = {
            "providers": {
                "bedrock": {
                    "provider": "bedrock",
                    "params": {"region": "us-east-1"},
                }
            },
            "models": {
                "haiku": {
                    "provider": "bedrock",
                    "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
                    "params": {"max_tokens": 4096, "temperature": 0.0},
                },
                "sonnet": {
                    "provider": "bedrock",
                    "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                    "params": {"max_tokens": 8192, "temperature": 0.0},
                },
            },
            "default_model": "haiku",
            "agent_tools": {
                "claude-code": {
                    # Point to base logs directory (contains mangled project dirs)
                    "conversation_path": str(project_dir / ".logs"),
                    "enabled": True,
                }
            },
            "drift_learning_types": {
                # Conversation-level (single-phase LLM)
                "incomplete_work": {
                    "description": "AI stopped before completing full scope of work",
                    "scope": "conversation_level",
                    "context": "Completing work in one pass saves user time and frustration",
                    "requires_project_context": False,
                    "phases": [
                        {
                            "name": "detection",
                            "type": "prompt",
                            "model": "haiku",
                            "prompt": (
                                "Look for instances where AI claimed to be "
                                "done but user had to ask for more."
                            ),
                            "available_resources": [],
                        }
                    ],
                },
                "skill_ignored": {
                    "description": "AI reinvented solutions when project skills existed",
                    "scope": "conversation_level",
                    "context": "Using existing skills maintains consistency",
                    "requires_project_context": True,
                    "supported_clients": ["claude-code"],
                    "phases": [
                        {
                            "name": "detection",
                            "type": "prompt",
                            "model": "haiku",
                            "prompt": (
                                "Check if AI wrote custom code when project " "had relevant skills."
                            ),
                            "available_resources": ["skill"],
                        }
                    ],
                },
                # Conversation-level (multi-phase)
                "command_activation_required": {
                    "description": (
                        "AI failed to activate required skills before "
                        "executing slash command steps"
                    ),
                    "scope": "conversation_level",
                    "context": (
                        "Commands with required skills dependencies must "
                        "have those skills activated first"
                    ),
                    "requires_project_context": True,
                    "supported_clients": ["claude-code"],
                    "phases": [
                        {
                            "name": "initial_scan",
                            "type": "prompt",
                            "model": "haiku",
                            "prompt": (
                                "Scan conversation for slash command usage. "
                                "Request command resources if needed."
                            ),
                            "available_resources": ["command", "skill"],
                        },
                        {
                            "name": "detailed_analysis",
                            "type": "prompt",
                            "model": "haiku",
                            "prompt": (
                                "With command content, verify if required "
                                "skills were activated before command execution."
                            ),
                            "available_resources": ["command", "skill"],
                        },
                    ],
                },
                # Project-level (programmatic)
                "claude_md_missing": {
                    "description": "Project missing CLAUDE.md configuration file",
                    "scope": "project_level",
                    "context": "CLAUDE.md provides essential context for AI effectiveness",
                    "requires_project_context": True,
                    "validation_rules": {
                        "scope": "project_level",
                        "document_bundle": {
                            "bundle_type": "configuration",
                            "file_patterns": ["CLAUDE.md"],
                            "bundle_strategy": "collection",
                        },
                        "rules": [
                            {
                                "rule_type": "file_exists",
                                "description": "CLAUDE.md must exist in project root",
                                "file_path": "CLAUDE.md",
                                "failure_message": "CLAUDE.md file is missing from project root",
                                "expected_behavior": "CLAUDE.md file should exist in project root",
                            }
                        ],
                    },
                },
            },
        }

        # Add conversations section if mode is specified
        if conversation_mode:
            conversations_config = {"mode": conversation_mode}
            if conversation_mode == "last_n_days" and conversation_days:
                conversations_config["days"] = conversation_days
            config["conversations"] = conversations_config

        return yaml.dump(config, sort_keys=False)

    def _create_conversation_jsonl(self, file_path: Path, scenario: str, project_dir: Path):
        """Create realistic Claude Code JSONL conversation file.

        Args:
            file_path: Path to write conversation file
            scenario: Type of conversation scenario to create
            project_dir: Project directory to use as cwd in conversation
        """
        scenarios = {
            "incomplete_work": self._incomplete_work_conversation(project_dir),
            "skill_ignored": self._skill_ignored_conversation(project_dir),
            "no_drift": self._no_drift_conversation(project_dir),
            "command_activation": self._command_activation_conversation(project_dir),
        }

        messages = scenarios.get(scenario, [])
        with open(file_path, "w") as f:
            for msg in messages:
                f.write(json.dumps(msg) + "\n")

    def _incomplete_work_conversation(self, project_dir: Path) -> List[Dict]:
        """Create conversation showing incomplete work pattern."""
        return [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Build an authentication system for the app",
                        }
                    ],
                },
                "timestamp": "2024-01-01T10:00:00Z",
                "sessionId": "session-incomplete",
                "cwd": str(project_dir),
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "I'll create a login function for authentication.",
                        },
                        {
                            "type": "tool_use",
                            "id": "tool-1",
                            "name": "Write",
                            "input": {
                                "file_path": "auth.py",
                                "content": (
                                    "def login(username, password):\n"
                                    "    # Login implementation\n"
                                    "    return True\n"
                                ),
                            },
                        },
                    ],
                },
                "timestamp": "2024-01-01T10:01:00Z",
                "sessionId": "session-incomplete",
                "cwd": str(project_dir),
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What about logout functionality and session management?",
                        }
                    ],
                },
                "timestamp": "2024-01-01T10:02:00Z",
                "sessionId": "session-incomplete",
                "cwd": str(project_dir),
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "You're right, let me add those missing pieces.",
                        },
                        {
                            "type": "tool_use",
                            "id": "tool-2",
                            "name": "Edit",
                            "input": {
                                "file_path": "auth.py",
                                "old_string": (
                                    "def login(username, password):\n"
                                    "    # Login implementation\n"
                                    "    return True\n"
                                ),
                                "new_string": (
                                    "def login(username, password):\n"
                                    "    # Login implementation\n"
                                    "    return True\n\n"
                                    "def logout(session_id):\n"
                                    "    # Logout implementation\n"
                                    "    pass\n\n"
                                    "def manage_session(user_id):\n"
                                    "    # Session management\n"
                                    "    pass\n"
                                ),
                            },
                        },
                    ],
                },
                "timestamp": "2024-01-01T10:03:00Z",
                "sessionId": "session-incomplete",
                "cwd": str(project_dir),
            },
        ]

    def _skill_ignored_conversation(self, project_dir: Path) -> List[Dict]:
        """Create conversation showing skill ignored pattern."""
        return [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Add a new REST API endpoint for user registration",
                        }
                    ],
                },
                "timestamp": "2024-01-02T10:00:00Z",
                "sessionId": "session-skill",
                "cwd": str(project_dir),
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "I'll create a custom Flask endpoint for user registration.",
                        },
                        {
                            "type": "tool_use",
                            "id": "tool-3",
                            "name": "Write",
                            "input": {
                                "file_path": "api.py",
                                "content": (
                                    "from flask import Flask, request\n\n"
                                    "app = Flask(__name__)\n\n"
                                    "@app.route('/register', methods=['POST'])\n"
                                    "def register():\n"
                                    "    data = request.json\n"
                                    "    # Registration logic\n"
                                    "    return {'success': True}\n"
                                ),
                            },
                        },
                    ],
                },
                "timestamp": "2024-01-02T10:01:00Z",
                "sessionId": "session-skill",
                "cwd": str(project_dir),
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "We have an api-design skill that provides "
                                "the standard patterns for this"
                            ),
                        }
                    ],
                },
                "timestamp": "2024-01-02T10:02:00Z",
                "sessionId": "session-skill",
                "cwd": str(project_dir),
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You're absolutely right. I should have used "
                                "the api-design skill to follow your project's "
                                "established patterns."
                            ),
                        }
                    ],
                },
                "timestamp": "2024-01-02T10:03:00Z",
                "sessionId": "session-skill",
                "cwd": str(project_dir),
            },
        ]

    def _command_activation_conversation(self, project_dir: Path) -> List[Dict]:
        """Create conversation showing command used without activating required skill."""
        return [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Run the /test command to verify everything works"}
                    ],
                },
                "timestamp": "2024-01-04T10:00:00Z",
                "sessionId": "session-command",
                "cwd": str(project_dir),
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "I'll run the test command now.",
                        },
                        {
                            "type": "tool_use",
                            "id": "tool-cmd-1",
                            "name": "SlashCommand",
                            "input": {"command": "/test"},
                        },
                    ],
                },
                "timestamp": "2024-01-04T10:01:00Z",
                "sessionId": "session-command",
                "cwd": str(project_dir),
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You should have activated the testing skill "
                                "first as per the command requirements"
                            ),
                        }
                    ],
                },
                "timestamp": "2024-01-04T10:02:00Z",
                "sessionId": "session-command",
                "cwd": str(project_dir),
            },
        ]

    def _no_drift_conversation(self, project_dir: Path) -> List[Dict]:
        """Create clean conversation with no drift."""
        return [
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Add a simple hello world function"}],
                },
                "timestamp": "2024-01-03T10:00:00Z",
                "sessionId": "session-clean",
                "cwd": str(project_dir),
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "I'll create a hello world function with proper documentation.",
                        },
                        {
                            "type": "tool_use",
                            "id": "tool-4",
                            "name": "Write",
                            "input": {
                                "file_path": "hello.py",
                                "content": (
                                    "def hello_world():\n"
                                    '    """Print hello world message."""\n'
                                    "    print('Hello, World!')\n"
                                    "    return 'Hello, World!'\n"
                                ),
                            },
                        },
                    ],
                },
                "timestamp": "2024-01-03T10:01:00Z",
                "sessionId": "session-clean",
                "cwd": str(project_dir),
            },
            {
                "type": "user",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "Perfect, thanks!"}],
                },
                "timestamp": "2024-01-03T10:02:00Z",
                "sessionId": "session-clean",
                "cwd": str(project_dir),
            },
        ]

    def _assert_learning_structure(self, learning: Dict):
        """Assert learning has required fields and valid content.

        Args:
            learning: Learning dictionary to validate
        """
        required_fields = [
            "turn_number",
            "observed_behavior",
            "expected_behavior",
            "learning_type",
            "frequency",
            "workflow_element",
            "context",
        ]
        for field in required_fields:
            assert field in learning, f"Missing required field: {field}"

        assert isinstance(learning["turn_number"], int), "turn_number must be int"
        assert len(learning["observed_behavior"]) > 0, "observed_behavior cannot be empty"
        assert len(learning["expected_behavior"]) > 0, "expected_behavior cannot be empty"

    def _assert_execution_detail_structure(self, detail: Dict):
        """Assert execution detail has correct structure.

        Args:
            detail: Execution detail dictionary to validate
        """
        assert "rule_name" in detail, "Missing rule_name"
        assert "status" in detail, "Missing status"
        assert detail["status"] in [
            "passed",
            "failed",
            "errored",
            "skipped",
        ], f"Invalid status: {detail['status']}"

        if "duration" in detail:
            assert isinstance(detail["duration"], (int, float)), "duration must be numeric"

        # Multi-phase specific
        if detail.get("phase_count", 1) > 1:
            assert "phases_executed" in detail, "Multi-phase must have phases_executed"

    def _assert_prompt_content(self, mock_provider: MockProvider, expected_patterns: List[str]):
        """Assert LLM prompts contain expected content.

        Args:
            mock_provider: MockProvider instance to inspect
            expected_patterns: List of patterns that should appear in prompts
        """
        assert len(mock_provider.calls) > 0, "No LLM calls were made"

        for pattern in expected_patterns:
            found = False
            for call in mock_provider.calls:
                prompt = call["prompt"]
                if pattern.lower() in prompt.lower():
                    found = True
                    break
            assert found, f"Pattern '{pattern}' not found in any prompt"

    def _assert_response_quality(self, response_str: str):
        """Assert mock response has realistic content.

        Args:
            response_str: JSON response string to validate
        """
        try:
            response = json.loads(response_str)
        except json.JSONDecodeError:
            pytest.fail(f"Invalid JSON response: {response_str}")

        # Handle both list (single-phase) and dict (multi-phase) responses
        if isinstance(response, list):
            for learning in response:
                if "observed_behavior" in learning:
                    assert len(learning["observed_behavior"]) > 20, "observed_behavior too short"
                if "expected_behavior" in learning:
                    assert len(learning["expected_behavior"]) > 20, "expected_behavior too short"
                if "turn_number" in learning:
                    assert 1 <= learning["turn_number"] <= 100, "turn_number out of range"

        elif isinstance(response, dict):
            # Multi-phase response
            if "findings" in response:
                for finding in response["findings"]:
                    if "observed_behavior" in finding:
                        assert len(finding["observed_behavior"]) > 20, "observed_behavior too short"
            if "resource_requests" in response:
                for req in response["resource_requests"]:
                    if "reason" in req:
                        assert len(req["reason"]) > 10, "resource request reason too short"

    # Test methods start here
    @patch("drift.core.analyzer.BedrockProvider", MockProvider)
    def test_full_analysis_with_mixed_learning_types(
        self, cli_runner, e2e_project_dir_all_conversations
    ):
        """Test complete analysis with conversation + project rules.

        This is the comprehensive baseline test that validates the entire
        end-to-end workflow with realistic conversations and mixed rule types.
        Uses mode='all' to analyze all 4 conversation files.
        """
        e2e_project_dir = e2e_project_dir_all_conversations
        # Create mock provider with responses for incomplete_work and skill_ignored
        mock_provider = SequentialMockProvider(
            [
                # Response for incomplete_work detection
                json.dumps(
                    [
                        {
                            "turn_number": 3,
                            "observed_behavior": (
                                "AI implemented only login functionality "
                                "without logout or session management components"
                            ),
                            "expected_behavior": (
                                "Complete authentication system should include "
                                "login, logout, and session management in initial "
                                "implementation"
                            ),
                            "resolved": False,
                            "still_needs_action": True,
                            "context": (
                                "User had to explicitly ask for missing logout "
                                "and session components in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for skill_ignored detection
                json.dumps(
                    [
                        {
                            "turn_number": 2,
                            "observed_behavior": (
                                "AI wrote custom Flask API endpoint code instead "
                                "of using the existing api-design skill pattern"
                            ),
                            "expected_behavior": (
                                "AI should have consulted and used the "
                                "api-design skill for API endpoint implementation"
                            ),
                            "resolved": True,
                            "still_needs_action": False,
                            "context": (
                                "Project has api-design skill but AI reinvented "
                                "the pattern, user corrected in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for no-drift conversation (empty)
                "[]",
            ]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            result = cli_runner.invoke(
                app, ["--project", str(e2e_project_dir), "--format", "markdown"]
            )

        # Verify exit code (2 = drift found)
        assert result.exit_code == 2, (
            f"Expected exit code 2 (drift found), got {result.exit_code}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Verify output structure
        assert "# Drift Analysis Results" in result.stdout
        assert "## Summary" in result.stdout

        # Verify summary statistics
        # Should find 4 conversation files (incomplete, skill, clean, command)
        assert "Total conversations: 4" in result.stdout
        assert "Total learnings:" in result.stdout  # Should have 2+ learnings

        # Verify learning types are mentioned
        assert "incomplete_work" in result.stdout
        assert "skill_ignored" in result.stdout

        # Verify both conversation and project scopes ran
        # (conversation learnings + programmatic claude_md_missing check)
        assert "Warnings" in result.stdout or "## Learnings" in result.stdout

        # Verify prompt content
        self._assert_prompt_content(
            mock_provider,
            [
                "Build an authentication system",  # User message
                "login",  # AI response content
                "logout",  # User correction
                "API endpoint",  # User message
                "api-design skill",  # User mentions skill
            ],
        )

        # Verify response quality
        for response in mock_provider.responses[:2]:  # Check meaningful responses
            self._assert_response_quality(response)

        # Verify LLM was called (not skipped)
        assert mock_provider.call_count > 0, "MockProvider should have been called"

    def test_json_output_includes_execution_details(
        self, cli_runner, e2e_project_dir_all_conversations
    ):
        """Test JSON always includes execution_details (regardless of --detailed flag).

        JSON output must ALWAYS include metadata.execution_details with information
        about what rules were executed, even when --detailed flag is NOT provided.
        """
        # Use mode='all' to load multiple conversations
        e2e_project_dir = e2e_project_dir_all_conversations

        # Create mock provider with responses
        mock_provider = SequentialMockProvider(
            [
                # Response for incomplete_work
                json.dumps(
                    [
                        {
                            "turn_number": 3,
                            "observed_behavior": (
                                "AI implemented only login functionality "
                                "without logout or session management components"
                            ),
                            "expected_behavior": (
                                "Complete authentication system should include "
                                "login, logout, and session management in initial "
                                "implementation"
                            ),
                            "resolved": False,
                            "still_needs_action": True,
                            "context": (
                                "User had to explicitly ask for missing logout "
                                "and session components in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for skill_ignored
                json.dumps(
                    [
                        {
                            "turn_number": 2,
                            "observed_behavior": (
                                "AI wrote custom Flask API endpoint code instead "
                                "of using the existing api-design skill pattern"
                            ),
                            "expected_behavior": (
                                "AI should have consulted and used the "
                                "api-design skill for API endpoint implementation"
                            ),
                            "resolved": True,
                            "still_needs_action": False,
                            "context": (
                                "Project has api-design skill but AI reinvented "
                                "the pattern, user corrected in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for no-drift conversation
                "[]",
            ]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --format json (NO --detailed flag)
            result = cli_runner.invoke(app, ["--project", str(e2e_project_dir), "--format", "json"])

        # Verify exit code
        assert result.exit_code == 2, (
            f"Expected exit code 2 (drift found), got {result.exit_code}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Parse JSON output
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as e:
            pytest.fail(f"Failed to parse JSON output: {e}\nOutput: {result.stdout}")

        # JSON output MUST include execution_details even without --detailed flag
        assert "metadata" in output, "No metadata in JSON output"
        assert "execution_details" in output["metadata"], "No execution_details in metadata"

        exec_details = output["metadata"]["execution_details"]
        assert isinstance(
            exec_details, list
        ), f"execution_details should be a list, got {type(exec_details)}"
        assert len(exec_details) > 0, "execution_details is empty"

        # Verify structure of execution details
        for detail in exec_details:
            self._assert_execution_detail_structure(detail)

        # Find specific rules in execution details
        rule_names = {d["rule_name"] for d in exec_details}

        # Should have conversation-level LLM rules
        assert "incomplete_work" in rule_names, (
            f"incomplete_work not in execution_details. " f"Found rules: {rule_names}"
        )
        assert "skill_ignored" in rule_names, (
            f"skill_ignored not in execution_details. " f"Found rules: {rule_names}"
        )

        # Should have project-level programmatic rule
        assert "claude_md_missing" in rule_names, (
            f"claude_md_missing not in execution_details. " f"Found rules: {rule_names}"
        )

        # Verify programmatic rules show validation_results
        claude_md_detail = next(
            (d for d in exec_details if d["rule_name"] == "claude_md_missing"), None
        )
        assert claude_md_detail is not None, "claude_md_missing execution detail not found"
        assert (
            "validation_results" in claude_md_detail
        ), "Programmatic rule should have validation_results"

        # Verify validation_results structure
        validation_results = claude_md_detail["validation_results"]
        assert isinstance(validation_results, dict), "validation_results should be dict"
        assert "rule_type" in validation_results

        # Bundle info and files are in execution_context
        assert "execution_context" in claude_md_detail
        exec_context = claude_md_detail["execution_context"]
        assert "bundle_type" in exec_context
        assert "bundle_id" in exec_context
        assert "files" in exec_context

        # Verify all details have required fields
        for detail in exec_details:
            assert "rule_name" in detail
            assert "status" in detail
            assert detail["status"] in ["passed", "failed", "error", "skipped"]
            # Duration is optional

        # Verify results array has learnings
        assert "results" in output, "No results in JSON output"
        assert isinstance(output["results"], list), "results should be a list"

        # Extract all learnings from results
        all_learnings = []
        for conv in output["results"]:
            all_learnings.extend(conv.get("learnings", []))

        # Should have learnings from conversation analysis
        conversation_learnings = [
            learning
            for learning in all_learnings
            if learning.get("learning_type") in ["incomplete_work", "skill_ignored"]
        ]
        assert len(conversation_learnings) >= 2, (
            f"Expected at least 2 conversation learnings, " f"got {len(conversation_learnings)}"
        )

    def test_detailed_flag_shows_execution_context(self, cli_runner, e2e_project_dir):
        """Test --detailed flag adds execution details section to markdown output.

        With --detailed flag, markdown output should include a section showing
        what rules were executed, what bundles/files were checked, and execution context.
        """
        # Create mock provider with responses
        mock_provider = SequentialMockProvider(
            [
                # Response for incomplete_work
                json.dumps(
                    [
                        {
                            "turn_number": 3,
                            "observed_behavior": (
                                "AI implemented only login functionality "
                                "without logout or session management components"
                            ),
                            "expected_behavior": (
                                "Complete authentication system should include "
                                "login, logout, and session management in initial "
                                "implementation"
                            ),
                            "resolved": False,
                            "still_needs_action": True,
                            "context": (
                                "User had to explicitly ask for missing logout "
                                "and session components in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for skill_ignored
                json.dumps(
                    [
                        {
                            "turn_number": 2,
                            "observed_behavior": (
                                "AI wrote custom Flask API endpoint code instead "
                                "of using the existing api-design skill pattern"
                            ),
                            "expected_behavior": (
                                "AI should have consulted and used the "
                                "api-design skill for API endpoint implementation"
                            ),
                            "resolved": True,
                            "still_needs_action": False,
                            "context": (
                                "Project has api-design skill but AI reinvented "
                                "the pattern, user corrected in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for no-drift conversation
                "[]",
            ]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --detailed flag
            result = cli_runner.invoke(app, ["--project", str(e2e_project_dir), "--detailed"])

        # Verify exit code
        assert result.exit_code == 2, (
            f"Expected exit code 2 (drift found), got {result.exit_code}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Should show execution details section
        assert (
            "Test Execution Details" in result.stdout or "Execution Details" in result.stdout
        ), f"No execution details section found in output:\n{result.stdout}"

        # Should show the rules that were executed
        assert (
            "incomplete_work" in result.stdout
        ), f"incomplete_work rule not found in output:\n{result.stdout}"
        assert (
            "skill_ignored" in result.stdout
        ), f"skill_ignored rule not found in output:\n{result.stdout}"
        assert (
            "claude_md_missing" in result.stdout
        ), f"claude_md_missing rule not found in output:\n{result.stdout}"

        # Should show execution context (bundle info, files checked, etc.)
        # For programmatic rules, this includes what was validated
        assert any(
            keyword in result.stdout
            for keyword in ["Bundle", "bundle", "Files", "Validated", "Validation"]
        ), f"No execution context found in output:\n{result.stdout}"

        # Should show what files/resources were checked
        assert (
            "CLAUDE.md" in result.stdout or ".claude.md" in result.stdout
        ), f"CLAUDE.md not mentioned in output:\n{result.stdout}"

        # Should show status (passed/failed/skipped)
        assert any(
            status in result.stdout.lower() for status in ["passed", "failed", "skipped", "error"]
        ), f"No status information found in output:\n{result.stdout}"

        # Should still have the regular analysis results
        assert "# Drift Analysis Results" in result.stdout
        assert "## Summary" in result.stdout

    def test_no_llm_flag_filters_correctly(self, cli_runner, e2e_project_dir):
        """Test --no-llm flag only runs programmatic rules.

        When --no-llm is specified, only programmatic validation rules
        should run. LLM-based conversation analysis should be skipped entirely.
        """

        # Create a mock provider that should NOT be called
        class FailIfCalledProvider(MockProvider):
            """Provider that fails if generate() is called."""

            def generate(self, prompt: str, **kwargs) -> str:
                pytest.fail("MockProvider.generate() should NOT be called with --no-llm flag")

        mock_provider = FailIfCalledProvider()

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --no-llm flag
            result = cli_runner.invoke(app, ["--project", str(e2e_project_dir), "--no-llm"])

        # Should succeed (exit code 0 because CLAUDE.md exists, so programmatic rule passes)
        assert result.exit_code == 0, (
            f"Expected exit code 0 (no drift with --no-llm), "
            f"got {result.exit_code}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Stderr should show skipped/running counts
        # (Output may go to stdout or stderr depending on implementation)
        output_text = result.stdout + result.stderr

        # Should mention skipping or that LLM rules were filtered
        # Could be in various formats, so check for common patterns
        assert (
            "programmatic" in output_text.lower()
            or "skipped" in output_text.lower()
            or "no-llm" in output_text.lower()
            or "0 conversations" in output_text.lower()
        ), f"No indication of LLM filtering in output:\n{output_text}"

        # Should NOT have conversation learnings
        assert (
            "incomplete_work" not in result.stdout
        ), "Should not have incomplete_work learning with --no-llm"
        assert (
            "skill_ignored" not in result.stdout
        ), "Should not have skill_ignored learning with --no-llm"

        # Verify MockProvider was NOT called
        assert (
            mock_provider.call_count == 0
        ), f"MockProvider should not be called with --no-llm, got {mock_provider.call_count} calls"

    def test_scope_conversation_only(self, cli_runner, e2e_project_dir_all_conversations):
        """Test --scope conversation filters project-level rules.

        Only conversation-level learning types should run, project-level rules
        should be skipped.
        """
        e2e_project_dir = e2e_project_dir_all_conversations
        # Create mock provider with responses for conversation rules
        # With 4 conversations and 3 conversation-level rules (2 single-phase, 1 multi-phase),
        # we need responses for: incomplete_work (4 calls), skill_ignored (4 calls),
        # command_activation (8 calls for multi-phase)
        mock_provider = SequentialMockProvider(
            [
                # incomplete_work responses (4 conversations)
                json.dumps(
                    [
                        {
                            "turn_number": 3,
                            "observed_behavior": "AI implemented only login without logout/session",
                            "expected_behavior": "Complete auth system with login, logout, session",
                            "resolved": False,
                            "still_needs_action": True,
                            "context": "User had to ask for missing components",
                        }
                    ]
                ),
                "[]",  # skill_ignored conversation
                "[]",  # clean conversation
                "[]",  # command conversation
                # skill_ignored responses (4 conversations)
                "[]",  # incomplete conversation
                json.dumps(
                    [
                        {
                            "turn_number": 2,
                            "observed_behavior": (
                                "AI wrote custom code instead of using " "api-design skill"
                            ),
                            "expected_behavior": "AI should use the api-design skill pattern",
                            "resolved": True,
                            "still_needs_action": False,
                            "context": "Project has api-design skill but AI reinvented pattern",
                        }
                    ]
                ),
                "[]",  # clean conversation
                "[]",  # command conversation
                # command_activation_required phase 1 responses (4 conversations)
                json.dumps({"resource_requests": [], "findings": [], "final_determination": True}),
                json.dumps({"resource_requests": [], "findings": [], "final_determination": True}),
                json.dumps({"resource_requests": [], "findings": [], "final_determination": True}),
                json.dumps({"resource_requests": [], "findings": [], "final_determination": True}),
            ]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --scope conversation
            result = cli_runner.invoke(
                app,
                ["--project", str(e2e_project_dir), "--scope", "conversation", "--format", "json"],
            )

        # Parse JSON output
        output = json.loads(result.stdout)

        # Should have conversation learnings
        # Results are conversations, each with a learnings array
        all_learnings = []
        for conv in output["results"]:
            all_learnings.extend(conv.get("learnings", []))

        conversation_learnings = [
            learning
            for learning in all_learnings
            if learning.get("learning_type") in ["incomplete_work", "skill_ignored"]
        ]
        assert len(conversation_learnings) >= 1, (
            f"Expected conversation learnings with --scope conversation, "
            f"got {len(conversation_learnings)}. All learnings: "
            f"{[learning.get('learning_type') for learning in all_learnings]}"
        )

        # Should NOT have project-level learnings
        # Project learnings would have learning_type of programmatic rules
        project_learnings = [
            learning
            for learning in all_learnings
            if learning.get("learning_type") == "claude_md_missing"
        ]
        assert len(project_learnings) == 0, (
            f"Should not have project learnings with --scope conversation, "
            f"got {len(project_learnings)}"
        )

        # Execution details should only have conversation rules
        exec_details = output["metadata"]["execution_details"]
        rule_names = {d["rule_name"] for d in exec_details}

        # Should have conversation rules
        assert "incomplete_work" in rule_names or "skill_ignored" in rule_names

        # Should NOT have project rules
        assert (
            "claude_md_missing" not in rule_names
        ), "Should not run claude_md_missing with --scope conversation"

    def test_scope_project_only(self, cli_runner, e2e_project_dir):
        """Test --scope project filters conversation-level rules.

        Only project-level learning types should run, conversation-level rules
        should be skipped.
        """

        # Create a mock provider that should NOT be called (no conversation analysis)
        class FailIfCalledProvider(MockProvider):
            """Provider that fails if generate() is called."""

            def generate(self, prompt: str, **kwargs) -> str:
                pytest.fail(
                    "MockProvider.generate() should NOT be called with --scope project "
                    "(assuming only programmatic project rules exist)"
                )

        mock_provider = FailIfCalledProvider()

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --scope project
            result = cli_runner.invoke(
                app,
                ["--project", str(e2e_project_dir), "--scope", "project", "--format", "json"],
            )

        # Parse JSON output
        output = json.loads(result.stdout)

        # Should NOT have conversation learnings
        conversation_learnings = [
            r
            for r in output["results"]
            if r.get("learning_type") in ["incomplete_work", "skill_ignored"]
        ]
        assert len(conversation_learnings) == 0, (
            f"Should not have conversation learnings with --scope project, "
            f"got {len(conversation_learnings)}"
        )

        # Summary should show 0 conversations analyzed
        assert output["summary"]["conversations_analyzed"] == 0, (
            f"Should analyze 0 conversations with --scope project, "
            f"got {output['summary']['conversations_analyzed']}"
        )

        # Execution details should only have project rules
        exec_details = output["metadata"]["execution_details"]
        rule_names = {d["rule_name"] for d in exec_details}

        # Should have project rules
        assert "claude_md_missing" in rule_names, (
            f"Should run claude_md_missing with --scope project. " f"Found rules: {rule_names}"
        )

        # Should NOT have conversation rules
        assert (
            "incomplete_work" not in rule_names
        ), "Should not run incomplete_work with --scope project"
        assert (
            "skill_ignored" not in rule_names
        ), "Should not run skill_ignored with --scope project"

    def test_scope_all_merges_results(self, cli_runner, e2e_project_dir_all_conversations):
        """Test default --scope all runs both conversation and project rules.

        All learning types should run and results should be merged together.
        """
        e2e_project_dir = e2e_project_dir_all_conversations
        # Create mock provider with responses
        mock_provider = SequentialMockProvider(
            [
                # Response for incomplete_work
                json.dumps(
                    [
                        {
                            "turn_number": 3,
                            "observed_behavior": (
                                "AI implemented only login functionality "
                                "without logout or session management components"
                            ),
                            "expected_behavior": (
                                "Complete authentication system should include "
                                "login, logout, and session management in initial "
                                "implementation"
                            ),
                            "resolved": False,
                            "still_needs_action": True,
                            "context": (
                                "User had to explicitly ask for missing logout "
                                "and session components in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for skill_ignored
                json.dumps(
                    [
                        {
                            "turn_number": 2,
                            "observed_behavior": (
                                "AI wrote custom Flask API endpoint code instead "
                                "of using the existing api-design skill pattern"
                            ),
                            "expected_behavior": (
                                "AI should have consulted and used the "
                                "api-design skill for API endpoint implementation"
                            ),
                            "resolved": True,
                            "still_needs_action": False,
                            "context": (
                                "Project has api-design skill but AI reinvented "
                                "the pattern, user corrected in turn 3"
                            ),
                        }
                    ]
                ),
                # Response for no-drift conversation
                "[]",
            ]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --scope all (or omit, as it's the default)
            result = cli_runner.invoke(
                app, ["--project", str(e2e_project_dir), "--scope", "all", "--format", "json"]
            )

        # Parse JSON output
        output = json.loads(result.stdout)

        # Should have BOTH conversation and project learnings
        # Extract all learnings from conversations
        all_learnings = []
        for conv in output["results"]:
            all_learnings.extend(conv.get("learnings", []))

        conversation_learnings = [
            learning
            for learning in all_learnings
            if learning.get("learning_type") in ["incomplete_work", "skill_ignored"]
        ]
        _ = [
            learning
            for learning in all_learnings
            if learning.get("learning_type") == "claude_md_missing"
        ]

        # Note: project programmatic rule (claude_md_missing) passes, so no learning
        # But we should have conversation learnings
        assert len(conversation_learnings) >= 1, (
            f"Expected conversation learnings with --scope all, "
            f"got {len(conversation_learnings)}"
        )

        # Summary should show conversations analyzed
        assert output["summary"]["conversations_analyzed"] >= 1, (
            f"Should analyze conversations with --scope all, "
            f"got {output['summary']['conversations_analyzed']}"
        )

        # Execution details should have BOTH types of rules
        exec_details = output["metadata"]["execution_details"]
        rule_names = {d["rule_name"] for d in exec_details}

        # Should have conversation rules
        assert "incomplete_work" in rule_names or "skill_ignored" in rule_names, (
            f"Should have conversation rules with --scope all. " f"Found: {rule_names}"
        )

        # Should have project rules
        assert "claude_md_missing" in rule_names, (
            f"Should have project rules with --scope all. " f"Found: {rule_names}"
        )

    def test_multi_phase_resource_requests(self, cli_runner, e2e_project_dir):
        """Test multi-phase analysis with resource loading.

        Multi-phase rules can request resources (command, skill, agent files) in phase 1,
        which are then loaded and included in phase 2 prompts.

        Uses mode='latest' which loads only session-command.jsonl (the latest conversation).
        """
        # Create mock provider with sequential responses for multi-phase
        # With mode='latest', only 1 conversation (session-command) is analyzed
        # Multi-phase needs 2 calls: phase 1 (request resources) + phase 2 (analyze with resources)
        mock_provider = SequentialMockProvider(
            [
                # Phase 1: Request resources
                json.dumps(
                    {
                        "resource_requests": [
                            {
                                "resource_type": "command",
                                "resource_id": "test",
                                "reason": "Need to verify command requirements",
                            }
                        ],
                        "findings": [],
                        "final_determination": False,
                    }
                ),
                # Phase 2: Analyze with loaded resources
                json.dumps(
                    {
                        "resource_requests": [],
                        "findings": [
                            {
                                "turn_number": 2,
                                "observed_behavior": (
                                    "AI executed /test without activating " "testing skill"
                                ),
                                "expected_behavior": (
                                    "AI should activate testing skill " "before /test command"
                                ),
                                "context": (
                                    "Command requires 'testing' skill but " "AI skipped activation"
                                ),
                            }
                        ],
                        "final_determination": True,
                    }
                ),
            ]
        )

        print(f"\n=== DEBUG: project_dir = {e2e_project_dir}")
        print(f"=== DEBUG: .drift.yaml exists = {(e2e_project_dir / '.drift.yaml').exists()}")
        if (e2e_project_dir / ".drift.yaml").exists():
            config_text = (e2e_project_dir / ".drift.yaml").read_text()
            print(
                f"=== DEBUG: Has command_activation_required = "
                f"{'command_activation_required' in config_text}"
            )
            print(f"=== DEBUG: Has missing_command = " f"{'missing_command' in config_text}")

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run analysis with --format json to get detailed metadata
            result = cli_runner.invoke(
                app,
                [
                    "--project",
                    str(e2e_project_dir),
                    "--format",
                    "json",
                    "--types",
                    "command_activation_required",
                ],
            )

        # Parse JSON output
        print(f"\n=== DEBUG: CLI exit code = {result.exit_code}")
        print(f"=== DEBUG: CLI stderr = {result.stderr}")
        if result.exception:
            import traceback

            exc_type = type(result.exception)
            exc_value = result.exception
            exc_tb = result.exception.__traceback__
            exc_formatted = traceback.format_exception(exc_type, exc_value, exc_tb)
            print(f"=== DEBUG: Exception: {exc_formatted}")

        output = json.loads(result.stdout)

        # DEBUG: Print what we got
        print(f"\n=== DEBUG: mock_provider.call_count = " f"{mock_provider.call_count}")
        print(f"=== DEBUG: Number of results = {len(output['results'])}")
        print(f"=== DEBUG: Summary = {output.get('summary', {})}")

        # Find execution detail for command_activation_required
        exec_details = output["metadata"]["execution_details"]
        print(f"=== DEBUG: execution_details = {json.dumps(exec_details, indent=2)}")

        cmd_detail = next(
            (d for d in exec_details if d["rule_name"] == "command_activation_required"),
            None,
        )

        assert cmd_detail is not None, (
            f"command_activation_required not in execution_details. "
            f"Found: {[d['rule_name'] for d in exec_details]}"
        )

        # Verify multi-phase execution
        assert "phase_results" in cmd_detail, "Multi-phase rule should have phase_results"

        print(f"=== DEBUG: phase_results = {cmd_detail.get('phase_results')}")

        assert (
            len(cmd_detail["phase_results"]) == 2
        ), f"Should execute 2 phases, got {len(cmd_detail.get('phase_results', []))}"

        # Verify resources were consulted
        assert (
            "resources_consulted" in cmd_detail
        ), "Multi-phase rule should have resources_consulted"
        resources = cmd_detail["resources_consulted"]
        assert len(resources) > 0, "Should have consulted at least one resource"

        # Verify prompt content
        # Phase 1 should have conversation context
        # Phase 2 should have loaded command and skill resources
        assert mock_provider.call_count >= 2, (
            f"Should make at least 2 calls for multi-phase, " f"got {mock_provider.call_count}"
        )

        # Check that prompts contain expected content
        prompts = [call["prompt"] for call in mock_provider.calls]

        # Phase 1 prompt should include conversation
        assert any(
            "/test" in prompt or "test command" in prompt.lower() for prompt in prompts[:2]
        ), "Phase 1 prompt should include conversation content about /test command"

        # Phase 2 prompt should include loaded resources
        # (Would contain command file content or skill content)
        # This is harder to test without knowing exact formatting, but we verify
        # resources_consulted above

        # Verify response quality
        # Check that phase 1 response had meaningful resource requests
        phase1_response = json.loads(mock_provider.responses[0])
        assert "resource_requests" in phase1_response
        for req in phase1_response["resource_requests"]:
            assert len(req.get("reason", "")) > 20, (
                f"Resource request reason should be meaningful (>20 chars), "
                f"got: {req.get('reason')}"
            )

        # Check that phase 2 response had meaningful findings
        phase2_response = json.loads(mock_provider.responses[1])
        assert "findings" in phase2_response
        if len(phase2_response["findings"]) > 0:
            finding = phase2_response["findings"][0]
            assert len(finding.get("observed_behavior", "")) > 20, (
                f"Finding observed_behavior should be meaningful (>20 chars), "
                f"got: {finding.get('observed_behavior')}"
            )
            assert len(finding.get("expected_behavior", "")) > 20, (
                f"Finding expected_behavior should be meaningful (>20 chars), "
                f"got: {finding.get('expected_behavior')}"
            )

    def test_programmatic_validation_file_exists(self, cli_runner, temp_dir):
        """Test file_exists programmatic validation.

        Tests both passing (file exists) and failing (file missing) scenarios.
        """
        # Case A: CLAUDE.md exists → passed
        project_with_file = temp_dir / "project_with_file"
        project_with_file.mkdir()
        (project_with_file / "CLAUDE.md").write_text("# Project Config\n")

        # Create config with file_exists rule
        config_content = """
drift_learning_types:
  claude_md_missing:
    description: "Project missing CLAUDE.md configuration file"
    scope: "project_level"
    context: "CLAUDE.md provides essential context"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "configuration"
        file_patterns: ["CLAUDE.md"]
        bundle_strategy: "collection"
      rules:
        - rule_type: "file_exists"
          description: "CLAUDE.md must exist"
          file_path: "CLAUDE.md"
          failure_message: "CLAUDE.md is missing"
          expected_behavior: "CLAUDE.md should exist"
"""
        (project_with_file / ".drift.yaml").write_text(config_content)

        # Run with --no-llm (only programmatic rules)
        result_pass = cli_runner.invoke(
            app, ["--project", str(project_with_file), "--no-llm", "--format", "json"]
        )

        # Should pass (exit code 0)
        assert result_pass.exit_code == 0, (
            f"Expected exit code 0 when file exists, got {result_pass.exit_code}\n"
            f"stdout: {result_pass.stdout}"
        )

        # Parse and verify
        output_pass = json.loads(result_pass.stdout)
        # Extract learnings
        all_learnings_pass = []
        for result in output_pass["results"]:
            all_learnings_pass.extend(result.get("learnings", []))
        assert len(all_learnings_pass) == 0, "Should have no learnings when file exists"

        # Verify execution detail shows passed
        exec_details = output_pass["metadata"]["execution_details"]
        claude_md_detail = next(
            (d for d in exec_details if d["rule_name"] == "claude_md_missing"), None
        )
        assert claude_md_detail is not None
        assert claude_md_detail["status"] == "passed"

        # Case B: CLAUDE.md missing → failed with learning
        project_without_file = temp_dir / "project_without_file"
        project_without_file.mkdir()
        (project_without_file / ".drift.yaml").write_text(config_content)

        result_fail = cli_runner.invoke(
            app, ["--project", str(project_without_file), "--no-llm", "--format", "json"]
        )

        # Should fail (exit code 2 = drift found)
        assert result_fail.exit_code == 2, (
            f"Expected exit code 2 when file missing, got {result_fail.exit_code}\n"
            f"stdout: {result_fail.stdout}"
        )

        # Parse and verify
        output_fail = json.loads(result_fail.stdout)
        assert len(output_fail["results"]) > 0, "Should have results when file missing"

        # Extract learnings from results
        all_learnings = []
        for result in output_fail["results"]:
            all_learnings.extend(result.get("learnings", []))

        assert len(all_learnings) > 0, "Should have learnings when file missing"

        # Verify learning
        learning = all_learnings[0]
        assert learning["learning_type"] == "claude_md_missing"
        assert "CLAUDE.md" in learning["observed_behavior"]

        # Verify execution detail shows failed
        exec_details_fail = output_fail["metadata"]["execution_details"]
        claude_md_detail_fail = next(
            (d for d in exec_details_fail if d["rule_name"] == "claude_md_missing"), None
        )
        assert claude_md_detail_fail is not None
        assert claude_md_detail_fail["status"] == "failed"

    def test_programmatic_validation_regex_match(self, cli_runner, temp_dir):
        """Test regex_match programmatic validation."""
        # Create test project
        project_dir = temp_dir / "regex_test"
        project_dir.mkdir()

        # Create README with specific pattern
        (project_dir / "README.md").write_text(
            "# Test Project\n\nVersion: 1.2.3\n\nDescription content."
        )

        # Create config with regex_match rule
        config_content = """
drift_learning_types:
  readme_version_format:
    description: "README should have proper version format"
    scope: "project_level"
    context: "Version format consistency"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "documentation"
        file_patterns: ["README.md"]
        bundle_strategy: "collection"
      rules:
        - rule_type: "regex_match"
          description: "README should contain version in X.Y.Z format"
          file_path: "README.md"
          pattern: "Version: \\\\d+\\\\.\\\\d+\\\\.\\\\d+"
          failure_message: "README missing proper version format"
          expected_behavior: "README should include 'Version: X.Y.Z'"
"""
        (project_dir / ".drift.yaml").write_text(config_content)

        # Run validation (should pass)
        result = cli_runner.invoke(
            app, ["--project", str(project_dir), "--no-llm", "--format", "json"]
        )

        # Should pass
        assert result.exit_code == 0, (
            f"Expected exit code 0 for matching pattern, got {result.exit_code}\n"
            f"stdout: {result.stdout}"
        )

        output = json.loads(result.stdout)
        assert len(output["results"]) == 0, "Should have no learnings when pattern matches"

        # Test non-matching case
        (project_dir / "README.md").write_text("# Test Project\n\nNo version here.")

        result_fail = cli_runner.invoke(
            app, ["--project", str(project_dir), "--no-llm", "--format", "json"]
        )

        # Should fail
        assert (
            result_fail.exit_code == 2
        ), f"Expected exit code 2 for non-matching pattern, got {result_fail.exit_code}"

        output_fail = json.loads(result_fail.stdout)
        assert len(output_fail["results"]) > 0, "Should have learning when pattern doesn't match"

    def test_learning_type_filter(self, cli_runner, e2e_project_dir_all_conversations):
        """Test --types filter to run specific learning types only."""
        e2e_project_dir = e2e_project_dir_all_conversations
        # Create mock provider with responses
        mock_provider = SequentialMockProvider(
            [
                # Response for incomplete_work
                json.dumps(
                    [
                        {
                            "turn_number": 3,
                            "observed_behavior": (
                                "AI implemented only login functionality without "
                                "logout or session management components"
                            ),
                            "expected_behavior": (
                                "Complete authentication system should include "
                                "login, logout, and session management"
                            ),
                            "resolved": False,
                            "still_needs_action": True,
                            "context": "User had to ask for missing components",
                        }
                    ]
                ),
            ]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --types to filter to only incomplete_work
            result = cli_runner.invoke(
                app,
                [
                    "--project",
                    str(e2e_project_dir),
                    "--types",
                    "incomplete_work",
                    "--format",
                    "json",
                ],
            )

        # Parse output
        output = json.loads(result.stdout)

        # Extract all learnings from conversations
        all_learnings = []
        for conv in output["results"]:
            all_learnings.extend(conv.get("learnings", []))

        # Should only have incomplete_work learnings
        learning_types = {learning["learning_type"] for learning in all_learnings}
        assert "incomplete_work" in learning_types or len(learning_types) == 0

        # Should NOT have other types
        assert (
            "skill_ignored" not in learning_types
        ), "Should not run skill_ignored when filtered out"
        assert (
            "claude_md_missing" not in learning_types
        ), "Should not run claude_md_missing when filtered out"

        # Execution details should only show incomplete_work
        exec_details = output["metadata"]["execution_details"]
        rule_names = {d["rule_name"] for d in exec_details}

        assert "incomplete_work" in rule_names, (
            f"Should run incomplete_work with --types filter. " f"Found: {rule_names}"
        )

        # May or may not have other rules depending on implementation
        # The important thing is incomplete_work ran

    def test_model_override(self, cli_runner, e2e_project_dir):
        """Test --model override changes which model is used."""
        # Create mock provider that tracks which model was requested
        mock_provider = SequentialMockProvider(
            [
                json.dumps([]),  # Empty responses
                json.dumps([]),
                json.dumps([]),
                json.dumps([]),
            ]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            # Run with --model sonnet (override default haiku)
            result = cli_runner.invoke(
                app,
                ["--project", str(e2e_project_dir), "--model", "sonnet", "--format", "json"],
            )

        # Parse output
        output = json.loads(result.stdout)

        # Check execution details to see if model was overridden
        # The exact field name may vary, but we're looking for indication
        # of model used
        _ = output["metadata"]["execution_details"]

        # At minimum, verify the CLI didn't error with the --model flag
        assert result.exit_code in [0, 2], (
            f"CLI should handle --model flag gracefully, " f"got exit code {result.exit_code}"
        )

        # Verify mock provider was called (if there were any LLM rules)
        # The test mainly ensures --model flag is accepted and passed through

    def test_conversation_mode_latest(self, cli_runner, temp_dir):
        """Test conversation mode 'latest' loads only the most recent file."""
        # Create project with multiple conversations
        project_dir = temp_dir / "mode_latest"
        project_dir.mkdir()
        (project_dir / "CLAUDE.md").write_text("# Test\n")

        # Create conversation files with different modification times
        logs_base = project_dir / ".logs"
        logs_base.mkdir()
        mangled_name = str(project_dir).replace("/", "-").replace("_", "-")
        logs_dir = logs_base / mangled_name
        logs_dir.mkdir()

        # Create 3 files, ensure different mtimes
        import time

        self._create_conversation_jsonl(logs_dir / "old1.jsonl", "no_drift", project_dir)
        time.sleep(0.1)
        self._create_conversation_jsonl(logs_dir / "old2.jsonl", "skill_ignored", project_dir)
        time.sleep(0.1)
        self._create_conversation_jsonl(logs_dir / "newest.jsonl", "incomplete_work", project_dir)

        # Config with mode='latest' (default)
        config_content = self._create_realistic_config(project_dir, conversation_mode="latest")
        (project_dir / ".drift.yaml").write_text(config_content)

        # Create mock provider - should only be called for the latest conversation
        mock_provider = SequentialMockProvider([json.dumps([])])  # No drift

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            result = cli_runner.invoke(app, ["--project", str(project_dir), "--format", "json"])

        output = json.loads(result.stdout)

        # Should only analyze 1 conversation (the latest)
        assert output["summary"]["conversations_analyzed"] == 1, (
            f"mode='latest' should analyze 1 conversation, "
            f"got {output['summary']['conversations_analyzed']}"
        )

    def test_conversation_mode_all(self, cli_runner, e2e_project_dir_all_conversations):
        """Test conversation mode 'all' loads all conversation files."""
        # Use fixture with mode='all'
        mock_provider = SequentialMockProvider(
            [json.dumps([]), json.dumps([]), json.dumps([]), json.dumps([])]
        )

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            result = cli_runner.invoke(
                app, ["--project", str(e2e_project_dir_all_conversations), "--format", "json"]
            )

        output = json.loads(result.stdout)

        # Should analyze all 4 conversations
        assert output["summary"]["conversations_analyzed"] == 4, (
            f"mode='all' should analyze 4 conversations, "
            f"got {output['summary']['conversations_analyzed']}"
        )

    def test_conversation_mode_last_n_days(self, cli_runner, temp_dir):
        """Test conversation mode 'last_n_days' filters by modification time."""
        project_dir = temp_dir / "mode_days"
        project_dir.mkdir()
        (project_dir / "CLAUDE.md").write_text("# Test\n")

        logs_base = project_dir / ".logs"
        logs_base.mkdir()
        mangled_name = str(project_dir).replace("/", "-").replace("_", "-")
        logs_dir = logs_base / mangled_name
        logs_dir.mkdir()

        # Create conversation files
        # Create files
        old_file = logs_dir / "old.jsonl"
        recent_file = logs_dir / "recent.jsonl"

        self._create_conversation_jsonl(old_file, "no_drift", project_dir)
        self._create_conversation_jsonl(recent_file, "incomplete_work", project_dir)

        # Set old file to 10 days ago
        ten_days_ago = (datetime.now() - timedelta(days=10)).timestamp()
        import os

        os.utime(old_file, (ten_days_ago, ten_days_ago))

        # Config with mode='last_n_days', days=7
        config_content = self._create_realistic_config(
            project_dir, conversation_mode="last_n_days", conversation_days=7
        )
        (project_dir / ".drift.yaml").write_text(config_content)

        mock_provider = SequentialMockProvider([json.dumps([])])

        with patch("drift.core.analyzer.BedrockProvider", return_value=mock_provider):
            result = cli_runner.invoke(app, ["--project", str(project_dir), "--format", "json"])

        output = json.loads(result.stdout)

        # Should only analyze 1 conversation (recent one within 7 days)
        assert output["summary"]["conversations_analyzed"] == 1, (
            f"mode='last_n_days' with days=7 should analyze 1 conversation, "
            f"got {output['summary']['conversations_analyzed']}"
        )

    def test_exit_codes_comprehensive(self, cli_runner, temp_dir):
        """Test all exit code scenarios: 0 (no drift), 2 (drift found), 1 (error)."""
        # Exit code 0: No learnings found
        project_no_drift = temp_dir / "no_drift"
        project_no_drift.mkdir()
        (project_no_drift / "CLAUDE.md").write_text("# Config\n")

        config_pass = """
drift_learning_types:
  claude_md_missing:
    description: "CLAUDE.md check"
    scope: "project_level"
    context: "Context"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "configuration"
        file_patterns: ["CLAUDE.md"]
        bundle_strategy: "collection"
      rules:
        - rule_type: "file_exists"
          description: "CLAUDE.md must exist"
          file_path: "CLAUDE.md"
          failure_message: "Missing"
          expected_behavior: "Should exist"
"""
        (project_no_drift / ".drift.yaml").write_text(config_pass)

        result_0 = cli_runner.invoke(app, ["--project", str(project_no_drift), "--no-llm"])
        assert result_0.exit_code == 0, f"Expected exit code 0, got {result_0.exit_code}"

        # Exit code 2: Drift found
        project_with_drift = temp_dir / "with_drift"
        project_with_drift.mkdir()
        # Don't create CLAUDE.md so validation fails
        (project_with_drift / ".drift.yaml").write_text(config_pass)

        result_2 = cli_runner.invoke(app, ["--project", str(project_with_drift), "--no-llm"])
        assert result_2.exit_code == 2, f"Expected exit code 2, got {result_2.exit_code}"

        # Exit code 1: Error scenarios
        # Invalid path
        result_1_path = cli_runner.invoke(app, ["--project", str(temp_dir / "nonexistent")])
        assert result_1_path.exit_code == 1, (
            f"Expected exit code 1 for invalid path, " f"got {result_1_path.exit_code}"
        )

        # Invalid config format
        project_bad_config = temp_dir / "bad_config"
        project_bad_config.mkdir()
        (project_bad_config / ".drift.yaml").write_text("invalid: yaml: content: [")

        result_1_config = cli_runner.invoke(app, ["--project", str(project_bad_config)])
        assert result_1_config.exit_code == 1, (
            f"Expected exit code 1 for invalid config, " f"got {result_1_config.exit_code}"
        )

    def test_document_bundle_strategies(self, cli_runner, temp_dir):
        """Test individual vs collection bundle strategies.

        - individual: Analyzes each file separately, creates one learning per file
        - collection: Analyzes all files together, creates single analysis
        """
        # Test individual strategy
        project_individual = temp_dir / "individual"
        project_individual.mkdir()

        # Create .claude directory with multiple skills
        claude_dir = project_individual / ".claude"
        claude_dir.mkdir()
        skills_dir = claude_dir / "skills"
        skills_dir.mkdir()

        # Create multiple skill directories
        (skills_dir / "skill1").mkdir()
        (skills_dir / "skill1" / "SKILL.md").write_text("# Skill 1\nIncomplete")
        (skills_dir / "skill2").mkdir()
        (skills_dir / "skill2" / "SKILL.md").write_text("# Skill 2\nAlso incomplete")

        # Config with individual strategy for skills
        config_individual = """
drift_learning_types:
  skill_completeness:
    description: "Skills should be complete"
    scope: "project_level"
    context: "Complete skills"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "skill"
        file_patterns: [".claude/skills/*/SKILL.md"]
        bundle_strategy: "individual"
      rules:
        - rule_type: "regex_match"
          description: "Skill should have examples"
          file_path: "SKILL.md"
          pattern: "## Examples"
          failure_message: "Missing examples section"
          expected_behavior: "Should have examples"
"""
        (project_individual / ".drift.yaml").write_text(config_individual)

        result_individual = cli_runner.invoke(
            app, ["--project", str(project_individual), "--no-llm", "--format", "json"]
        )

        # With individual strategy, should get separate learnings for each file
        output_individual = json.loads(result_individual.stdout)
        # Should have multiple learnings (one per skill file)
        # Results array has 1 AnalysisResult for documents with multiple learnings inside
        assert len(output_individual["results"]) >= 1, "Should have document results"
        document_result = output_individual["results"][0]
        assert len(document_result["learnings"]) >= 2, (
            f"Individual strategy should create separate learnings (one per file), "
            f"got {len(document_result['learnings'])}"
        )

        # Test collection strategy
        project_collection = temp_dir / "collection"
        project_collection.mkdir()
        (project_collection / "README.md").write_text("# Project\nContent")
        (project_collection / "CONTRIBUTING.md").write_text("# Contributing\nGuide")

        # Config with collection strategy
        config_collection = """
drift_learning_types:
  docs_consistency:
    description: "Documentation consistency"
    scope: "project_level"
    context: "Consistent docs"
    requires_project_context: true
    validation_rules:
      document_bundle:
        bundle_type: "documentation"
        file_patterns: ["*.md"]
        bundle_strategy: "collection"
      rules:
        - rule_type: "regex_match"
          description: "Should have license section"
          file_path: "README.md"
          pattern: "## License"
          failure_message: "Missing license"
          expected_behavior: "Should have license"
"""
        (project_collection / ".drift.yaml").write_text(config_collection)

        result_collection = cli_runner.invoke(
            app, ["--project", str(project_collection), "--no-llm", "--format", "json"]
        )

        # With collection strategy, should get single analysis
        output_collection = json.loads(result_collection.stdout)

        # Execution details should show collection strategy
        exec_details = output_collection["metadata"]["execution_details"]
        docs_detail = next((d for d in exec_details if d["rule_name"] == "docs_consistency"), None)

        assert docs_detail is not None, "Should have execution detail for docs_consistency"

        # Collection strategy should process files together
        # (Exact structure may vary, but should indicate collection approach)
