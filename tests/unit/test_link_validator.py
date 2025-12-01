"""Unit tests for link validation."""

from unittest.mock import Mock, patch

import pytest
import requests

from drift.utils.link_validator import LinkValidator


class TestLinkValidator:
    """Test cases for LinkValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a LinkValidator instance."""
        return LinkValidator()

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        (tmp_path / ".claude" / "skills" / "test-skill").mkdir(parents=True)
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".claude" / "agents").mkdir(parents=True)
        (tmp_path / "docs").mkdir(parents=True)

        # Create some test files
        (tmp_path / ".claude" / "skills" / "test-skill" / "SKILL.md").write_text("skill")
        (tmp_path / ".claude" / "commands" / "test-cmd.md").write_text("command")
        (tmp_path / ".claude" / "agents" / "test-agent.md").write_text("agent")
        (tmp_path / "docs" / "readme.md").write_text("docs")

        return tmp_path

    def test_extract_links_simple(self, validator):
        """Test extracting simple markdown links."""
        content = "[Link Text](http://example.com)"

        links = validator.extract_links(content)

        assert len(links) == 1
        assert links[0] == ("Link Text", "http://example.com")

    def test_extract_links_multiple(self, validator):
        """Test extracting multiple links."""
        content = """
[First](http://first.com)
Some text
[Second](http://second.com)
[Third](file.md)
"""
        links = validator.extract_links(content)

        assert len(links) == 3
        assert links[0] == ("First", "http://first.com")
        assert links[1] == ("Second", "http://second.com")
        assert links[2] == ("Third", "file.md")

    def test_extract_links_none(self, validator):
        """Test content with no links."""
        content = "Just plain text with no links"

        links = validator.extract_links(content)

        assert len(links) == 0

    def test_extract_links_with_spaces(self, validator):
        """Test links with spaces in text."""
        content = "[Link with spaces](http://example.com)"

        links = validator.extract_links(content)

        assert len(links) == 1
        assert links[0] == ("Link with spaces", "http://example.com")

    def test_extract_links_relative_paths(self, validator):
        """Test extracting relative path links."""
        content = "[Doc](../docs/readme.md)\n[Local](./file.txt)"

        links = validator.extract_links(content)

        assert len(links) == 2
        assert links[0] == ("Doc", "../docs/readme.md")
        assert links[1] == ("Local", "./file.txt")

    def test_validate_local_file_exists(self, validator, temp_project):
        """Test validating existing local file."""
        base_path = temp_project / ".claude" / "commands"

        # Relative path from base_path
        is_valid = validator.validate_local_file("../skills/test-skill/SKILL.md", base_path)

        assert is_valid is True

    def test_validate_local_file_not_exists(self, validator, temp_project):
        """Test validating non-existent local file."""
        base_path = temp_project / ".claude" / "commands"

        is_valid = validator.validate_local_file("missing.md", base_path)

        assert is_valid is False

    def test_validate_local_file_absolute_path(self, validator, temp_project):
        """Test validating absolute path."""
        file_path = temp_project / "docs" / "readme.md"
        base_path = temp_project

        is_valid = validator.validate_local_file(str(file_path), base_path)

        assert is_valid is True

    def test_validate_local_file_directory(self, validator, temp_project):
        """Test that directories are not valid files."""
        base_path = temp_project

        is_valid = validator.validate_local_file(".claude/skills/test-skill", base_path)

        assert is_valid is False

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_external_url_success(self, mock_head, validator):
        """Test validating successful external URL."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        is_valid = validator.validate_external_url("http://example.com")

        assert is_valid is True
        mock_head.assert_called_once()

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_external_url_not_found(self, mock_head, validator):
        """Test validating URL that returns 404."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        is_valid = validator.validate_external_url("http://example.com/missing")

        assert is_valid is False

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_external_url_timeout(self, mock_head, validator):
        """Test handling URL timeout."""
        mock_head.side_effect = requests.Timeout()

        is_valid = validator.validate_external_url("http://example.com")

        assert is_valid is False

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_external_url_connection_error(self, mock_head, validator):
        """Test handling connection error."""
        mock_head.side_effect = requests.ConnectionError()

        is_valid = validator.validate_external_url("http://example.com")

        assert is_valid is False

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_external_url_redirect(self, mock_head, validator):
        """Test URL with redirect."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        is_valid = validator.validate_external_url("http://example.com/redirect")

        assert is_valid is True

    def test_validate_resource_reference_skill(self, validator, temp_project):
        """Test validating skill resource reference."""
        is_valid = validator.validate_resource_reference("test-skill", temp_project, "skill")

        assert is_valid is True

    def test_validate_resource_reference_skill_not_found(self, validator, temp_project):
        """Test validating non-existent skill."""
        is_valid = validator.validate_resource_reference("missing-skill", temp_project, "skill")

        assert is_valid is False

    def test_validate_resource_reference_command(self, validator, temp_project):
        """Test validating command resource reference."""
        is_valid = validator.validate_resource_reference("test-cmd", temp_project, "command")

        assert is_valid is True

    def test_validate_resource_reference_command_not_found(self, validator, temp_project):
        """Test validating non-existent command."""
        is_valid = validator.validate_resource_reference("missing-cmd", temp_project, "command")

        assert is_valid is False

    def test_validate_resource_reference_agent(self, validator, temp_project):
        """Test validating agent resource reference."""
        is_valid = validator.validate_resource_reference("test-agent", temp_project, "agent")

        assert is_valid is True

    def test_validate_resource_reference_agent_not_found(self, validator, temp_project):
        """Test validating non-existent agent."""
        is_valid = validator.validate_resource_reference("missing-agent", temp_project, "agent")

        assert is_valid is False

    def test_validate_resource_reference_unknown_type(self, validator, temp_project):
        """Test validating unknown resource type."""
        is_valid = validator.validate_resource_reference("test", temp_project, "unknown")

        assert is_valid is False

    def test_categorize_link_external(self, validator):
        """Test categorizing external URLs."""
        assert validator.categorize_link("http://example.com") == "external"
        assert validator.categorize_link("https://example.com") == "external"

    def test_categorize_link_local(self, validator):
        """Test categorizing local links."""
        assert validator.categorize_link("file.md") == "local"
        assert validator.categorize_link("./docs/readme.md") == "local"
        assert validator.categorize_link("../parent/file.txt") == "local"

    def test_categorize_link_unknown(self, validator):
        """Test categorizing special links."""
        assert validator.categorize_link("#anchor") == "unknown"
        assert validator.categorize_link("mailto:test@example.com") == "unknown"
        assert validator.categorize_link("tel:+1234567890") == "unknown"

    def test_extract_all_file_references_markdown_links(self, validator):
        """Test extracting markdown-style links."""
        content = "[Guide](README.md) and [API](docs/api.md)"

        refs = validator.extract_all_file_references(content)

        assert "README.md" in refs
        assert "docs/api.md" in refs

    def test_extract_all_file_references_relative_paths(self, validator):
        """Test extracting relative path references."""
        content = "See ./test.sh for details and ../setup.py for configuration"

        refs = validator.extract_all_file_references(content)

        assert "./test.sh" in refs
        assert "../setup.py" in refs

    def test_extract_all_file_references_absolute_paths(self, validator):
        """Test that absolute system paths are NOT extracted.

        Absolute paths like /usr/local/bin are usually examples in docs,
        not actual file references to validate. We only validate:
        - Relative paths (./file, ../file)
        - Paths with extensions (path/to/file.ext)
        - Standalone filenames with extensions
        """
        content = "Check /usr/local/bin/script or /etc/config.yaml"

        refs = validator.extract_all_file_references(content)

        # Absolute system paths should NOT be extracted (they're usually examples)
        assert "/usr/local/bin/script" not in refs
        # But files with extensions might be extracted as standalone files
        assert "config.yaml" in refs

    def test_extract_all_file_references_paths_with_extensions(self, validator):
        """Test extracting paths with common file extensions."""
        content = """
        Check README.md for info
        Run src/main.py
        See docs/guide.txt
        Config in config/settings.json
        """

        refs = validator.extract_all_file_references(content)

        assert "README.md" in refs
        assert "src/main.py" in refs
        assert "docs/guide.txt" in refs
        assert "config/settings.json" in refs

    def test_extract_all_file_references_ignores_urls(self, validator):
        """Test that URLs are not extracted as file paths."""
        content = "[Example](https://example.com/path/to/page) and http://test.com/file.pdf"

        refs = validator.extract_all_file_references(content)

        # Should get markdown link URL
        assert "https://example.com/path/to/page" in refs
        # Plain URLs (not in markdown links) are ignored
        # They're external URLs, not file references
        assert "http://test.com/file.pdf" not in refs
        # Should NOT extract fragments like "/path/to/page" from URLs
        assert not any("/path/to/page" == r for r in refs)
        assert not any("/file.pdf" == r for r in refs)

    def test_extract_all_file_references_mixed_content(self, validator):
        """Test extracting from content with mixed reference types."""
        content = """
        # Documentation

        See [Getting Started](docs/getting-started.md) for setup.
        Run ./install.sh to install.
        Configuration in config/app.yaml
        Visit [Docs](https://docs.example.com) for more info
        """

        refs = validator.extract_all_file_references(content)

        # Should find markdown links
        assert "docs/getting-started.md" in refs
        # Should find shell scripts
        assert "./install.sh" in refs
        # Should find config files
        assert "config/app.yaml" in refs
        # Should find markdown link URLs
        assert "https://docs.example.com" in refs

    def test_extract_all_file_references_no_duplicates(self, validator):
        """Test that duplicate references are removed."""
        content = """
        See README.md for info
        Check README.md again
        [Link](README.md)
        """

        refs = validator.extract_all_file_references(content)

        # Should only have one instance of README.md
        readme_count = refs.count("README.md")
        assert readme_count == 1

    def test_extract_all_file_references_ignores_non_file_paths(self, validator):
        """Test that non-file path patterns are not extracted."""
        content = """
        Some text with numbers like 1/2 or 3/4
        Math expressions: x/y + a/b
        Dates like 2024/01/15
        """

        refs = validator.extract_all_file_references(content)

        # Should not extract things that look like math or dates
        # These don't have file extensions so won't match
        assert "1/2" not in refs
        assert "3/4" not in refs

    def test_extract_all_file_references_shell_scripts(self, validator):
        """Test extracting shell script references."""
        content = """
        Run ./test.sh to test
        Execute ./lint.sh --fix for linting
        Use ../scripts/deploy.sh for deployment
        """

        refs = validator.extract_all_file_references(content)

        assert "./test.sh" in refs
        assert "./lint.sh" in refs
        assert "../scripts/deploy.sh" in refs

    def test_extract_all_file_references_nested_paths(self, validator):
        """Test extracting deeply nested file paths."""
        content = """
        Check src/utils/validators/link_validator.py
        See tests/unit/test_validators.py
        Config at config/environments/production/settings.yaml
        """

        refs = validator.extract_all_file_references(content)

        assert "src/utils/validators/link_validator.py" in refs
        assert "tests/unit/test_validators.py" in refs
        assert "config/environments/production/settings.yaml" in refs

    def test_extract_all_file_references_common_extensions(self, validator):
        """Test extracting files with common programming language extensions."""
        content = """
        Python: main.py, utils.py
        JavaScript: app.js, index.ts
        Markdown: README.md, CONTRIBUTING.md
        Config: .env, config.yaml, settings.json
        Shell: install.sh, setup.bash
        """

        refs = validator.extract_all_file_references(content)

        # Should detect all common file types
        assert "main.py" in refs
        assert "app.js" in refs
        assert "index.ts" in refs
        assert "README.md" in refs
        assert "config.yaml" in refs
        assert "settings.json" in refs
        assert "install.sh" in refs

    def test_extract_all_file_references_with_hyphens_and_underscores(self, validator):
        """Test extracting files with hyphens and underscores in names."""
        content = """
        Check getting-started.md
        Run test_validators.py
        See my-cool-script.sh
        Config in app_config.yaml
        """

        refs = validator.extract_all_file_references(content)

        assert "getting-started.md" in refs
        assert "test_validators.py" in refs
        assert "my-cool-script.sh" in refs
        assert "app_config.yaml" in refs
