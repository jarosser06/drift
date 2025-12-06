"""Tests for MarkdownLinkValidator."""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.markdown_validators import MarkdownLinkValidator


class TestMarkdownLinkValidator:
    """Tests for MarkdownLinkValidator."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return MarkdownLinkValidator()

    @pytest.fixture
    def tmp_path(self, tmp_path):
        """Provide tmp_path fixture."""
        return tmp_path

    def test_validation_passes_with_valid_local_links(self, validator, tmp_path):
        """Test that validation passes when all local links exist."""
        # Create files
        (tmp_path / "README.md").write_text("content")
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").write_text("content")

        test_file = tmp_path / "index.md"
        content = """# Index

[Link to README](README.md)
[Link to guide](docs/guide.md)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check markdown links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": True,
                "check_external_urls": False,
            },
        )

        result = validator.validate(rule, bundle)
        assert result is None

    def test_validation_fails_with_broken_local_links(self, validator, tmp_path):
        """Test that validation fails when local links are broken."""
        test_file = tmp_path / "index.md"
        content = """# Index

[Broken link](nonexistent.md)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check markdown links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": True,
                "check_external_urls": False,
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "nonexistent.md" in result.observed_issue
        assert "local file not found" in result.observed_issue

    def test_validation_checks_external_urls(self, validator, tmp_path):
        """Test that external URL validation can be enabled."""
        test_file = tmp_path / "index.md"
        content = """# Index

[External](https://example.com)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check external links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": False,
                "check_external_urls": True,
            },
        )

        # This should attempt to validate external URLs
        # We can't guarantee the result since it depends on network
        validator.validate(rule, bundle)
        # Just verify it runs without error

    def test_validation_skips_example_domains(self, validator, tmp_path):
        """Test that example domains are skipped by default."""
        test_file = tmp_path / "index.md"
        content = """# Index

[Example](https://example.com)
[Example org](https://example.org)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": False,
                "check_external_urls": True,
                "skip_example_domains": True,
            },
        )

        result = validator.validate(rule, bundle)
        # Should pass because example domains are skipped
        assert result is None

    def test_validation_custom_skip_patterns(self, validator, tmp_path):
        """Test custom skip patterns."""
        test_file = tmp_path / "index.md"
        content = """# Index

[Skip this](test.py)
[And this](config.yaml)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": True,
                "check_external_urls": False,
                "custom_skip_patterns": [r"\.py$", r"\.yaml$"],
            },
        )

        result = validator.validate(rule, bundle)
        # Should pass because these patterns are skipped
        assert result is None

    def test_validation_checks_code_blocks(self, validator, tmp_path):
        """Test that code block skipping can be configured."""
        test_file = tmp_path / "index.md"
        content = """# Index

```
[Link in code block](broken.md)
```
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": True,
                "check_external_urls": False,
                "skip_code_blocks": True,
            },
        )

        result = validator.validate(rule, bundle)
        # Should pass because code blocks are skipped
        assert result is None

    def test_validation_relative_to_project_root(self, validator, tmp_path):
        """Test that links relative to project root work."""
        # Create file at project root
        (tmp_path / "README.md").write_text("content")

        # Create subdirectory with file
        subdir = tmp_path / "docs"
        subdir.mkdir()
        test_file = subdir / "index.md"
        content = """# Index

[Root README](../README.md)
[Absolute](README.md)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="docs/index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": True,
                "check_external_urls": False,
            },
        )

        result = validator.validate(rule, bundle)
        # Both links should be found (relative to file dir and project root)
        assert result is None

    def test_computation_type(self, validator):
        """Test that computation_type is programmatic."""
        assert validator.computation_type == "programmatic"

    def test_validation_multiple_broken_links(self, validator, tmp_path):
        """Test that all broken links are reported."""
        test_file = tmp_path / "index.md"
        content = """# Index

[Broken 1](missing1.md)
[Broken 2](missing2.md)
[Broken 3](missing3.md)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check links",
            failure_message="Broken links found",
            expected_behavior="All links should be valid",
            params={
                "check_local_files": True,
                "check_external_urls": False,
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "missing1.md" in result.observed_issue
        assert "missing2.md" in result.observed_issue
        assert "missing3.md" in result.observed_issue

    def test_validation_resource_references_skill(self, validator, tmp_path):
        """Test validation of skill resource references.

        Resource references use the pattern in the link TEXT, not URL.
        Example: [skill:test-skill](https://example.com)
        """
        # Create actual skill
        skill_dir = tmp_path / ".claude" / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("# Test Skill")

        test_file = tmp_path / "index.md"
        content = """# Index

[skill:test-skill](https://example.com)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="command",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check resource references",
            failure_message="Broken resource references found",
            expected_behavior="All resource references should be valid",
            params={
                "check_local_files": False,
                "check_external_urls": False,
                "check_resource_refs": True,
                "resource_patterns": [r"skill:([a-zA-Z0-9-_]+)"],
            },
        )

        result = validator.validate(rule, bundle)
        # Should pass because test-skill exists
        assert result is None

    def test_validation_resource_references_missing_skill(self, validator, tmp_path):
        """Test validation fails for missing skill resource."""
        test_file = tmp_path / "index.md"
        content = """# Index

[skill:missing-skill](some-url.md)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="command",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check resource references",
            failure_message="Broken resource references found",
            expected_behavior="All resource references should be valid",
            params={
                "check_local_files": False,
                "check_external_urls": False,
                "check_resource_refs": True,
                "resource_patterns": [r"skill:([a-zA-Z0-9-_]+)"],
            },
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "missing-skill" in result.observed_issue
        assert "skill reference not found" in result.observed_issue

    def test_validation_resource_references_command(self, validator, tmp_path):
        """Test validation of command resource references."""
        # Create actual command
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "test-cmd.md").write_text("# Test Command")

        test_file = tmp_path / "index.md"
        content = """# Index

[/test-cmd](https://example.com)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check resource references",
            failure_message="Broken resource references found",
            expected_behavior="All resource references should be valid",
            params={
                "check_local_files": False,
                "check_external_urls": False,
                "check_resource_refs": True,
                "resource_patterns": [r"/([a-zA-Z0-9-_]+)"],
            },
        )

        result = validator.validate(rule, bundle)
        # Should pass because test-cmd exists
        assert result is None

    def test_validation_resource_references_agent(self, validator, tmp_path):
        """Test validation of agent resource references."""
        # Create actual agent
        agent_dir = tmp_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)
        (agent_dir / "test-agent.md").write_text("# Test Agent")

        test_file = tmp_path / "index.md"
        content = """# Index

[Test Agent](agent:test-agent)
"""
        test_file.write_text(content)

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[
                DocumentFile(
                    relative_path="index.md",
                    content=content,
                    file_path=str(test_file),
                )
            ],
        )

        rule = ValidationRule(
            rule_type="core:markdown_link",
            description="Check resource references",
            failure_message="Broken resource references found",
            expected_behavior="All resource references should be valid",
            params={
                "check_local_files": False,
                "check_external_urls": False,
                "check_resource_refs": True,
                "resource_patterns": [r"agent:([a-zA-Z0-9-_]+)"],
            },
        )

        result = validator.validate(rule, bundle)
        # Should pass because test-agent exists
        assert result is None

    def test_guess_resource_type_from_pattern(self, validator):
        """Test _guess_resource_type method."""
        # Test skill pattern
        assert validator._guess_resource_type("skill:([^)]+)") == "skill"

        # Test command pattern (contains /)
        assert validator._guess_resource_type("/([^)]+)") == "command"

        # Test agent pattern
        assert validator._guess_resource_type("agent:([^)]+)") == "agent"

        # Test unknown pattern
        assert validator._guess_resource_type("unknown:([^)]+)") is None
