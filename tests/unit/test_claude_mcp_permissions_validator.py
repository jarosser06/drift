"""Tests for ClaudeMcpPermissionsValidator."""

import json

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle
from drift.validation.validators.client.claude import ClaudeMcpPermissionsValidator


class TestClaudeMcpPermissionsValidator:
    """Tests for ClaudeMcpPermissionsValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ClaudeMcpPermissionsValidator()

    @pytest.fixture
    def validation_rule(self):
        """Create validation rule for testing."""
        return ValidationRule(
            rule_type="core:claude_mcp_permissions",
            description="Check for MCP permissions",
            failure_message="MCP servers missing permissions",
            expected_behavior="All MCP servers have permissions",
        )

    def test_no_mcp_file_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when .mcp.json doesn't exist."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_empty_mcp_servers_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when no MCP servers defined."""
        # Create .mcp.json with no servers
        mcp_file = tmp_path / ".mcp.json"
        mcp_file.write_text(json.dumps({"mcpServers": {}}))

        # Create settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"permissions": {"allow": []}}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_enable_all_project_mcp_servers_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when enableAllProjectMcpServers is true."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
                "serena": {"command": "mcp-server-serena"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create settings.json with enableAllProjectMcpServers
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "enableAllProjectMcpServers": True,
            "permissions": {"allow": []},
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_all_servers_have_permissions_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes when all MCP servers have permissions."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
                "serena": {"command": "mcp-server-serena"},
                "context7": {"command": "mcp-server-context7"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "mcp__github",
                    "mcp__serena",
                    "mcp__context7",
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_missing_single_permission_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails when one MCP server lacks permission."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
                "serena": {"command": "mcp-server-serena"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create settings.json with only partial permissions
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "mcp__github",
                    # Missing serena
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "serena" in result.context
        assert "MCP servers missing from permissions.allow" in result.context
        assert "mcp__serena" in result.context

    def test_missing_multiple_permissions_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails and reports all missing MCP servers."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
                "serena": {"command": "mcp-server-serena"},
                "context7": {"command": "mcp-server-context7"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create settings.json with only one permission
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "mcp__github",
                    # Missing serena and context7
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "serena" in result.context
        assert "context7" in result.context

    def test_missing_all_permissions_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails when no permissions exist for MCP servers."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create settings.json with empty allow list
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {"permissions": {"allow": []}}
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "github" in result.context

    def test_missing_settings_file_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails when settings.json is missing but .mcp.json exists."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # No settings.json

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "settings.json not found" in result.context
        assert ".mcp.json exists" in result.context

    def test_invalid_mcp_json_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails with invalid .mcp.json."""
        # Create invalid .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_file.write_text("{ invalid json")

        # Create settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text(json.dumps({"permissions": {"allow": []}}))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "Invalid JSON in .mcp.json" in result.context

    def test_invalid_settings_json_fails(self, validator, validation_rule, tmp_path):
        """Test validation fails with invalid settings.json."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create invalid settings.json
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings_file.write_text("{ invalid json")

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert "Invalid JSON in settings.json" in result.context

    def test_permissions_with_other_entries_passes(self, validator, validation_rule, tmp_path):
        """Test validation passes with MCP permissions among other permissions."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create settings.json with mixed permissions
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {
            "permissions": {
                "allow": [
                    "Skill(testing)",
                    "Bash(ls:*)",
                    "mcp__github",
                    "WebSearch",
                ]
            }
        }
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is None

    def test_computation_type_is_programmatic(self, validator):
        """Test validator is programmatic."""
        assert validator.computation_type == "programmatic"

    def test_supported_clients_is_claude(self, validator):
        """Test validator only supports Claude."""
        from drift.config.models import ClientType

        clients = validator.supported_clients
        assert len(clients) == 1
        assert ClientType.CLAUDE in clients

    def test_file_paths_include_both_files(self, validator, validation_rule, tmp_path):
        """Test failure result includes both .mcp.json and settings.json in file_paths."""
        # Create .mcp.json
        mcp_file = tmp_path / ".mcp.json"
        mcp_config = {
            "mcpServers": {
                "github": {"command": "mcp-server-github"},
            }
        }
        mcp_file.write_text(json.dumps(mcp_config))

        # Create settings.json with no permissions
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_file = claude_dir / "settings.json"
        settings = {"permissions": {"allow": []}}
        settings_file.write_text(json.dumps(settings))

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        result = validator.validate(validation_rule, bundle)
        assert result is not None
        assert ".claude/settings.json" in result.file_paths
        assert ".mcp.json" in result.file_paths
