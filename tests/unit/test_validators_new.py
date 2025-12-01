"""Unit tests for new validators (DependencyDuplicateValidator, MarkdownLinkValidator)."""

from unittest.mock import Mock, patch

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import DependencyDuplicateValidator, MarkdownLinkValidator


def create_bundle(files, project_path, bundle_id="test-bundle"):
    """Create a DocumentBundle with required fields."""
    return DocumentBundle(
        bundle_id=bundle_id,
        bundle_type="project",
        bundle_strategy="individual",
        files=files,
        project_path=project_path,
    )


class TestDependencyDuplicateValidator:
    """Test cases for DependencyDuplicateValidator class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        # Create .claude directory structure
        (tmp_path / ".claude" / "commands").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-a").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-b").mkdir(parents=True)
        (tmp_path / ".claude" / "skills" / "skill-c").mkdir(parents=True)

        return tmp_path

    @pytest.fixture
    def mock_loader(self, temp_project):
        """Create a mock loader with project path."""
        loader = Mock()
        loader.project_path = temp_project
        return loader

    @pytest.fixture
    def validator(self, mock_loader):
        """Create a DependencyDuplicateValidator instance."""
        return DependencyDuplicateValidator(mock_loader)

    @pytest.fixture
    def validation_rule(self):
        """Create a validation rule."""
        return ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for duplicate dependencies",
            failure_message="Found duplicate dependencies",
            expected_behavior="No duplicate dependencies",
            params={"resource_dirs": [".claude/commands", ".claude/skills", ".claude/agents"]},
        )

    def test_initialization(self, validator, mock_loader):
        """Test validator initialization."""
        assert validator.loader == mock_loader

    def test_validate_no_duplicates(self, validator, validation_rule, temp_project):
        """Test validation when there are no duplicates."""
        # Create command that depends on skill-a
        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
---
"""
        )

        # Create skill-a that depends on skill-b
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
"""
        )

        # Create skill-b with no deps
        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text(
            """---
name: skill-b
---
"""
        )

        # Create bundle with all files
        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="cmd.md",
                    file_path=command_file,
                    content=command_file.read_text(),
                ),
                DocumentFile(
                    relative_path="skill-a/SKILL.md",
                    file_path=skill_a_file,
                    content=skill_a_file.read_text(),
                ),
                DocumentFile(
                    relative_path="skill-b/SKILL.md",
                    file_path=skill_b_file,
                    content=skill_b_file.read_text(),
                ),
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle, [bundle])

        assert result is None

    def test_validate_with_duplicates(self, validator, validation_rule, temp_project):
        """Test validation when there are duplicate dependencies."""
        # Create command that depends on skill-a and skill-b
        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
  - skill-b
---
"""
        )

        # Create skill-a that also depends on skill-b
        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
"""
        )

        # Create skill-b with no deps
        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text(
            """---
name: skill-b
---
"""
        )

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="cmd.md",
                    file_path=command_file,
                    content=command_file.read_text(),
                ),
                DocumentFile(
                    relative_path="skill-a/SKILL.md",
                    file_path=skill_a_file,
                    content=skill_a_file.read_text(),
                ),
                DocumentFile(
                    relative_path="skill-b/SKILL.md",
                    file_path=skill_b_file,
                    content=skill_b_file.read_text(),
                ),
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle, [bundle])

        assert result is not None
        assert result.bundle_id == "test-bundle"
        assert "skill-b" in result.observed_issue
        assert "skill-a" in result.observed_issue
        assert "redundant" in result.observed_issue.lower()

    def test_validate_deep_chain_duplicates(self, validator, validation_rule, temp_project):
        """Test validation with deep dependency chain."""
        # cmd -> [skill-a, skill-c]
        # skill-a -> [skill-b]
        # skill-b -> [skill-c]
        # skill-c is redundant in cmd

        command_file = temp_project / ".claude" / "commands" / "cmd.md"
        command_file.write_text(
            """---
skills:
  - skill-a
  - skill-c
---
"""
        )

        skill_a_file = temp_project / ".claude" / "skills" / "skill-a" / "SKILL.md"
        skill_a_file.write_text(
            """---
name: skill-a
skills:
  - skill-b
---
"""
        )

        skill_b_file = temp_project / ".claude" / "skills" / "skill-b" / "SKILL.md"
        skill_b_file.write_text(
            """---
name: skill-b
skills:
  - skill-c
---
"""
        )

        skill_c_file = temp_project / ".claude" / "skills" / "skill-c" / "SKILL.md"
        skill_c_file.write_text(
            """---
name: skill-c
---
"""
        )

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="cmd.md",
                    file_path=command_file,
                    content=command_file.read_text(),
                ),
                DocumentFile(
                    relative_path="skill-a/SKILL.md",
                    file_path=skill_a_file,
                    content=skill_a_file.read_text(),
                ),
                DocumentFile(
                    relative_path="skill-b/SKILL.md",
                    file_path=skill_b_file,
                    content=skill_b_file.read_text(),
                ),
                DocumentFile(
                    relative_path="skill-c/SKILL.md",
                    file_path=skill_c_file,
                    content=skill_c_file.read_text(),
                ),
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle, [bundle])

        assert result is not None
        assert "skill-c" in result.observed_issue
        assert "redundant" in result.observed_issue.lower()

    def test_validate_no_project_path(self, validation_rule, tmp_path):
        """Test validation when loader has no project path."""
        loader = Mock()
        loader.project_path = None
        validator = DependencyDuplicateValidator(loader)

        bundle = create_bundle(
            [],
            tmp_path,
        )

        result = validator.validate(validation_rule, bundle, [bundle])

        assert result is None

    def test_determine_resource_type_skill(self, validator, temp_project):
        """Test resource type detection for skills."""
        skill_file = temp_project / ".claude" / "skills" / "test-skill" / "SKILL.md"
        resource_type = validator._determine_resource_type(skill_file)
        assert resource_type == "skill"

    def test_determine_resource_type_command(self, validator, temp_project):
        """Test resource type detection for commands."""
        command_file = temp_project / ".claude" / "commands" / "test.md"
        resource_type = validator._determine_resource_type(command_file)
        assert resource_type == "command"

    def test_determine_resource_type_agent(self, validator, temp_project):
        """Test resource type detection for agents."""
        agent_file = temp_project / ".claude" / "agents" / "test.md"
        resource_type = validator._determine_resource_type(agent_file)
        assert resource_type == "agent"

    def test_determine_resource_type_unknown(self, validator, temp_project):
        """Test resource type detection for unknown files."""
        unknown_file = temp_project / "readme.md"
        resource_type = validator._determine_resource_type(unknown_file)
        assert resource_type is None


class TestMarkdownLinkValidator:
    """Test cases for MarkdownLinkValidator class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project structure."""
        (tmp_path / "docs").mkdir(parents=True)
        (tmp_path / "docs" / "guide.md").write_text("Guide content")
        return tmp_path

    @pytest.fixture
    def mock_loader(self, temp_project):
        """Create a mock loader with project path."""
        loader = Mock()
        loader.project_path = temp_project
        return loader

    @pytest.fixture
    def validator(self, mock_loader):
        """Create a MarkdownLinkValidator instance."""
        return MarkdownLinkValidator(mock_loader)

    @pytest.fixture
    def validation_rule(self):
        """Create a validation rule."""
        return ValidationRule(
            rule_type=ValidationType.MARKDOWN_LINK,
            description="Check for broken links",
            failure_message="Found broken links",
            expected_behavior="All links should be valid",
            params={},
        )

    def test_initialization(self, validator, mock_loader):
        """Test validator initialization."""
        assert validator.loader == mock_loader

    def test_validate_valid_local_links(self, validator, validation_rule, temp_project):
        """Test validation with valid local links."""
        file_path = temp_project / "readme.md"
        file_path.write_text("[Guide](docs/guide.md)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle)

        assert result is None

    def test_validate_broken_local_links(self, validator, validation_rule, temp_project):
        """Test validation with broken local links."""
        file_path = temp_project / "readme.md"
        file_path.write_text("[Missing](docs/missing.md)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle)

        assert result is not None
        assert "missing.md" in result.observed_issue
        assert "not found" in result.observed_issue.lower()

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_valid_external_links(
        self, mock_head, validator, validation_rule, temp_project
    ):
        """Test validation with valid external links."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        file_path = temp_project / "readme.md"
        file_path.write_text("[Example](https://example.com)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle)

        assert result is None

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_broken_external_links(
        self, mock_head, validator, validation_rule, temp_project
    ):
        """Test validation with broken external links."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        file_path = temp_project / "readme.md"
        file_path.write_text("[Example](https://example.com/missing)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle)

        assert result is not None
        assert "example.com" in result.observed_issue
        assert "unreachable" in result.observed_issue.lower()

    def test_validate_no_project_path(self, validation_rule, tmp_path):
        """Test validation when loader has no project path."""
        loader = Mock()
        loader.project_path = None
        validator = MarkdownLinkValidator(loader)

        bundle = create_bundle(
            [],
            tmp_path,
        )

        result = validator.validate(validation_rule, bundle, [bundle])

        assert result is None

    def test_validate_no_links(self, validator, validation_rule, temp_project):
        """Test validation with file containing no links."""
        file_path = temp_project / "readme.md"
        file_path.write_text("Just plain text with no links")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle)

        assert result is None

    def test_validate_skip_local_files(self, validator, temp_project):
        """Test validation skips local file checks when disabled."""
        file_path = temp_project / "readme.md"
        file_path.write_text("[Missing](docs/missing.md)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        # Create rule with check_local_files disabled
        rule = ValidationRule(
            rule_type=ValidationType.MARKDOWN_LINK,
            description="Check for broken links",
            failure_message="Found broken links",
            expected_behavior="All links should be valid",
            params={"check_local_files": False},
        )
        result = validator.validate(rule, bundle)

        assert result is None

    @patch("drift.utils.link_validator.requests.head")
    def test_validate_skip_external_urls(self, mock_head, validator, temp_project):
        """Test validation skips external URL checks when disabled."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        file_path = temp_project / "readme.md"
        file_path.write_text("[Example](https://example.com/missing)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        # Create rule with check_external_urls disabled
        rule = ValidationRule(
            rule_type=ValidationType.MARKDOWN_LINK,
            description="Check for broken links",
            failure_message="Found broken links",
            expected_behavior="All links should be valid",
            params={"check_external_urls": False},
        )
        result = validator.validate(rule, bundle)

        assert result is None
        mock_head.assert_not_called()

    def test_validate_multiple_files(self, validator, validation_rule, temp_project):
        """Test validation across multiple files."""
        file1 = temp_project / "file1.md"
        file1.write_text("[Valid](docs/guide.md)")

        file2 = temp_project / "file2.md"
        file2.write_text("[Invalid](docs/missing.md)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="file1.md",
                    file_path=file1,
                    content=file1.read_text(),
                ),
                DocumentFile(
                    relative_path="file2.md",
                    file_path=file2,
                    content=file2.read_text(),
                ),
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle)

        assert result is not None
        assert "file2.md" in result.observed_issue
        assert "missing.md" in result.observed_issue

    def test_validate_anchor_links_ignored(self, validator, validation_rule, temp_project):
        """Test that anchor links are ignored."""
        file_path = temp_project / "readme.md"
        file_path.write_text("[Anchor](#section)")

        bundle = create_bundle(
            [
                DocumentFile(
                    relative_path="readme.md",
                    file_path=file_path,
                    content=file_path.read_text(),
                )
            ],
            temp_project,
        )

        result = validator.validate(validation_rule, bundle)

        assert result is None
