"""Unit tests for link validation."""

from unittest.mock import Mock, patch

import pytest
import requests

from drift.utils.link_validator import LinkValidator


class TestLinkValidator:
    """Test cases for LinkValidator class."""

    @pytest.fixture
    def validator(self):
        """Create a LinkValidator instance with filtering disabled for backward compatibility."""
        return LinkValidator(
            skip_example_domains=False,
            skip_code_blocks=False,
            skip_placeholder_paths=False,
            custom_skip_patterns=[],
        )

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
        """Test that directories are valid paths."""
        base_path = temp_project

        is_valid = validator.validate_local_file(".claude/skills/test-skill", base_path)

        # Directories should be considered valid (changed to support directory links)
        assert is_valid is True

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
        content = "Check /usr/local/bin/script or /etc/config.yaml standalone.md"

        refs = validator.extract_all_file_references(content)

        # Absolute system paths should NOT be extracted (they're usually examples)
        assert "/usr/local/bin/script" not in refs
        assert "/etc/config.yaml" not in refs
        assert "etc/config.yaml" not in refs
        assert "config.yaml" not in refs  # Not extracted from /etc/config.yaml
        # But truly standalone files should be extracted
        assert "standalone.md" in refs

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


class TestCodeBlockFiltering:
    """Test cases for code block filtering."""

    def test_skip_fenced_code_blocks(self):
        """Test that links in fenced code blocks are skipped."""
        content = """
# Documentation

Here's a link to [real file](./README.md)

```python
# This is example code
link = "[example](http://example.com)"
file = "path/to/example.py"
```

And another [real link](./config.yaml)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./README.md" in refs
        assert "./config.yaml" in refs
        assert "http://example.com" not in refs
        assert "path/to/example.py" not in refs

    def test_skip_indented_code_blocks(self):
        """Test that links in indented code blocks are skipped."""
        content = """
# Documentation

[Real link](./file.md)

    # This is an indented code block
    [example](http://example.com)
    path/to/example.py

Back to normal text with [another link](./other.md)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./file.md" in refs
        assert "./other.md" in refs
        assert "http://example.com" not in refs
        assert "path/to/example.py" not in refs

    def test_code_block_filtering_disabled(self):
        """Test that code blocks are processed when filtering is disabled."""
        content = """
```
[example](http://example.com)
```
"""
        validator = LinkValidator(skip_code_blocks=False, skip_example_domains=False)
        refs = validator.extract_all_file_references(content)

        assert "http://example.com" in refs

    def test_multiple_fenced_code_blocks(self):
        """Test handling of multiple fenced code blocks."""
        content = """
[real](./file.md)

```python
code1 = "path/to/code1.py"
```

[another](./file2.md)

```bash
./script.sh
```

[third](./file3.md)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./file.md" in refs
        assert "./file2.md" in refs
        assert "./file3.md" in refs
        assert "path/to/code1.py" not in refs
        assert "./script.sh" not in refs

    def test_fenced_code_with_language_specifier(self):
        """Test fenced code blocks with language specifiers."""
        content = """
```python
example.com
```

```typescript
path/to/file.ts
```

```json
{
  "url": "http://example.com"
}
```
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "example.com" not in refs
        assert "path/to/file.ts" not in refs
        assert "http://example.com" not in refs

    def test_mixed_indented_and_fenced(self):
        """Test document with both indented and fenced code blocks."""
        content = """
[real](./doc.md)

```
fenced example.py
```

    indented example.sh

[another](./file.md)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./doc.md" in refs
        assert "./file.md" in refs
        assert "example.py" not in refs
        assert "example.sh" not in refs


class TestExampleDomainFiltering:
    """Test cases for example domain filtering."""

    def test_skip_example_com(self):
        """Test that example.com is skipped."""
        content = "[example](http://example.com)"
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "http://example.com" not in refs

    def test_skip_example_org(self):
        """Test that example.org is skipped."""
        content = "[example](https://example.org)"
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "https://example.org" not in refs

    def test_skip_localhost(self):
        """Test that localhost is skipped."""
        content = """
[local](http://localhost:8080)
[ip](http://127.0.0.1:3000)
"""
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "http://localhost:8080" not in refs
        assert "http://127.0.0.1:3000" not in refs

    def test_skip_subdomain_of_example(self):
        """Test that subdomains of example.com are skipped."""
        content = """
[api](http://api.example.com)
[www](https://www.example.org)
[sub](http://sub.domain.example.net)
"""
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "http://api.example.com" not in refs
        assert "https://www.example.org" not in refs
        assert "http://sub.domain.example.net" not in refs

    def test_skip_mailto_with_example_domain(self):
        """Test that mailto links are kept (categorized as unknown)."""
        content = "[email](mailto:user@example.com)"
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        # Mailto links are kept: categorized as "unknown" and
        # skipped during validation
        assert "mailto:user@example.com" in refs

    def test_example_domain_filtering_disabled(self):
        """Test that example domains are kept when filtering is disabled."""
        content = "[example](http://example.com)"
        validator = LinkValidator(skip_example_domains=False)
        refs = validator.extract_all_file_references(content)

        assert "http://example.com" in refs

    def test_real_domain_not_filtered(self):
        """Test that real domains are not filtered."""
        content = """
[google](https://google.com)
[github](https://github.com)
[docs](https://docs.python.org)
"""
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "https://google.com" in refs
        assert "https://github.com" in refs
        assert "https://docs.python.org" in refs

    def test_skip_test_com(self):
        """Test that test.com is skipped."""
        content = "[test](http://test.com)"
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "http://test.com" not in refs

    def test_example_with_port(self):
        """Test that example domains with ports are skipped."""
        content = "[example](http://example.com:8080/path)"
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "http://example.com:8080/path" not in refs


class TestPlaceholderPathFiltering:
    """Test cases for placeholder path filtering."""

    def test_skip_path_to_pattern(self):
        """Test that path/to/ pattern is skipped."""
        content = """
Check path/to/file.py
Also path/to/config.yaml
"""
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        assert "path/to/file.py" not in refs
        assert "path/to/config.yaml" not in refs

    def test_skip_your_project_pattern(self):
        """Test that your-* pattern is skipped."""
        content = """
See your-project/src/main.py
Check your-app/config.json
"""
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        assert "your-project/src/main.py" not in refs
        assert "your-app/config.json" not in refs

    def test_skip_my_pattern(self):
        """Test that my-* pattern is skipped."""
        content = "Check my-app/src/index.ts"
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        assert "my-app/src/index.ts" not in refs

    def test_skip_template_variables(self):
        """Test that template variable patterns are skipped."""
        content = """
{variable}/path/file.py
${VAR}/path/file.js
<something>/path/file.md
"""
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        # These should all be filtered out
        for ref in refs:
            assert "{" not in ref
            assert "$" not in ref
            assert "<" not in ref

    def test_placeholder_filtering_disabled(self):
        """Test that placeholders are kept when filtering is disabled."""
        content = "path/to/file.py"
        validator = LinkValidator(skip_placeholder_paths=False)
        refs = validator.extract_all_file_references(content)

        assert "path/to/file.py" in refs

    def test_real_paths_not_filtered(self):
        """Test that real-looking paths are not filtered."""
        content = """
src/main.py
tests/unit/test_file.py
docs/api/reference.md
"""
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        assert "src/main.py" in refs
        assert "tests/unit/test_file.py" in refs
        assert "docs/api/reference.md" in refs


class TestCustomPatternFiltering:
    """Test cases for custom pattern filtering."""

    def test_custom_pattern_single(self):
        """Test filtering with a single custom pattern."""
        content = """
[keep](./file.md)
[skip](./vendor/lib.js)
[also-keep](./src/main.py)
"""
        validator = LinkValidator(custom_skip_patterns=[r"vendor/"])
        refs = validator.extract_all_file_references(content)

        assert "./file.md" in refs
        assert "./src/main.py" in refs
        assert "./vendor/lib.js" not in refs

    def test_custom_pattern_multiple(self):
        """Test filtering with multiple custom patterns."""
        content = """
[keep](./src/file.py)
[skip1](./node_modules/package.json)
[skip2](./vendor/lib.js)
[skip3](./temp.tmp)
"""
        validator = LinkValidator(custom_skip_patterns=[r"node_modules/", r"vendor/", r"\.tmp$"])
        refs = validator.extract_all_file_references(content)

        assert "./src/file.py" in refs
        assert "./node_modules/package.json" not in refs
        assert "./vendor/lib.js" not in refs
        assert "./temp.tmp" not in refs

    def test_custom_pattern_regex(self):
        """Test that custom patterns support full regex."""
        content = """
[file1](./test_file.py)
[file2](./example_test.py)
[file3](./main.py)
"""
        validator = LinkValidator(custom_skip_patterns=[r".*test.*\.py$"])
        refs = validator.extract_all_file_references(content)

        assert "./main.py" in refs
        assert "./test_file.py" not in refs
        assert "./example_test.py" not in refs

    def test_invalid_regex_ignored(self):
        """Test that invalid regex patterns are silently ignored."""
        content = "[file](./test.py)"
        # Invalid regex pattern - unclosed bracket
        validator = LinkValidator(custom_skip_patterns=[r"[unclosed"])
        refs = validator.extract_all_file_references(content)

        # Should not crash, file should be kept
        assert "./test.py" in refs

    def test_empty_custom_patterns(self):
        """Test that empty custom patterns list works."""
        content = "[file](./test.py)"
        validator = LinkValidator(custom_skip_patterns=[])
        refs = validator.extract_all_file_references(content)

        assert "./test.py" in refs

    def test_custom_pattern_on_urls(self):
        """Test custom patterns work on URLs too."""
        content = """
[keep](https://github.com)
[skip](https://internal.company.com)
"""
        validator = LinkValidator(custom_skip_patterns=[r"internal\.company\.com"])
        refs = validator.extract_all_file_references(content)

        assert "https://github.com" in refs
        assert "https://internal.company.com" not in refs


class TestCombinedFiltering:
    """Test cases for combined filtering scenarios."""

    def test_all_filters_enabled(self):
        """Test with all filtering options enabled."""
        content = """
# Real content
[real](./README.md)

```python
# Example code
link = "http://example.com"
path = "path/to/example.py"
```

[localhost](http://localhost:8080)
your-project/config.yaml
[vendor](./vendor/lib.js)

[another-real](./src/main.py)
"""
        validator = LinkValidator(
            skip_code_blocks=True,
            skip_example_domains=True,
            skip_placeholder_paths=True,
            custom_skip_patterns=[r"vendor/"],
        )
        refs = validator.extract_all_file_references(content)

        # Should keep real files
        assert "./README.md" in refs
        assert "./src/main.py" in refs

        # Should filter out everything else
        assert "http://example.com" not in refs
        assert "path/to/example.py" not in refs
        assert "http://localhost:8080" not in refs
        assert "your-project/config.yaml" not in refs
        assert "./vendor/lib.js" not in refs

    def test_selective_filtering(self):
        """Test with only some filters enabled."""
        content = """
http://example.com
path/to/file.py
./vendor/lib.js
"""
        # Only skip example domains
        validator = LinkValidator(
            skip_code_blocks=False,
            skip_example_domains=True,
            skip_placeholder_paths=False,
            custom_skip_patterns=[],
        )
        refs = validator.extract_all_file_references(content)

        assert "http://example.com" not in refs
        assert "path/to/file.py" in refs
        assert "./vendor/lib.js" in refs

    def test_no_filtering(self):
        """Test with all filtering disabled."""
        content = """
```
[example](http://example.com)
```
path/to/file.py
[localhost](http://localhost)
"""
        validator = LinkValidator(
            skip_code_blocks=False,
            skip_example_domains=False,
            skip_placeholder_paths=False,
            custom_skip_patterns=[],
        )
        refs = validator.extract_all_file_references(content)

        assert "http://example.com" in refs
        assert "path/to/file.py" in refs
        assert "http://localhost" in refs

    def test_real_world_cicd_example(self):
        """Test the real-world example from cicd.md."""
        content = """
[project]
name = "drift"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
"""
        validator = LinkValidator(
            skip_code_blocks=True, skip_example_domains=True, skip_placeholder_paths=True
        )
        refs = validator.extract_all_file_references(content)

        # The example email should be filtered out
        assert "your.email@example.com" not in refs


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""

    def test_nested_code_blocks_markdown(self):
        """Test handling of nested markdown in code blocks."""
        content = """
# Docs

```markdown
# Example Document
[link](http://example.com)
See path/to/file.py
```

[real](./actual.md)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./actual.md" in refs
        assert "http://example.com" not in refs
        assert "path/to/file.py" not in refs

    def test_code_block_with_no_language(self):
        """Test fenced code blocks without language specifier."""
        content = """
```
example.com
./test.sh
```

[real](./file.md)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./file.md" in refs
        assert "example.com" not in refs
        assert "./test.sh" not in refs

    def test_partial_code_block_markers(self):
        """Test that partial code block markers don't break filtering."""
        content = """
This has ``` inline backticks but [link](./file.md) should work

```
code block
example.com
```

More text [another](./other.md)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./file.md" in refs
        assert "./other.md" in refs
        assert "example.com" not in refs

    def test_example_domain_with_path_and_query(self):
        """Test example domains with complex URLs."""
        content = """
[ex1](http://example.com/path/to/page?query=1)
[ex2](https://api.example.org:8080/v1/endpoint#section)
[ex3](http://sub.example.net/path)
"""
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "http://example.com/path/to/page?query=1" not in refs
        assert "https://api.example.org:8080/v1/endpoint#section" not in refs
        assert "http://sub.example.net/path" not in refs

    def test_localhost_variations(self):
        """Test various localhost and IP address formats."""
        content = """
[l1](http://localhost)
[l2](http://localhost:3000)
[l3](http://127.0.0.1:8080)
[l4](http://0.0.0.0:5000)
[real](http://192.168.1.1)
"""
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "http://localhost" not in refs
        assert "http://localhost:3000" not in refs
        assert "http://127.0.0.1:8080" not in refs
        assert "http://0.0.0.0:5000" not in refs
        # Real local network IP should be kept
        assert "http://192.168.1.1" in refs

    def test_placeholder_with_real_project_paths(self):
        """Test that real project paths aren't filtered as placeholders."""
        content = """
src/utils/helper.py
tests/integration/test_api.py
docs/guides/installation.md
path/to/example.py
your-project/src/main.py
"""
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        # Real-looking paths should be kept
        assert "src/utils/helper.py" in refs
        assert "tests/integration/test_api.py" in refs
        assert "docs/guides/installation.md" in refs

        # Placeholders should be filtered
        assert "path/to/example.py" not in refs
        assert "your-project/src/main.py" not in refs

    def test_template_variable_variations(self):
        """Test various template variable formats."""
        content = """
{project}/src/main.py
${HOME}/config.yaml
<username>/settings.json
{{variable}}/path/file.py
$VAR/path/file.py
"""
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        # All template variables should be filtered
        for ref in refs:
            assert "{" not in ref
            assert "$" not in ref
            assert "<" not in ref

    def test_custom_pattern_case_sensitivity(self):
        """Test that custom patterns respect case sensitivity."""
        content = """
[f1](./Vendor/lib.js)
[f2](./vendor/lib.js)
[f3](./VENDOR/lib.js)
"""
        # Case-sensitive pattern
        validator = LinkValidator(custom_skip_patterns=[r"vendor/"])
        refs = validator.extract_all_file_references(content)

        assert "./Vendor/lib.js" in refs  # Capital V not matched
        assert "./vendor/lib.js" not in refs  # Lowercase matched
        assert "./VENDOR/lib.js" in refs  # All caps not matched

    def test_custom_pattern_with_anchors(self):
        """Test custom patterns with regex anchors."""
        content = """
./test_file.py
./file_test.py
./test.py
./my_test.py
"""
        # Only files starting with "test_"
        validator = LinkValidator(custom_skip_patterns=[r"^\.\/test_"])
        refs = validator.extract_all_file_references(content)

        assert "./test_file.py" not in refs
        assert "./file_test.py" in refs
        assert "./test.py" in refs
        assert "./my_test.py" in refs

    def test_mixed_filtering_priority(self):
        """Test that filters work correctly together."""
        content = """
```yaml
example.com
path/to/file.py
```

[ex](http://example.com/real)
path/to/another.py
./vendor/lib.js
./src/main.py
"""
        validator = LinkValidator(
            skip_code_blocks=True,
            skip_example_domains=True,
            skip_placeholder_paths=True,
            custom_skip_patterns=[r"vendor/"],
        )
        refs = validator.extract_all_file_references(content)

        # Should only keep real paths
        assert "./src/main.py" in refs

        # Everything else filtered
        assert "http://example.com/real" not in refs  # example domain
        assert "path/to/another.py" not in refs  # placeholder
        assert "./vendor/lib.js" not in refs  # custom pattern

    def test_empty_content(self):
        """Test handling of empty content."""
        validator = LinkValidator()
        refs = validator.extract_all_file_references("")

        assert refs == []

    def test_only_code_blocks(self):
        """Test content that is entirely code blocks."""
        content = """
```python
import os
file = "test.py"
```

```bash
./script.sh
```
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert refs == []

    def test_unicode_in_links(self):
        """Test handling of Unicode characters in links."""
        content = """
[file](./文件.md)
[doc](./tëst.py)
[real](./file.md)
"""
        validator = LinkValidator()
        refs = validator.extract_all_file_references(content)

        # All should be extracted (Unicode support)
        assert "./file.md" in refs

    def test_whitespace_in_paths(self):
        """Test paths with various whitespace."""
        content = """
[spaces](./path with spaces/file.md)
[tabs](./path\twith\ttabs.py)
"""
        validator = LinkValidator()
        refs = validator.extract_all_file_references(content)

        # Current implementation may not handle spaces well,
        # but shouldn't crash
        assert isinstance(refs, list)

    def test_example_domain_false_positives(self):
        """Test that domains containing 'example' aren't over-filtered."""
        content = """
[good1](https://myexample.com)
[good2](https://example-site.com)
[good3](https://exampleproject.org)
[bad](https://example.com)
[bad2](https://sub.example.org)
"""
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        # Only exact example.com/org/net domains should be filtered
        assert "https://myexample.com" in refs
        assert "https://example-site.com" in refs
        assert "https://exampleproject.org" in refs
        assert "https://example.com" not in refs
        assert "https://sub.example.org" not in refs

    def test_placeholder_path_false_positives(self):
        """Test that paths containing placeholder keywords aren't over-filtered."""
        content = """
mypath/to/file.py
src/path/utils.py
tests/yourtest.py
myproject/src/main.py
your-tests/test.py
"""
        validator = LinkValidator(skip_placeholder_paths=True)
        refs = validator.extract_all_file_references(content)

        # Only exact placeholder patterns should be filtered
        assert "src/path/utils.py" in refs  # "path" mid-word OK
        assert "tests/yourtest.py" in refs  # "your" mid-word OK
        assert "myproject/src/main.py" in refs  # "my" without hyphen OK
        assert "your-tests/test.py" not in refs  # "your-" matches pattern

    def test_multiple_links_same_line(self):
        """Test multiple links on the same line."""
        content = "[f1](./a.md) and [f2](./b.md) and [ex](http://example.com)"
        validator = LinkValidator(skip_example_domains=True)
        refs = validator.extract_all_file_references(content)

        assert "./a.md" in refs
        assert "./b.md" in refs
        assert "http://example.com" not in refs

    def test_code_block_edge_case_unclosed(self):
        """Test handling of unclosed code blocks."""
        content = """
[real](./file.md)

```python
this code block is never closed
path/to/example.py
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        # Unclosed blocks should still be handled gracefully
        # (regex should match to end of string)
        assert "./file.md" in refs
        assert "path/to/example.py" not in refs

    def test_indented_code_with_tabs_and_spaces(self):
        """Test indented code blocks with both tabs and spaces."""
        content = """
[real](./file.md)

    space-indented example.com

\tTab-indented path/to/file.py

[another](./other.md)
"""
        validator = LinkValidator(skip_code_blocks=True)
        refs = validator.extract_all_file_references(content)

        assert "./file.md" in refs
        assert "./other.md" in refs
        # Both should be filtered as code blocks
        assert "example.com" not in refs
        # path/to is also a placeholder pattern
        assert "path/to/file.py" not in refs

    def test_filter_default_initialization(self):
        """Test that default initialization enables all filters."""
        content = """
```
example.com
```
[ex](http://localhost)
path/to/file.py
"""
        validator = LinkValidator()  # All defaults should be True
        refs = validator.extract_all_file_references(content)

        # All should be filtered with defaults
        assert "example.com" not in refs
        assert "http://localhost" not in refs
        assert "path/to/file.py" not in refs

    def test_selective_filter_combinations(self):
        """Test various combinations of enabled/disabled filters."""
        content = """
```
code-block-link.md
```
[ex](http://example.com)
path/to/placeholder.py
./vendor/lib.js
./src/real.py
"""
        # Only code blocks
        v1 = LinkValidator(
            skip_code_blocks=True,
            skip_example_domains=False,
            skip_placeholder_paths=False,
        )
        refs1 = v1.extract_all_file_references(content)
        assert "http://example.com" in refs1
        assert "path/to/placeholder.py" in refs1

        # Only example domains
        v2 = LinkValidator(
            skip_code_blocks=False,
            skip_example_domains=True,
            skip_placeholder_paths=False,
        )
        refs2 = v2.extract_all_file_references(content)
        assert "http://example.com" not in refs2
        assert "path/to/placeholder.py" in refs2

        # Only placeholders
        v3 = LinkValidator(
            skip_code_blocks=False,
            skip_example_domains=False,
            skip_placeholder_paths=True,
        )
        refs3 = v3.extract_all_file_references(content)
        assert "http://example.com" in refs3
        assert "path/to/placeholder.py" not in refs3
