"""Tests for CircularDependenciesValidator failure_details feature."""

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeCircularDependenciesValidator


class TestCircularDependenciesValidatorFailureDetails:
    """Tests for CircularDependenciesValidator failure_details enhancement."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ClaudeCircularDependenciesValidator()

    @pytest.fixture
    def validation_rule(self):
        """Create standard validation rule."""
        return ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Circular dependency detected",
            expected_behavior="Dependencies should not form cycles",
        )

    @pytest.fixture
    def project_with_single_cycle(self, tmp_path):
        """Create project with single circular dependency."""
        # skill-a → skill-b → skill-a
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / "SKILL.md").write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        return tmp_path

    @pytest.fixture
    def project_with_multiple_cycles(self, tmp_path):
        """Create project with multiple circular dependencies."""
        # Cycle 1: skill-a → skill-b → skill-a
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / "SKILL.md").write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        # Cycle 2: skill-c → skill-d → skill-e → skill-c
        skill_c_dir = tmp_path / ".claude" / "skills" / "skill-c"
        skill_c_dir.mkdir(parents=True)
        (skill_c_dir / "SKILL.md").write_text("---\nname: skill-c\nskills:\n  - skill-d\n---\n")

        skill_d_dir = tmp_path / ".claude" / "skills" / "skill-d"
        skill_d_dir.mkdir(parents=True)
        (skill_d_dir / "SKILL.md").write_text("---\nname: skill-d\nskills:\n  - skill-e\n---\n")

        skill_e_dir = tmp_path / ".claude" / "skills" / "skill-e"
        skill_e_dir.mkdir(parents=True)
        (skill_e_dir / "SKILL.md").write_text("---\nname: skill-e\nskills:\n  - skill-c\n---\n")

        return tmp_path

    def test_single_cycle_has_failure_details(
        self, validator, validation_rule, project_with_single_cycle
    ):
        """Test that single cycle includes failure_details in result."""
        # Create bundles
        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
            skill_path = project_with_single_cycle / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_single_cycle,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Verify failure_details exists
        assert result is not None
        assert result.failure_details is not None
        assert isinstance(result.failure_details, dict)

    def test_single_cycle_failure_details_structure(
        self, validator, validation_rule, project_with_single_cycle
    ):
        """Test that failure_details has expected structure for single cycle."""
        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
            skill_path = project_with_single_cycle / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_single_cycle,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Verify structure
        assert "circular_path" in result.failure_details
        assert "cycle_count" in result.failure_details
        assert "all_cycles" in result.failure_details

        # Verify values
        assert result.failure_details["cycle_count"] == 1
        assert isinstance(result.failure_details["all_cycles"], list)
        assert len(result.failure_details["all_cycles"]) == 1

    def test_single_cycle_circular_path_format(
        self, validator, validation_rule, project_with_single_cycle
    ):
        """Test that circular_path is properly formatted with arrows."""
        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
            skill_path = project_with_single_cycle / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_single_cycle,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        circular_path = result.failure_details["circular_path"]
        assert "→" in circular_path
        assert "skill-a" in circular_path
        assert "skill-b" in circular_path

    def test_single_cycle_message_includes_circular_path(
        self, validator, validation_rule, project_with_single_cycle
    ):
        """Test that observed_issue message includes circular_path from failure_details."""
        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
            skill_path = project_with_single_cycle / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_single_cycle,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Message should contain the circular path
        circular_path = result.failure_details["circular_path"]
        assert circular_path in result.observed_issue

    def test_multiple_cycles_failure_details_structure(
        self, validator, validation_rule, project_with_multiple_cycles
    ):
        """Test failure_details structure for multiple cycles."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]:
            skill_path = (
                project_with_multiple_cycles / ".claude" / "skills" / skill_name / "SKILL.md"
            )
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
                    project_path=project_with_multiple_cycles,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Verify cycle count
        assert result.failure_details["cycle_count"] >= 1
        assert len(result.failure_details["all_cycles"]) >= 1

    def test_multiple_cycles_all_cycles_details(
        self, validator, validation_rule, project_with_multiple_cycles
    ):
        """Test that all_cycles contains detailed info for each cycle."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]:
            skill_path = (
                project_with_multiple_cycles / ".claude" / "skills" / skill_name / "SKILL.md"
            )
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
                    project_path=project_with_multiple_cycles,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Each cycle detail should have file and cycle_path
        for cycle_detail in result.failure_details["all_cycles"]:
            assert "file" in cycle_detail
            assert "cycle_path" in cycle_detail
            assert "→" in cycle_detail["cycle_path"]

    def test_multiple_cycles_message_format(
        self, validator, validation_rule, project_with_multiple_cycles
    ):
        """Test message formatting for multiple cycles."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]:
            skill_path = (
                project_with_multiple_cycles / ".claude" / "skills" / skill_name / "SKILL.md"
            )
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
                    project_path=project_with_multiple_cycles,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Message should mention multiple cycles if count > 1
        if result.failure_details["cycle_count"] > 1:
            assert "cycles detected" in result.observed_issue.lower()

    def test_self_loop_failure_details(self, validator, validation_rule, tmp_path):
        """Test failure_details for self-referencing dependency."""
        # skill-a → skill-a
        skill_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: skill-a\nskills:\n  - skill-a\n---\n")

        skill_path = skill_dir / "SKILL.md"
        bundle = DocumentBundle(
            bundle_id="skill-a",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_path),
                    relative_path=".claude/skills/skill-a/SKILL.md",
                    content=skill_path.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        result = validator.validate(validation_rule, bundle, [bundle])

        # Verify failure_details
        assert result is not None
        assert result.failure_details is not None
        assert "circular_path" in result.failure_details
        assert "skill-a" in result.failure_details["circular_path"]

    def test_long_cycle_chain_in_failure_details(self, validator, validation_rule, tmp_path):
        """Test failure_details for long circular chain."""
        # Create A → B → C → D → E → A
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
        for i, skill_name in enumerate(skills):
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)
            next_skill = skills[(i + 1) % len(skills)]
            content = f"---\nname: {skill_name}\nskills:\n  - {next_skill}\n---\n"
            (skill_dir / "SKILL.md").write_text(content)

        bundles = []
        for skill_name in skills:
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Verify all skills in cycle are in circular_path
        circular_path = result.failure_details["circular_path"]
        for skill in skills:
            assert skill in circular_path

    def test_failure_details_file_paths_match_violations(
        self, validator, validation_rule, project_with_single_cycle
    ):
        """Test that file_paths in DocumentRule match files in failure_details."""
        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
            skill_path = project_with_single_cycle / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_single_cycle,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Verify file_paths list contains files from all_cycles
        for cycle_detail in result.failure_details["all_cycles"]:
            assert cycle_detail["file"] in result.file_paths

    def test_no_cycles_returns_none(self, validator, validation_rule, tmp_path):
        """Test that no cycles returns None (no failure_details)."""
        skill_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: skill-a\n---\n")

        skill_path = skill_dir / "SKILL.md"
        bundle = DocumentBundle(
            bundle_id="skill-a",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_path),
                    relative_path=".claude/skills/skill-a/SKILL.md",
                    content=skill_path.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        result = validator.validate(validation_rule, bundle, [bundle])

        assert result is None

    def test_failure_details_with_unicode_arrows(
        self, validator, validation_rule, project_with_single_cycle
    ):
        """Test that circular_path uses Unicode arrow character."""
        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
            skill_path = project_with_single_cycle / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_single_cycle,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Should use → (not ->)
        assert "→" in result.failure_details["circular_path"]
        assert "->" not in result.failure_details["circular_path"]

    def test_failure_details_serializable(
        self, validator, validation_rule, project_with_single_cycle
    ):
        """Test that failure_details can be serialized (for JSON output)."""
        import json

        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
            skill_path = project_with_single_cycle / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_single_cycle,
                )
            )

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Should be JSON serializable
        try:
            json.dumps(result.failure_details)
        except (TypeError, ValueError) as e:
            pytest.fail(f"failure_details not JSON serializable: {e}")
