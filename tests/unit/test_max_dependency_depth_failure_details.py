"""Tests for MaxDependencyDepthValidator failure_details feature."""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeMaxDependencyDepthValidator


class TestMaxDependencyDepthValidatorFailureDetails:
    """Tests for MaxDependencyDepthValidator failure_details enhancement."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ClaudeMaxDependencyDepthValidator()

    @pytest.fixture
    def validation_rule(self):
        """Create standard validation rule with max_depth=3."""
        return ValidationRule(
            rule_type="core:max_dependency_depth",
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain exceeds maximum depth",
            expected_behavior="Dependencies should not exceed depth 3",
        )

    @pytest.fixture
    def project_with_deep_chain(self, tmp_path):
        """Create project with dependency chain exceeding depth."""
        # Create chain: A → B → C → D → E (depth 4)
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
        for i, skill_name in enumerate(skills):
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)

            if i < len(skills) - 1:
                next_skill = skills[i + 1]
                content = f"---\nname: {skill_name}\nskills:\n  - {next_skill}\n---\n"
            else:
                content = f"---\nname: {skill_name}\n---\n"

            (skill_dir / "SKILL.md").write_text(content)

        return tmp_path

    def test_depth_violation_has_failure_details(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that depth violation includes failure_details in result."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Verify failure_details exists
        assert result is not None
        assert result.failure_details is not None
        assert isinstance(result.failure_details, dict)

    def test_failure_details_structure(self, validator, validation_rule, project_with_deep_chain):
        """Test that failure_details has expected structure."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Verify structure
        assert "actual_depth" in result.failure_details
        assert "max_depth" in result.failure_details
        assert "dependency_chain" in result.failure_details
        assert "violation_count" in result.failure_details
        assert "all_violations" in result.failure_details

    def test_failure_details_actual_depth_correct(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that actual_depth in failure_details is correct."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # skill-a has depth 4 (A → B → C → D → E)
        assert result.failure_details["actual_depth"] == 4

    def test_failure_details_max_depth_correct(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that max_depth in failure_details matches rule params."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        assert result.failure_details["max_depth"] == 3

    def test_failure_details_dependency_chain_format(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that dependency_chain is properly formatted with arrows."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        dependency_chain = result.failure_details["dependency_chain"]
        assert "→" in dependency_chain
        assert "skill-a" in dependency_chain
        assert "skill-e" in dependency_chain

    def test_failure_details_complete_chain(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that dependency_chain contains complete path."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        dependency_chain = result.failure_details["dependency_chain"]
        # Should contain all skills in order
        for skill in skills:
            assert skill in dependency_chain

    def test_message_includes_failure_details(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that observed_issue message includes details from failure_details."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Message should contain depth information
        assert "4" in result.observed_issue  # actual_depth
        assert "3" in result.observed_issue  # max_depth

    def test_all_violations_structure(self, validator, validation_rule, project_with_deep_chain):
        """Test that all_violations contains detailed info for each violation."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Each violation should have file, actual_depth, and dependency_chain
        for violation in result.failure_details["all_violations"]:
            assert "file" in violation
            assert "actual_depth" in violation
            assert "dependency_chain" in violation

    def test_multiple_violations_in_bundle(self, validator, validation_rule, tmp_path):
        """Test handling of multiple depth violations in same bundle."""
        # Create two skills that both exceed depth
        # skill-a → skill-b → skill-c → skill-d (depth 3)
        # skill-x → skill-y → skill-z → skill-w (depth 3)
        skills = ["skill-a", "skill-b", "skill-c", "skill-d"]
        for i, skill_name in enumerate(skills):
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)

            if i < len(skills) - 1:
                next_skill = skills[i + 1]
                content = f"---\nname: {skill_name}\nskills:\n  - {next_skill}\n---\n"
            else:
                content = f"---\nname: {skill_name}\n---\n"

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

        # Use max_depth of 2 to trigger violation
        rule = ValidationRule(
            rule_type="core:max_dependency_depth",
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 2},
            failure_message="Dependency chain exceeds maximum depth",
            expected_behavior="Dependencies should not exceed depth 2",
        )

        result = validator.validate(rule, bundles[0], bundles)

        if result:
            assert result.failure_details["violation_count"] >= 1

    def test_depth_exactly_at_maximum_no_violation(self, validator, validation_rule, tmp_path):
        """Test that depth exactly at max_depth does not violate (no failure_details)."""
        # Create chain: A → B → C → D (depth 3)
        skills = ["skill-a", "skill-b", "skill-c", "skill-d"]
        for i, skill_name in enumerate(skills):
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)

            if i < len(skills) - 1:
                next_skill = skills[i + 1]
                content = f"---\nname: {skill_name}\nskills:\n  - {next_skill}\n---\n"
            else:
                content = f"---\nname: {skill_name}\n---\n"

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

        # depth 3 == max_depth 3, should pass
        assert result is None

    def test_no_dependencies_no_violation(self, validator, validation_rule, tmp_path):
        """Test that resource with no dependencies has no violation."""
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
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that dependency_chain uses Unicode arrow character."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Should use → (not ->)
        assert "→" in result.failure_details["dependency_chain"]
        assert "->" not in result.failure_details["dependency_chain"]

    def test_failure_details_serializable(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that failure_details can be serialized (for JSON output)."""
        import json

        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        # Should be JSON serializable
        try:
            json.dumps(result.failure_details)
        except (TypeError, ValueError) as e:
            pytest.fail(f"failure_details not JSON serializable: {e}")

    def test_very_deep_chain_no_truncation(self, validator, tmp_path):
        """Test that very long dependency chains are not truncated."""
        # Create chain with 10 levels
        skills = [f"skill-{chr(97 + i)}" for i in range(10)]  # skill-a to skill-j
        for i, skill_name in enumerate(skills):
            skill_dir = tmp_path / ".claude" / "skills" / skill_name
            skill_dir.mkdir(parents=True)

            if i < len(skills) - 1:
                next_skill = skills[i + 1]
                content = f"---\nname: {skill_name}\nskills:\n  - {next_skill}\n---\n"
            else:
                content = f"---\nname: {skill_name}\n---\n"

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

        rule = ValidationRule(
            rule_type="core:max_dependency_depth",
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain exceeds maximum depth",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        result = validator.validate(rule, bundles[0], bundles)

        # Verify all skills are in the chain
        dependency_chain = result.failure_details["dependency_chain"]
        for skill in skills:
            assert skill in dependency_chain

    def test_violation_count_matches_all_violations_length(
        self, validator, validation_rule, project_with_deep_chain
    ):
        """Test that violation_count equals length of all_violations list."""
        bundles = []
        skills = ["skill-a", "skill-b", "skill-c", "skill-d", "skill-e"]
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

        result = validator.validate(validation_rule, bundles[0], bundles)

        assert result.failure_details["violation_count"] == len(
            result.failure_details["all_violations"]
        )
