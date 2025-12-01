"""Unit tests for YAML frontmatter parsing."""

import pytest
import yaml

from drift.utils.frontmatter import extract_frontmatter


class TestExtractFrontmatter:
    """Test cases for extract_frontmatter function."""

    def test_valid_frontmatter(self):
        """Test extraction of valid YAML frontmatter."""
        content = """---
name: my-skill
description: A test skill
skills:
  - other-skill
  - another-skill
---
# Main content here
"""
        result = extract_frontmatter(content)

        assert result is not None
        assert result["name"] == "my-skill"
        assert result["description"] == "A test skill"
        assert result["skills"] == ["other-skill", "another-skill"]

    def test_no_frontmatter(self):
        """Test content without frontmatter."""
        content = "# Just a regular markdown file\nNo frontmatter here."

        result = extract_frontmatter(content)

        assert result is None

    def test_empty_frontmatter(self):
        """Test empty frontmatter block."""
        content = """---
---
# Content
"""
        result = extract_frontmatter(content)

        # Empty YAML should return None or empty dict
        assert result is None or result == {}

    def test_frontmatter_with_whitespace(self):
        """Test frontmatter with extra whitespace."""
        content = """---
name: test
---
Content"""
        result = extract_frontmatter(content)

        assert result is not None
        assert result["name"] == "test"

    def test_malformed_yaml(self):
        """Test that malformed YAML raises an error."""
        content = """---
name: test
  invalid: indentation
  more: problems
---
Content"""
        with pytest.raises(yaml.YAMLError):
            extract_frontmatter(content)

    def test_frontmatter_not_at_start(self):
        """Test that frontmatter not at start is ignored."""
        content = """Some content first

---
name: test
---
More content"""
        result = extract_frontmatter(content)

        assert result is None

    def test_single_dash_markers(self):
        """Test that single dash lines don't match."""
        content = """-
name: test
-
Content"""
        result = extract_frontmatter(content)

        assert result is None

    def test_nested_structure(self):
        """Test frontmatter with nested structures."""
        content = """---
name: complex
metadata:
  author: test
  version: 1.0
  tags:
    - tag1
    - tag2
skills:
  - skill1
---
Content"""
        result = extract_frontmatter(content)

        assert result is not None
        assert result["name"] == "complex"
        assert result["metadata"]["author"] == "test"
        assert result["metadata"]["tags"] == ["tag1", "tag2"]

    def test_frontmatter_with_colon_in_value(self):
        """Test frontmatter with colons in string values."""
        content = """---
description: "This: has colons: in it"
url: "https://example.com"
---
Content"""
        result = extract_frontmatter(content)

        assert result is not None
        assert result["description"] == "This: has colons: in it"
        assert result["url"] == "https://example.com"

    def test_boolean_and_numeric_values(self):
        """Test frontmatter with various data types."""
        content = """---
enabled: true
disabled: false
count: 42
ratio: 3.14
---
Content"""
        result = extract_frontmatter(content)

        assert result is not None
        assert result["enabled"] is True
        assert result["disabled"] is False
        assert result["count"] == 42
        assert result["ratio"] == 3.14

    def test_multiline_string(self):
        """Test frontmatter with multiline string."""
        content = """---
description: |
  This is a multiline
  description that spans
  multiple lines
---
Content"""
        result = extract_frontmatter(content)

        assert result is not None
        assert "multiline" in result["description"]
