"""Tests for parameter type resolution."""

import re

import pytest

from drift.core.types import DocumentBundle
from drift.documents.loader import DocumentLoader
from drift.validation.params import ParamResolver


class TestParamResolver:
    """Tests for ParamResolver."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create a temporary project structure."""
        # Create skill
        skill_dir = tmp_path / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill\nContent here")

        # Create command
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "test-command.md").write_text("# Test Command\nRun tests")

        # Create test file
        (tmp_path / "settings.json").write_text('{"key": "value"}')

        return tmp_path

    @pytest.fixture
    def bundle(self, project_root):
        """Create a test bundle."""
        return DocumentBundle(
            bundle_id="test",
            bundle_type="test",
            bundle_strategy="individual",
            files=[],
            project_path=project_root,
        )

    @pytest.fixture
    def loader(self, project_root):
        """Create a document loader."""
        return DocumentLoader(project_root)

    def test_resolve_string(self, bundle):
        """Test STRING param type resolution."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve({"type": "string", "value": "hello"})
        assert result == "hello"

    def test_resolve_string_invalid_value(self, bundle):
        """Test STRING param with non-string value."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="STRING param requires string value"):
            resolver.resolve({"type": "string", "value": 123})

    def test_resolve_string_list_from_list(self, bundle):
        """Test STRING_LIST param with list input."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve({"type": "string_list", "value": ["a", "b", "c"]})
        assert result == ["a", "b", "c"]

    def test_resolve_string_list_from_string(self, bundle):
        """Test STRING_LIST param with comma-separated string."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve({"type": "string_list", "value": "a, b, c"})
        assert result == ["a", "b", "c"]

    def test_resolve_resource_list(self, bundle, loader):
        """Test RESOURCE_LIST param type."""
        resolver = ParamResolver(bundle, loader)
        result = resolver.resolve({"type": "resource_list", "value": "skill"})
        assert "test-skill" in result

    def test_resolve_resource_list_no_loader(self, bundle):
        """Test RESOURCE_LIST without loader raises error."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="RESOURCE_LIST param requires loader"):
            resolver.resolve({"type": "resource_list", "value": "skill"})

    def test_resolve_resource_content_skill(self, bundle):
        """Test RESOURCE_CONTENT param for skill."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve({"type": "resource_content", "value": "skill:test-skill"})
        assert "Test Skill" in result
        assert "Content here" in result

    def test_resolve_resource_content_command(self, bundle):
        """Test RESOURCE_CONTENT param for command."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve({"type": "resource_content", "value": "command:test-command"})
        assert "Test Command" in result
        assert "Run tests" in result

    def test_resolve_resource_content_invalid_format(self, bundle):
        """Test RESOURCE_CONTENT with invalid format."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="RESOURCE_CONTENT requires 'type:name' format"):
            resolver.resolve({"type": "resource_content", "value": "invalid"})

    def test_resolve_resource_content_unknown_type(self, bundle):
        """Test RESOURCE_CONTENT with unknown resource type."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="Unknown resource type"):
            resolver.resolve({"type": "resource_content", "value": "unknown:foo"})

    def test_resolve_resource_content_not_found(self, bundle):
        """Test RESOURCE_CONTENT for nonexistent resource."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="Resource not found"):
            resolver.resolve({"type": "resource_content", "value": "skill:nonexistent"})

    def test_resolve_file_content(self, bundle):
        """Test FILE_CONTENT param type."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve({"type": "file_content", "value": "settings.json"})
        assert "key" in result
        assert "value" in result

    def test_resolve_file_content_not_found(self, bundle):
        """Test FILE_CONTENT for nonexistent file."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="File not found"):
            resolver.resolve({"type": "file_content", "value": "nonexistent.txt"})

    def test_resolve_regex_pattern(self, bundle):
        """Test REGEX_PATTERN param type."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve({"type": "regex_pattern", "value": r"test_\w+"})
        assert isinstance(result, re.Pattern)
        assert result.match("test_foo")

    def test_resolve_regex_pattern_invalid(self, bundle):
        """Test REGEX_PATTERN with invalid pattern."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="Invalid regex pattern"):
            resolver.resolve({"type": "regex_pattern", "value": r"test_["})

    def test_resolve_legacy_non_dict_param(self, bundle):
        """Test legacy non-dict parameters pass through."""
        resolver = ParamResolver(bundle)
        result = resolver.resolve("plain string")
        assert result == "plain string"

    def test_resolve_unsupported_type(self, bundle):
        """Test unsupported param type raises error."""
        resolver = ParamResolver(bundle)
        with pytest.raises(ValueError, match="Unsupported param type"):
            resolver.resolve({"type": "unknown_type", "value": "test"})
