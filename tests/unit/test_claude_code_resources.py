"""Tests for Claude Code resource loading."""

import json
from pathlib import Path

import pytest

from drift.agent_tools.claude_code import ClaudeCodeContextExtractor, ClaudeCodeLoader


class TestClaudeCodeContextExtractor:
    """Test ClaudeCodeContextExtractor methods."""

    @pytest.fixture
    def extractor(self):
        """Create a context extractor instance."""
        return ClaudeCodeContextExtractor()

    @pytest.fixture
    def project_with_features(self, temp_dir):
        """Create a project directory with Claude Code features."""
        project_root = temp_dir / "test_project"
        project_root.mkdir()

        # Create commands
        commands_dir = project_root / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "test.md").write_text("# Test Command\nDo something")
        (commands_dir / "lint.md").write_text("# Lint Command\nRun linter")

        # Create skills
        skills_dir = project_root / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "testing.md").write_text("# Testing Skill\nWrite tests")

        # Create MCP config
        mcp_config = {"mcpServers": {"github": {}, "filesystem": {}}}
        (project_root / ".mcp.json").write_text(json.dumps(mcp_config))

        # Create agents
        agents_dir = project_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "qa.md").write_text("# QA Agent\nRun QA")

        return project_root

    def test_extract_context_with_all_features(self, extractor, project_with_features):
        """Test extracting context with all features present."""
        context = extractor.extract_context(str(project_with_features))

        assert context is not None
        assert "Commands: /lint, /test" in context
        assert "Skills: testing" in context
        assert "MCP Servers: filesystem, github" in context
        assert "Agents: qa" in context

    def test_extract_context_no_project_path(self, extractor):
        """Test extracting context with no project path."""
        assert extractor.extract_context(None) is None
        assert extractor.extract_context("") is None

    def test_extract_context_nonexistent_path(self, extractor):
        """Test extracting context from nonexistent path."""
        context = extractor.extract_context("/nonexistent/path")
        assert context is None

    def test_extract_context_empty_project(self, extractor, temp_dir):
        """Test extracting context from empty project."""
        empty_project = temp_dir / "empty"
        empty_project.mkdir()
        context = extractor.extract_context(str(empty_project))
        assert context is None  # No features to extract

    def test_extract_commands(self, extractor, project_with_features):
        """Test extracting command names."""
        commands = extractor._extract_commands(project_with_features)
        assert commands == ["/lint", "/test"]

    def test_extract_commands_empty_dir(self, extractor, temp_dir):
        """Test extracting commands from empty directory."""
        empty_dir = temp_dir / "no_commands"
        empty_dir.mkdir()
        commands = extractor._extract_commands(empty_dir)
        assert commands == []

    def test_extract_skills(self, extractor, project_with_features):
        """Test extracting skill names."""
        skills = extractor._extract_skills(project_with_features)
        assert skills == ["testing"]

    def test_extract_skills_empty_dir(self, extractor, temp_dir):
        """Test extracting skills from empty directory."""
        empty_dir = temp_dir / "no_skills"
        empty_dir.mkdir()
        skills = extractor._extract_skills(empty_dir)
        assert skills == []

    def test_extract_mcp_servers(self, extractor, project_with_features):
        """Test extracting MCP server names."""
        servers = extractor._extract_mcp_servers(project_with_features)
        assert "filesystem" in servers
        assert "github" in servers

    def test_extract_mcp_servers_no_file(self, extractor, temp_dir):
        """Test extracting MCP servers when .mcp.json doesn't exist."""
        empty_dir = temp_dir / "no_mcp"
        empty_dir.mkdir()
        servers = extractor._extract_mcp_servers(empty_dir)
        assert servers == []

    def test_extract_mcp_servers_invalid_json(self, extractor, temp_dir):
        """Test extracting MCP servers with invalid JSON."""
        project = temp_dir / "bad_mcp"
        project.mkdir()
        (project / ".mcp.json").write_text("not valid json{")

        servers = extractor._extract_mcp_servers(project)
        assert servers == []  # Should handle error gracefully

    def test_extract_mcp_servers_missing_key(self, extractor, temp_dir):
        """Test extracting MCP servers when mcpServers key is missing."""
        project = temp_dir / "mcp_no_key"
        project.mkdir()
        (project / ".mcp.json").write_text(json.dumps({"other": "data"}))

        servers = extractor._extract_mcp_servers(project)
        assert servers == []

    def test_extract_agents(self, extractor, project_with_features):
        """Test extracting agent names."""
        agents = extractor._extract_agents(project_with_features)
        assert agents == ["qa"]

    def test_extract_agents_empty_dir(self, extractor, temp_dir):
        """Test extracting agents from empty directory."""
        empty_dir = temp_dir / "no_agents"
        empty_dir.mkdir()
        agents = extractor._extract_agents(empty_dir)
        assert agents == []


class TestClaudeCodeLoaderResources:
    """Test ClaudeCodeLoader resource loading methods."""

    @pytest.fixture
    def loader(self, temp_dir):
        """Create a ClaudeCodeLoader instance."""
        return ClaudeCodeLoader(str(temp_dir))

    @pytest.fixture
    def project_with_resources(self, temp_dir):
        """Create a project with various resources."""
        project_root = temp_dir / "resource_project"
        project_root.mkdir()

        # Create a command
        commands_dir = project_root / ".claude" / "commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "deploy.md").write_text("# Deploy\nDeploy the application")

        # Create a skill file
        skills_dir = project_root / ".claude" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "code-review.md").write_text("# Code Review\nReview code quality")

        # Create a skill directory
        testing_skill_dir = skills_dir / "testing"
        testing_skill_dir.mkdir()
        (testing_skill_dir / "SKILL.md").write_text("# Testing\nWrite comprehensive tests")

        # Create an agent
        agents_dir = project_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "developer.md").write_text("# Developer Agent\nImplement features")

        # Create main config (CLAUDE.md in project root)
        (project_root / "CLAUDE.md").write_text(
            "# Project Configuration\nThis is the main config for the project."
        )

        return project_root

    def test_get_resource_no_project_path(self, loader):
        """Test getting resource with no project path."""
        response = loader.get_resource("command", "test", project_path=None)

        assert response.found is False
        assert response.error == "No project path provided"
        assert response.content is None

    def test_get_resource_command(self, loader, project_with_resources):
        """Test getting a command resource."""
        response = loader.get_resource(
            "command", "deploy", project_path=str(project_with_resources)
        )

        assert response.found is True
        assert response.error is None
        assert "Deploy the application" in response.content
        assert response.file_path.endswith("deploy.md")

    def test_get_resource_command_with_slash(self, loader, project_with_resources):
        """Test getting a command resource with leading slash."""
        response = loader.get_resource(
            "command", "/deploy", project_path=str(project_with_resources)
        )

        assert response.found is True
        assert "Deploy the application" in response.content

    def test_get_resource_command_not_found(self, loader, project_with_resources):
        """Test getting a nonexistent command."""
        response = loader.get_resource(
            "command", "nonexistent", project_path=str(project_with_resources)
        )

        assert response.found is False
        assert "not found" in response.error.lower()

    def test_get_resource_skill_file(self, loader, project_with_resources):
        """Test getting a skill resource (file pattern)."""
        response = loader.get_resource(
            "skill", "code-review", project_path=str(project_with_resources)
        )

        assert response.found is True
        assert response.error is None
        assert "Review code quality" in response.content

    def test_get_resource_skill_directory(self, loader, project_with_resources):
        """Test getting a skill resource (directory pattern)."""
        response = loader.get_resource("skill", "testing", project_path=str(project_with_resources))

        assert response.found is True
        assert response.error is None
        assert "comprehensive tests" in response.content.lower()

    def test_get_resource_skill_not_found(self, loader, project_with_resources):
        """Test getting a nonexistent skill."""
        response = loader.get_resource(
            "skill", "nonexistent", project_path=str(project_with_resources)
        )

        assert response.found is False
        assert "not found" in response.error.lower()

    def test_get_resource_agent(self, loader, project_with_resources):
        """Test getting an agent resource."""
        response = loader.get_resource(
            "agent", "developer", project_path=str(project_with_resources)
        )

        assert response.found is True
        assert response.error is None
        assert "Implement features" in response.content

    def test_get_resource_agent_not_found(self, loader, project_with_resources):
        """Test getting a nonexistent agent."""
        response = loader.get_resource(
            "agent", "nonexistent", project_path=str(project_with_resources)
        )

        assert response.found is False
        assert "not found" in response.error.lower()

    def test_get_resource_main_config(self, loader, project_with_resources):
        """Test getting the main config."""
        response = loader.get_resource("main_config", "", project_path=str(project_with_resources))

        assert response.found is True
        assert response.error is None
        assert "Project Configuration" in response.content
        assert response.file_path.endswith("CLAUDE.md")

    def test_get_resource_main_config_not_found(self, loader, temp_dir):
        """Test getting main config when it doesn't exist."""
        empty_project = temp_dir / "no_config"
        empty_project.mkdir()

        response = loader.get_resource("main_config", "", project_path=str(empty_project))

        assert response.found is False
        assert "found" in response.error.lower()  # Error says " found" at the end

    def test_get_resource_unknown_type(self, loader, project_with_resources):
        """Test getting resource with unknown type."""
        response = loader.get_resource(
            "unknown_type", "foo", project_path=str(project_with_resources)
        )

        assert response.found is False
        assert "Unknown resource type" in response.error

    def test_get_resource_handles_exceptions(self, loader):
        """Test that get_resource handles exceptions gracefully."""
        # Use a path that will cause an exception
        response = loader.get_resource(
            "command", "test", project_path="/nonexistent/path/that/does/not/exist"
        )

        assert response.found is False
        assert response.error is not None

    def test_get_resource_main_config_mcp_json(self, loader, temp_dir):
        """Test getting main config from .mcp.json when CLAUDE.md doesn't exist."""
        project = temp_dir / "mcp_only"
        project.mkdir()

        # Create only .mcp.json (no CLAUDE.md)
        mcp_config = {"mcpServers": {"test": {}}}
        (project / ".mcp.json").write_text(json.dumps(mcp_config))

        response = loader.get_resource("main_config", "", project_path=str(project))

        assert response.found is True
        assert response.error is None
        assert "mcpServers" in response.content
        assert response.file_path.endswith(".mcp.json")


class TestClaudeCodeLoaderConversations:
    """Test ClaudeCodeLoader conversation loading methods."""

    @pytest.fixture
    def loader_with_convos(self, temp_dir):
        """Create a loader with some conversation files."""
        # Create a mock conversation directory structure
        convos_dir = temp_dir / "conversations"
        convos_dir.mkdir()

        # Create a mangled project directory (Claude Code format)
        project_dir = convos_dir / "-Users-jim-Projects-test-project"
        project_dir.mkdir()

        # Create conversation files
        (project_dir / "session1.jsonl").write_text('{"sessionId": "session1"}\n')
        (project_dir / "session2.jsonl").write_text('{"sessionId": "session2"}\n')

        return ClaudeCodeLoader(str(convos_dir))

    def test_get_conversation_files_all_projects(self, loader_with_convos):
        """Test getting conversation files from all projects."""
        files = loader_with_convos.get_conversation_files()

        assert len(files) == 2
        assert all(f.suffix == ".jsonl" for f in files)

    def test_get_conversation_files_specific_project(self, loader_with_convos):
        """Test getting conversation files for specific project."""
        # Use the original path (before mangling)
        project_path = Path("/Users/jim/Projects/test_project")
        files = loader_with_convos.get_conversation_files(project_path=project_path)

        assert len(files) == 2

    def test_get_conversation_files_with_since_filter(self, loader_with_convos, temp_dir):
        """Test filtering conversation files by modification time."""
        from datetime import datetime, timedelta

        # Files should be very recent, so a filter from the future should exclude them
        future = datetime.now() + timedelta(days=1)
        files = loader_with_convos.get_conversation_files(since=future)

        assert len(files) == 0  # All files excluded

    def test_get_conversation_files_sorted_by_mtime(self, temp_dir):
        """Test that files are sorted by modification time."""
        import time

        convos_dir = temp_dir / "sorted_test"
        convos_dir.mkdir()
        project_dir = convos_dir / "project1"
        project_dir.mkdir()

        # Create files with different modification times
        file1 = project_dir / "old.jsonl"
        file1.write_text('{"id": "old"}\n')
        time.sleep(0.01)

        file2 = project_dir / "new.jsonl"
        file2.write_text('{"id": "new"}\n')

        loader = ClaudeCodeLoader(str(convos_dir))
        files = loader.get_conversation_files()

        # Newest should be first
        assert len(files) == 2
        assert files[0].name == "new.jsonl"
        assert files[1].name == "old.jsonl"

    def test_parse_conversation_file_basic(self, temp_dir):
        """Test parsing a basic conversation file."""
        convo_file = temp_dir / "test.jsonl"
        convo_file.write_text(
            '{"type": "user", "sessionId": "test-123", "cwd": "/test/path", '
            '"message": {"content": [{"text": "Hello"}]}}\n'
            '{"type": "assistant", "message": {"content": [{"text": "Hi there"}]}}\n'
        )

        loader = ClaudeCodeLoader(str(temp_dir))
        result = loader._parse_conversation_file(convo_file)

        assert result["session_id"] == "test-123"
        assert result["project_path"] == "/test/path"

    def test_parse_conversation_file_empty(self, temp_dir):
        """Test parsing an empty conversation file."""
        convo_file = temp_dir / "empty.jsonl"
        convo_file.write_text("")

        loader = ClaudeCodeLoader(str(temp_dir))
        result = loader._parse_conversation_file(convo_file)

        # Session ID defaults to filename without extension
        assert result["session_id"] == "empty"
        assert result["project_path"] is None
        assert len(result["turns"]) == 0

    def test_parse_conversation_file_invalid_json(self, temp_dir):
        """Test parsing a file with invalid JSON lines."""
        convo_file = temp_dir / "invalid.jsonl"
        convo_file.write_text(
            "not valid json\n"
            '{"type": "user", "sessionId": "test", "message": {"content": [{"text": "Hello"}]}}\n'
            '{"type": "assistant", "message": {"content": [{"text": "Response"}]}}\n'
        )

        loader = ClaudeCodeLoader(str(temp_dir))
        result = loader._parse_conversation_file(convo_file)

        # Should skip invalid line but process valid ones
        assert result["session_id"] == "test"

    def test_parse_conversation_file_project_path_formats(self, temp_dir):
        """Test parsing project_path from both cwd and project_path fields."""
        # Test with cwd field (Claude Code format)
        convo_file1 = temp_dir / "with_cwd.jsonl"
        convo_file1.write_text('{"type": "user", "sessionId": "s1", "cwd": "/from/cwd"}\n')

        loader = ClaudeCodeLoader(str(temp_dir))
        result = loader._parse_conversation_file(convo_file1)
        assert result["project_path"] == "/from/cwd"

        # Test with project_path field (test format)
        convo_file2 = temp_dir / "with_project_path.jsonl"
        convo_file2.write_text(
            '{"type": "user", "sessionId": "s2", "project_path": "/from/project_path"}\n'
        )

        result2 = loader._parse_conversation_file(convo_file2)
        assert result2["project_path"] == "/from/project_path"
