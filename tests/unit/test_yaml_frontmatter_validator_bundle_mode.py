"""Tests for YamlFrontmatterValidator bundle mode."""

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators.core.format_validators import YamlFrontmatterValidator


class TestYamlFrontmatterValidatorBundleMode:
    """Tests for YamlFrontmatterValidator in bundle mode (no file_path)."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return YamlFrontmatterValidator(loader=None)

    def test_bundle_mode_all_files_valid(self, validator, tmp_path):
        """Test that validation passes when all files in bundle have valid frontmatter."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "agent1.md"),
                relative_path=".claude/agents/agent1.md",
                content="""---
name: agent1
description: First test agent
model: sonnet
---
Content
""",
            ),
            DocumentFile(
                file_path=str(tmp_path / "agent2.md"),
                relative_path=".claude/agents/agent2.md",
                content="""---
name: agent2
description: Second test agent
model: haiku
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="agent",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate agent frontmatter",
            params={"required_fields": ["name", "description", "model"]},
            failure_message="Missing required fields",
            expected_behavior="Should have all required fields",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # No failures

    def test_bundle_mode_one_file_missing_fields(self, validator, tmp_path):
        """Test that validation fails when one file is missing required fields."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "agent1.md"),
                relative_path=".claude/agents/agent1.md",
                content="""---
name: agent1
description: First test agent
model: sonnet
---
Content
""",
            ),
            DocumentFile(
                file_path=str(tmp_path / "agent2.md"),
                relative_path=".claude/agents/agent2.md",
                content="""---
description: Second test agent
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="agent",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate agent frontmatter",
            params={"required_fields": ["name", "description", "model"]},
            failure_message="Missing required fields",
            expected_behavior="Should have all required fields",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert ".claude/agents/agent2.md" in result.observed_issue
        assert "Missing required frontmatter fields: name, model" in result.observed_issue
        assert ".claude/agents/agent2.md" in result.file_paths

    def test_bundle_mode_multiple_files_with_errors(self, validator, tmp_path):
        """Test that validation reports all files with errors."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "agent1.md"),
                relative_path=".claude/agents/agent1.md",
                content="""---
name: agent1
---
Content
""",
            ),
            DocumentFile(
                file_path=str(tmp_path / "agent2.md"),
                relative_path=".claude/agents/agent2.md",
                content="""---
description: Second test agent
---
Content
""",
            ),
            DocumentFile(
                file_path=str(tmp_path / "agent3.md"),
                relative_path=".claude/agents/agent3.md",
                content="""---
name: agent3
description: Third test agent
model: opus
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="agent",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate agent frontmatter",
            params={"required_fields": ["name", "description", "model"]},
            failure_message="Missing required fields",
            expected_behavior="Should have all required fields",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert ".claude/agents/agent1.md" in result.observed_issue
        assert ".claude/agents/agent2.md" in result.observed_issue
        assert ".claude/agents/agent3.md" not in result.observed_issue
        assert len(result.file_paths) == 2

    def test_bundle_mode_no_frontmatter(self, validator, tmp_path):
        """Test that validation fails when file has no frontmatter."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "command.md"),
                relative_path=".claude/commands/command.md",
                content="# Command\n\nNo frontmatter here",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="command",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate command frontmatter",
            params={"required_fields": ["description"]},
            failure_message="Missing frontmatter",
            expected_behavior="Should have frontmatter",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "No YAML frontmatter found" in result.observed_issue

    def test_bundle_mode_invalid_yaml(self, validator, tmp_path):
        """Test that validation fails when YAML is invalid."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "command.md"),
                relative_path=".claude/commands/command.md",
                content="""---
description: [unclosed bracket
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="command",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate command frontmatter",
            params={"required_fields": ["description"]},
            failure_message="Invalid YAML",
            expected_behavior="Should have valid YAML",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Invalid YAML in frontmatter" in result.observed_issue

    def test_bundle_mode_with_schema_validation(self, validator, tmp_path):
        """Test bundle mode with JSON schema validation."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "agent.md"),
                relative_path=".claude/agents/agent.md",
                content="""---
name: test-agent
description: Test agent with valid schema
model: sonnet
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="agent",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "pattern": "^[a-z][a-z0-9-]*$"},
                "description": {"type": "string", "minLength": 10},
                "model": {"type": "string", "enum": ["sonnet", "opus", "haiku"]},
            },
            "required": ["name", "description", "model"],
        }

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate agent frontmatter with schema",
            params={"required_fields": ["name", "description", "model"], "schema": schema},
            failure_message="Schema validation failed",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Should pass

    def test_bundle_mode_schema_validation_failure(self, validator, tmp_path):
        """Test that schema validation catches invalid values."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "agent.md"),
                relative_path=".claude/agents/agent.md",
                content="""---
name: InvalidName
description: Too short
model: invalid_model
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="agent",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "pattern": "^[a-z][a-z0-9-]*$"},
                "description": {"type": "string", "minLength": 10},
                "model": {"type": "string", "enum": ["sonnet", "opus", "haiku"]},
            },
            "required": ["name", "description", "model"],
        }

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate agent frontmatter with schema",
            params={"schema": schema},
            failure_message="Schema validation failed",
            expected_behavior="Should match schema",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "schema validation failed" in result.observed_issue.lower()

    def test_bundle_mode_empty_bundle(self, validator, tmp_path):
        """Test that validation passes for empty bundle."""
        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="agent",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate agent frontmatter",
            params={"required_fields": ["name", "description", "model"]},
            failure_message="Missing required fields",
            expected_behavior="Should have all required fields",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # No files to fail

    def test_bundle_mode_command_validation(self, validator, tmp_path):
        """Test validation for command files."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "test.md"),
                relative_path=".claude/commands/test.md",
                content="""---
description: Run pytest tests
skills:
  - testing
  - linting
---
Content
""",
            ),
            DocumentFile(
                file_path=str(tmp_path / "lint.md"),
                relative_path=".claude/commands/lint.md",
                content="""---
description: Run linters and formatters
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="command",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate command frontmatter",
            params={"required_fields": ["description"]},
            failure_message="Missing description",
            expected_behavior="Should have description",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Both files valid

    def test_bundle_mode_command_missing_description(self, validator, tmp_path):
        """Test that command validation fails when description is missing."""
        files = [
            DocumentFile(
                file_path=str(tmp_path / "test.md"),
                relative_path=".claude/commands/test.md",
                content="""---
skills:
  - testing
---
Content
""",
            ),
        ]

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="command",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=files,
        )

        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate command frontmatter",
            params={"required_fields": ["description"]},
            failure_message="Missing description",
            expected_behavior="Should have description",
        )

        result = validator.validate(rule, bundle)
        assert result is not None
        assert "Missing required frontmatter fields: description" in result.observed_issue

    def test_bundle_mode_backward_compatible_with_file_path(self, validator, tmp_path):
        """Test that bundle mode is backward compatible with file_path parameter."""
        # Create a test file
        test_file = tmp_path / "test.md"
        test_file.write_text(
            """---
name: test
description: Test file
model: sonnet
---
Content
"""
        )

        bundle = DocumentBundle(
            bundle_id="test",
            bundle_type="agent",
            bundle_strategy="individual",
            project_path=tmp_path,
            files=[],  # Empty files list
        )

        # Rule with file_path (legacy mode)
        rule = ValidationRule(
            rule_type=ValidationType.YAML_FRONTMATTER,
            description="Validate agent frontmatter",
            file_path="test.md",
            params={"required_fields": ["name", "description", "model"]},
            failure_message="Missing required fields",
            expected_behavior="Should have all required fields",
        )

        result = validator.validate(rule, bundle)
        assert result is None  # Should pass in legacy mode
