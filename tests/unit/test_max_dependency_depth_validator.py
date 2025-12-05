"""Tests for Claude Max Dependency Depth Validator."""

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeMaxDependencyDepthValidator


class TestMaxDependencyDepthValidator:
    """Tests for MaxDependencyDepthValidator."""

    @pytest.fixture
    def project_with_deep_chain(self, tmp_path):
        """Create project with deep dependency chain."""
        # Create chain: A → B → C → D → E → F (depth 5)
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e", "skill-f"]
        for i, skill_name in enumerate(skills):
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)

            if i < len(skills) - 1:
                # Has dependency on next skill
                next_skill = skills[i + 1]
                content = f"---\nname: {skill_name}\nskills:\n  - {next_skill}\n---\n"
            else:
                # Last skill has no dependencies
                content = f"---\nname: {skill_name}\n---\n"

            (skill_dir / "SKILL.md").write_text(content)

        return tmp_path

    @pytest.fixture
    def all_bundles_deep_chain(self, project_with_deep_chain):
        """Create bundles for all skills in deep chain."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e", "skill-f"]

        for skill_name in skills:
            skill_path = project_with_deep_chain / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_deep_chain,
                )
            )

        return bundles

    def test_computation_type(self):
        """Test that validator has correct computation type."""
        validator = ClaudeMaxDependencyDepthValidator()
        assert validator.computation_type == "programmatic"

    def test_detects_excessive_depth(self, project_with_deep_chain, all_bundles_deep_chain):
        """Test detection of dependency chain exceeding max depth."""
        # skill-a has depth 5, max is 3
        skill_a_path = project_with_deep_chain / ".claude" / "skills" / "skill-a" / "SKILL.md"
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
            project_path=project_with_deep_chain,
        )

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        result = validator.validate(rule, bundle_skill_a, all_bundles_deep_chain)

        assert result is not None
        assert "5" in result.observed_issue  # actual depth
        assert "3" in result.observed_issue  # max depth
        assert "skill-a" in result.observed_issue
        assert "→" in result.observed_issue
        assert "depth" in result.observed_issue.lower()

    def test_passes_when_within_depth_limit(self, project_with_deep_chain, all_bundles_deep_chain):
        """Test validation passes when depth is within limit."""
        # skill-d has depth 2, max is 5
        skill_d_path = project_with_deep_chain / ".claude" / "skills" / "skill-d" / "SKILL.md"
        bundle_skill_d = DocumentBundle(
            bundle_id="skill-d",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_d_path),
                    relative_path=".claude/skills/skill-d/SKILL.md",
                    content=skill_d_path.read_text(),
                )
            ],
            project_path=project_with_deep_chain,
        )

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 5},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 5",
        )

        result = validator.validate(rule, bundle_skill_d, all_bundles_deep_chain)
        assert result is None

    def test_passes_with_no_dependencies(self, tmp_path):
        """Test validation passes when resource has no dependencies."""
        skill_dir = tmp_path / ".claude" / "skills" / "solo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: solo-skill\n---\n")

        skill_path = skill_dir / "SKILL.md"
        bundle = DocumentBundle(
            bundle_id="solo-skill",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_path),
                    relative_path=".claude/skills/solo-skill/SKILL.md",
                    content=skill_path.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        result = validator.validate(rule, bundle, [bundle])
        assert result is None

    def test_exactly_at_limit(self, tmp_path):
        """Test validation when depth exactly equals max_depth."""
        # Create chain: A → B → C (depth 2)
        for skill_name, deps in [
            ("skill-a", ["skill-b"]),
            ("skill-b", ["skill-c"]),
            ("skill-c", []),
        ]:
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            if deps:
                deps_yaml = "\n".join([f"  - {d}" for d in deps])
                content = f"---\nname: {skill_name}\nskills:\n{deps_yaml}\n---\n"
            else:
                content = f"---\nname: {skill_name}\n---\n"
            (skill_dir / "SKILL.md").write_text(content)

        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 2},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 2",
        )

        # Depth 2 should pass when max_depth is 2
        result = validator.validate(rule, bundles[0], bundles)
        assert result is None

    def test_uses_default_max_depth(self, project_with_deep_chain, all_bundles_deep_chain):
        """Test validator uses default max_depth of 5 when not specified."""
        skill_a_path = project_with_deep_chain / ".claude" / "skills" / "skill-a" / "SKILL.md"
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
            project_path=project_with_deep_chain,
        )

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"]},  # No max_depth specified
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed default depth",
        )

        # skill-a has depth 5, default max is 5, should pass
        result = validator.validate(rule, bundle_skill_a, all_bundles_deep_chain)
        assert result is None

    def test_detects_multiple_branches_uses_longest(self, tmp_path):
        """Test validation uses longest path when multiple branches exist."""
        # A → B (depth 1)
        # A → C → D → E (depth 3) - longest path
        for skill_name, deps in [
            ("skill-a", ["skill-b", "skill-c"]),
            ("skill-b", []),
            ("skill-c", ["skill-d"]),
            ("skill-d", ["skill-e"]),
            ("skill-e", []),
        ]:
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            if deps:
                deps_yaml = "\n".join([f"  - {d}" for d in deps])
                content = f"---\nname: {skill_name}\nskills:\n{deps_yaml}\n---\n"
            else:
                content = f"---\nname: {skill_name}\n---\n"
            (skill_dir / "SKILL.md").write_text(content)

        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]:
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 2},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 2",
        )

        result = validator.validate(rule, bundles[0], bundles)
        assert result is not None
        assert "3" in result.observed_issue  # longest path depth
        assert "skill-c" in result.observed_issue or "skill-e" in result.observed_issue

    def test_returns_none_without_all_bundles(self, project_with_deep_chain):
        """Test validator returns None when all_bundles not provided."""
        skill_a_path = project_with_deep_chain / ".claude" / "skills" / "skill-a" / "SKILL.md"
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
            project_path=project_with_deep_chain,
        )

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        result = validator.validate(rule, bundle, all_bundles=None)
        assert result is None

    def test_raises_error_without_resource_dirs(self, project_with_deep_chain):
        """Test validator raises error when resource_dirs param missing."""
        skill_a_path = project_with_deep_chain / ".claude" / "skills" / "skill-a" / "SKILL.md"
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
            project_path=project_with_deep_chain,
        )

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"max_depth": 3},  # Missing resource_dirs
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        with pytest.raises(ValueError, match="requires 'resource_dirs' param"):
            validator.validate(rule, bundle, [bundle])

    def test_handles_malformed_resource_files(self, tmp_path):
        """Test validator handles files that can't be loaded gracefully."""
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        # Should not raise exception - malformed files are skipped
        result = validator.validate(rule, bundle, [bundle])
        # No excessive depth detected (file couldn't be loaded)
        assert result is None

    def test_determine_resource_type_skill(self):
        """Test _determine_resource_type identifies skills correctly."""
        from pathlib import Path

        validator = ClaudeMaxDependencyDepthValidator()
        skill_path = Path(".claude/skills/test-skill/SKILL.md")
        assert validator._determine_resource_type(skill_path) == "skill"

    def test_determine_resource_type_command(self):
        """Test _determine_resource_type identifies commands correctly."""
        from pathlib import Path

        validator = ClaudeMaxDependencyDepthValidator()
        cmd_path = Path(".claude/commands/test-cmd.md")
        assert validator._determine_resource_type(cmd_path) == "command"

    def test_determine_resource_type_agent(self):
        """Test _determine_resource_type identifies agents correctly."""
        from pathlib import Path

        validator = ClaudeMaxDependencyDepthValidator()
        agent_path = Path(".claude/agents/test-agent.md")
        assert validator._determine_resource_type(agent_path) == "agent"

    def test_determine_resource_type_unknown(self):
        """Test _determine_resource_type returns None for unknown types."""
        from pathlib import Path

        validator = ClaudeMaxDependencyDepthValidator()
        unknown_path = Path("some/other/file.md")
        assert validator._determine_resource_type(unknown_path) is None
