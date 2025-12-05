"""Tests for Claude Dependency Duplicate Validator."""

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeDependencyDuplicateValidator


class TestDependencyDuplicateValidator:
    """Tests for DependencyDuplicateValidator."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create temporary project structure with skills and commands."""
        # Create skill hierarchy:
        # skill-c depends on skill-b, skill-b depends on skill-a
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\ndescription: Skill A\n---\n\nSkill A content")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_content = (
            "---\nname: skill-b\ndescription: Skill B\nskills:\n"
            "  - skill-a\n---\n\nSkill B content"
        )
        (skill_b_dir / "SKILL.md").write_text(skill_b_content)

        skill_c_dir = tmp_path / ".claude" / "skills" / "skill-c"
        skill_c_dir.mkdir(parents=True)
        skill_c_content = (
            "---\nname: skill-c\ndescription: Skill C\nskills:\n"
            "  - skill-b\n  - skill-a\n---\n\n"
            "Skill C content (redundant dependency)"
        )
        (skill_c_dir / "SKILL.md").write_text(skill_c_content)

        # Create command that depends on skill-c
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        cmd_content = (
            "---\ndescription: Test command\nskills:\n  - skill-c\n"
            "  - skill-a\n---\n\nCommand content (redundant dependency)"
        )
        (cmd_dir / "test-cmd.md").write_text(cmd_content)

        return tmp_path

    @pytest.fixture
    def bundle_skill_c(self, project_root):
        """Create bundle for skill-c with redundant dependency."""
        skill_c_path = project_root / ".claude" / "skills" / "skill-c" / "SKILL.md"
        return DocumentBundle(
            bundle_id="skill-c",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_c_path),
                    relative_path=".claude/skills/skill-c/SKILL.md",
                    content=skill_c_path.read_text(),
                )
            ],
            project_path=project_root,
        )

    @pytest.fixture
    def bundle_command(self, project_root):
        """Create bundle for command with redundant dependency."""
        cmd_path = project_root / ".claude" / "commands" / "test-cmd.md"
        return DocumentBundle(
            bundle_id="test-cmd",
            bundle_type="command",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(cmd_path),
                    relative_path=".claude/commands/test-cmd.md",
                    content=cmd_path.read_text(),
                )
            ],
            project_path=project_root,
        )

    @pytest.fixture
    def all_bundles(self, project_root):
        """Create all bundles for cross-bundle analysis."""
        bundles = []

        # Create bundles for all skills
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_root / ".claude" / "skills" / skill_name / "SKILL.md"
            rel_path = f".claude/skills/{skill_name}/SKILL.md"
            bundles.append(
                DocumentBundle(
                    bundle_id=skill_name,
                    bundle_type="skill",
                    bundle_strategy="individual",
                    files=[
                        DocumentFile(
                            file_path=str(skill_path),
                            relative_path=rel_path,
                            content=skill_path.read_text(),
                        )
                    ],
                    project_path=project_root,
                )
            )

        # Create bundle for command
        cmd_path = project_root / ".claude" / "commands" / "test-cmd.md"
        bundles.append(
            DocumentBundle(
                bundle_id="test-cmd",
                bundle_type="command",
                bundle_strategy="individual",
                files=[
                    DocumentFile(
                        file_path=str(cmd_path),
                        relative_path=".claude/commands/test-cmd.md",
                        content=cmd_path.read_text(),
                    )
                ],
                project_path=project_root,
            )
        )

        return bundles

    def test_computation_type(self):
        """Test that validator has correct computation type."""
        validator = ClaudeDependencyDuplicateValidator()
        assert validator.computation_type == "programmatic"

    def test_detects_redundant_skill_dependency(self, bundle_skill_c, all_bundles):
        """Test detection of redundant transitive skill dependency."""
        validator = ClaudeDependencyDuplicateValidator()
        rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found redundant skill dependencies",
            expected_behavior="Skills declare only direct dependencies",
        )

        result = validator.validate(rule, bundle_skill_c, all_bundles)

        assert result is not None
        assert "skill-a" in result.observed_issue
        assert "skill-b" in result.observed_issue
        assert "redundant" in result.observed_issue.lower()

    def test_detects_redundant_command_dependency(self, bundle_command, all_bundles):
        """Test detection of redundant transitive dependency in command."""
        validator = ClaudeDependencyDuplicateValidator()
        rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/commands", ".claude/skills"]},
            failure_message="Found redundant dependencies",
            expected_behavior="Commands declare only direct dependencies",
        )

        result = validator.validate(rule, bundle_command, all_bundles)

        assert result is not None
        assert "skill-a" in result.observed_issue
        assert "skill-c" in result.observed_issue

    def test_passes_with_no_redundant_dependencies(self, project_root, all_bundles):
        """Test validation passes when no redundant dependencies exist."""
        # Create bundle for skill-b (no redundant dependencies)
        skill_b_path = project_root / ".claude" / "skills" / "skill-b" / "SKILL.md"
        bundle_skill_b = DocumentBundle(
            bundle_id="skill-b",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_b_path),
                    relative_path=".claude/skills/skill-b/SKILL.md",
                    content=skill_b_path.read_text(),
                )
            ],
            project_path=project_root,
        )

        validator = ClaudeDependencyDuplicateValidator()
        rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found redundant dependencies",
            expected_behavior="Skills declare only direct dependencies",
        )

        result = validator.validate(rule, bundle_skill_b, all_bundles)
        assert result is None

    def test_returns_none_without_all_bundles(self, bundle_skill_c):
        """Test validator returns None when all_bundles not provided."""
        validator = ClaudeDependencyDuplicateValidator()
        rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found redundant dependencies",
            expected_behavior="Skills declare only direct dependencies",
        )

        result = validator.validate(rule, bundle_skill_c, all_bundles=None)
        assert result is None

    def test_raises_error_without_resource_dirs(self, bundle_skill_c, all_bundles):
        """Test validator raises error when resource_dirs param missing."""
        validator = ClaudeDependencyDuplicateValidator()
        rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for redundant dependencies",
            params={},  # Missing resource_dirs
            failure_message="Found redundant dependencies",
            expected_behavior="Skills declare only direct dependencies",
        )

        with pytest.raises(ValueError, match="requires 'resource_dirs' param"):
            validator.validate(rule, bundle_skill_c, all_bundles)

    def test_determine_resource_type_skill(self):
        """Test _determine_resource_type identifies skills correctly."""
        from pathlib import Path

        validator = ClaudeDependencyDuplicateValidator()

        # Test skill path
        skill_path = Path(".claude/skills/test-skill/SKILL.md")
        assert validator._determine_resource_type(skill_path) == "skill"

    def test_determine_resource_type_command(self):
        """Test _determine_resource_type identifies commands correctly."""
        from pathlib import Path

        validator = ClaudeDependencyDuplicateValidator()

        # Test command path
        cmd_path = Path(".claude/commands/test-cmd.md")
        assert validator._determine_resource_type(cmd_path) == "command"

    def test_determine_resource_type_agent(self):
        """Test _determine_resource_type identifies agents correctly."""
        from pathlib import Path

        validator = ClaudeDependencyDuplicateValidator()

        # Test agent path
        agent_path = Path(".claude/agents/test-agent.md")
        assert validator._determine_resource_type(agent_path) == "agent"

    def test_determine_resource_type_unknown(self):
        """Test _determine_resource_type returns None for unknown types."""
        from pathlib import Path

        validator = ClaudeDependencyDuplicateValidator()

        # Test unknown path
        unknown_path = Path("some/other/file.md")
        assert validator._determine_resource_type(unknown_path) is None

    def test_handles_malformed_resource_files(self, project_root, all_bundles):
        """Test validator handles files that can't be loaded gracefully."""
        # Create a malformed skill file
        bad_skill_dir = project_root / ".claude" / "skills" / "bad-skill"
        bad_skill_dir.mkdir(parents=True)
        (bad_skill_dir / "SKILL.md").write_text("Not valid frontmatter")

        bad_skill_path = bad_skill_dir / "SKILL.md"
        bundle_bad = DocumentBundle(
            bundle_id="bad-skill",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(bad_skill_path),
                    relative_path=".claude/skills/bad-skill/SKILL.md",
                    content=bad_skill_path.read_text(),
                )
            ],
            project_path=project_root,
        )

        validator = ClaudeDependencyDuplicateValidator()
        rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found redundant dependencies",
            expected_behavior="Skills declare only direct dependencies",
        )

        # Should not raise exception - malformed files are skipped
        validator.validate(rule, bundle_bad, all_bundles + [bundle_bad])
        # The important thing is it doesn't crash

    def test_handles_missing_resource_in_graph(self, bundle_command, project_root):
        """Test validator handles resources not in dependency graph."""
        # Create bundles without the full dependency chain
        incomplete_bundles = [bundle_command]

        validator = ClaudeDependencyDuplicateValidator()
        rule = ValidationRule(
            rule_type=ValidationType.DEPENDENCY_DUPLICATE,
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/commands", ".claude/skills"]},
            failure_message="Found redundant dependencies",
            expected_behavior="Commands declare only direct dependencies",
        )

        # Should not raise KeyError - missing resources are handled
        validator.validate(rule, bundle_command, incomplete_bundles)
        # May return None since incomplete graph can't detect duplicates
