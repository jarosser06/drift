"""Tests for Claude Circular Dependencies Validator."""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeCircularDependenciesValidator


class TestCircularDependenciesValidator:
    """Tests for CircularDependenciesValidator."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create temporary project structure with circular dependencies."""
        # Create skill-a → skill-b → skill-a (cycle)
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_content = "---\nname: skill-a\ndescription: Skill A\nskills:\n  - skill-b\n---\n"
        (skill_a_dir / "SKILL.md").write_text(skill_a_content)

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_content = "---\nname: skill-b\ndescription: Skill B\nskills:\n  - skill-a\n---\n"
        (skill_b_dir / "SKILL.md").write_text(skill_b_content)

        # Create skill-c with no cycles
        skill_c_dir = tmp_path / ".claude" / "skills" / "skill-c"
        skill_c_dir.mkdir(parents=True)
        (skill_c_dir / "SKILL.md").write_text("---\nname: skill-c\n---\n")

        # Create command with circular dependency through skills
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        cmd_content = "---\ndescription: Test command\nskills:\n  - skill-a\n---\n"
        (cmd_dir / "test-cmd.md").write_text(cmd_content)

        return tmp_path

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
        validator = ClaudeCircularDependenciesValidator()
        assert validator.computation_type == "programmatic"

    def test_detects_circular_dependency(self, project_root, all_bundles):
        """Test detection of circular dependency between skills."""
        # Bundle for skill-a which has circular dependency with skill-b
        skill_a_path = project_root / ".claude" / "skills" / "skill-a" / "SKILL.md"
        bundle_skill_a = DocumentBundle(
            bundle_id="skill-a",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_a_path),
                    relative_path=".claude/skills/skill-a/SKILL.md",
                    content=skill_a_path.read_text(),
                )
            ],
            project_path=project_root,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type="core:circular_dependencies",
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        result = validator.validate(rule, bundle_skill_a, all_bundles)

        assert result is not None
        assert "skill-a" in result.observed_issue
        assert "skill-b" in result.observed_issue
        assert "→" in result.observed_issue
        # Changed: verify failure_message is present (not "cycle")
        assert "circular dependency" in result.observed_issue.lower()

    def test_passes_with_no_circular_dependencies(self, project_root, all_bundles):
        """Test validation passes when no circular dependencies exist."""
        # Bundle for skill-c which has no dependencies
        skill_c_path = project_root / ".claude" / "skills" / "skill-c" / "SKILL.md"
        bundle_skill_c = DocumentBundle(
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

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type="core:circular_dependencies",
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        result = validator.validate(rule, bundle_skill_c, all_bundles)
        assert result is None

    def test_detects_self_loop(self, tmp_path):
        """Test detection of self-referencing dependency."""
        # Create skill that depends on itself
        skill_dir = tmp_path / ".claude" / "skills" / "self-skill"
        skill_dir.mkdir(parents=True)
        skill_content = "---\nname: self-skill\nskills:\n  - self-skill\n---\n"
        (skill_dir / "SKILL.md").write_text(skill_content)

        skill_path = skill_dir / "SKILL.md"
        bundle = DocumentBundle(
            bundle_id="self-skill",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_path),
                    relative_path=".claude/skills/self-skill/SKILL.md",
                    content=skill_path.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type="core:circular_dependencies",
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        result = validator.validate(rule, bundle, [bundle])

        assert result is not None
        assert "self-skill" in result.observed_issue
        # Changed: verify failure_message is present (not "cycle")
        assert "circular dependency" in result.observed_issue.lower()

    def test_detects_multi_node_cycle(self, tmp_path):
        """Test detection of multi-node circular dependency."""
        # Create A → B → C → D → A
        for skill_name, deps in [
            ("skill-a", ["skill-b"]),
            ("skill-b", ["skill-c"]),
            ("skill-c", ["skill-d"]),
            ("skill-d", ["skill-a"]),
        ]:
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            deps_yaml = "\n".join([f"  - {d}" for d in deps])
            content = f"---\nname: {skill_name}\nskills:\n{deps_yaml}\n---\n"
            (skill_dir / "SKILL.md").write_text(content)

        # Create bundles for all skills
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d"]:
            skill_path = tmp_path / ".claude" / "skills" / skill_name / "SKILL.md"
            bundles.append(
                DocumentBundle(
                    bundle_id=skill_name,
                    bundle_type="skill",
                    bundle_strategy="individual",
                    files=[
                        DocumentFile(
                            file_path=str(skill_path),
                            relative_path=f".claude/skills/{skill_name}/SKILL.md",
                            content=skill_path.read_text(),
                        )
                    ],
                    project_path=tmp_path,
                )
            )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type="core:circular_dependencies",
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        result = validator.validate(rule, bundles[0], bundles)

        assert result is not None
        # Changed: verify failure_message is present (not "cycle")
        assert "circular dependency" in result.observed_issue.lower()
        # Should contain the cycle path
        assert "skill-a" in result.observed_issue
        assert "→" in result.observed_issue

    def test_returns_none_without_all_bundles(self, project_root):
        """Test validator returns None when all_bundles not provided."""
        skill_a_path = project_root / ".claude" / "skills" / "skill-a" / "SKILL.md"
        bundle = DocumentBundle(
            bundle_id="skill-a",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_a_path),
                    relative_path=".claude/skills/skill-a/SKILL.md",
                    content=skill_a_path.read_text(),
                )
            ],
            project_path=project_root,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type="core:circular_dependencies",
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        result = validator.validate(rule, bundle, all_bundles=None)
        assert result is None

    def test_raises_error_without_resource_dirs(self, project_root, all_bundles):
        """Test validator raises error when resource_dirs param missing."""
        skill_a_path = project_root / ".claude" / "skills" / "skill-a" / "SKILL.md"
        bundle = DocumentBundle(
            bundle_id="skill-a",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_a_path),
                    relative_path=".claude/skills/skill-a/SKILL.md",
                    content=skill_a_path.read_text(),
                )
            ],
            project_path=project_root,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type="core:circular_dependencies",
            description="Check for circular dependencies",
            params={},  # Missing resource_dirs
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        with pytest.raises(ValueError, match="requires 'resource_dirs' param"):
            validator.validate(rule, bundle, all_bundles)

    def test_handles_malformed_resource_files(self, tmp_path):
        """Test validator handles files that can't be loaded gracefully."""
        # Create a malformed skill file
        bad_skill_dir = tmp_path / ".claude" / "skills" / "bad-skill"
        bad_skill_dir.mkdir(parents=True)
        (bad_skill_dir / "SKILL.md").write_text("Not valid frontmatter")

        bad_skill_path = bad_skill_dir / "SKILL.md"
        bundle = DocumentBundle(
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
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type="core:circular_dependencies",
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        # Should not raise exception - malformed files are skipped
        result = validator.validate(rule, bundle, [bundle])
        # No circular dependency detected (file couldn't be loaded)
        assert result is None

    def test_determine_resource_type_skill(self):
        """Test _determine_resource_type identifies skills correctly."""
        from pathlib import Path

        validator = ClaudeCircularDependenciesValidator()
        skill_path = Path(".claude/skills/test-skill/SKILL.md")
        assert validator._determine_resource_type(skill_path) == "skill"

    def test_determine_resource_type_command(self):
        """Test _determine_resource_type identifies commands correctly."""
        from pathlib import Path

        validator = ClaudeCircularDependenciesValidator()
        cmd_path = Path(".claude/commands/test-cmd.md")
        assert validator._determine_resource_type(cmd_path) == "command"

    def test_determine_resource_type_agent(self):
        """Test _determine_resource_type identifies agents correctly."""
        from pathlib import Path

        validator = ClaudeCircularDependenciesValidator()
        agent_path = Path(".claude/agents/test-agent.md")
        assert validator._determine_resource_type(agent_path) == "agent"

    def test_determine_resource_type_unknown(self):
        """Test _determine_resource_type returns None for unknown types."""
        from pathlib import Path

        validator = ClaudeCircularDependenciesValidator()
        unknown_path = Path("some/other/file.md")
        assert validator._determine_resource_type(unknown_path) is None
