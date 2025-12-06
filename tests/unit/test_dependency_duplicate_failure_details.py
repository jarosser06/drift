"""Tests for DependencyDuplicateValidator failure_details feature."""

import pytest

from drift.config.models import ValidationRule
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeDependencyDuplicateValidator


class TestDependencyDuplicateValidatorFailureDetails:
    """Tests for DependencyDuplicateValidator failure_details enhancement."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ClaudeDependencyDuplicateValidator()

    @pytest.fixture
    def validation_rule(self):
        """Create standard validation rule."""
        return ValidationRule(
            rule_type="core:dependency_duplicate",
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found redundant dependency",
            expected_behavior="Skills should declare only direct dependencies",
        )

    @pytest.fixture
    def project_with_duplicate(self, tmp_path):
        """Create project with duplicate/redundant dependency."""
        # skill-b → skill-a
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\nname: skill-a\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / "SKILL.md").write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        # skill-c → skill-b, skill-a (redundant - skill-a already in skill-b)
        skill_c_dir = tmp_path / ".claude" / "skills" / "skill-c"
        skill_c_dir.mkdir(parents=True)
        (skill_c_dir / "SKILL.md").write_text(
            "---\nname: skill-c\nskills:\n  - skill-b\n  - skill-a\n---\n"
        )

        return tmp_path

    @pytest.fixture
    def project_with_multiple_duplicates(self, tmp_path):
        """Create project with multiple redundant dependencies."""
        # Chain: skill-d → skill-c → skill-b → skill-a
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\nname: skill-a\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / "SKILL.md").write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        skill_c_dir = tmp_path / ".claude" / "skills" / "skill-c"
        skill_c_dir.mkdir(parents=True)
        (skill_c_dir / "SKILL.md").write_text("---\nname: skill-c\nskills:\n  - skill-b\n---\n")

        # skill-d depends on skill-c, skill-b, skill-a (last 2 are redundant)
        skill_d_dir = tmp_path / ".claude" / "skills" / "skill-d"
        skill_d_dir.mkdir(parents=True)
        (skill_d_dir / "SKILL.md").write_text(
            "---\nname: skill-d\nskills:\n  - skill-c\n  - skill-b\n  - skill-a\n---\n"
        )

        return tmp_path

    def test_duplicate_has_failure_details(
        self, validator, validation_rule, project_with_duplicate
    ):
        """Test that duplicate detection includes failure_details in result."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        # Test skill-c which has redundant dependency
        result = validator.validate(validation_rule, bundles[2], bundles)

        # Verify failure_details exists
        assert result is not None
        assert result.failure_details is not None
        assert isinstance(result.failure_details, dict)

    def test_failure_details_structure(self, validator, validation_rule, project_with_duplicate):
        """Test that failure_details has expected structure."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        # Verify structure
        assert "duplicate_resource" in result.failure_details
        assert "declared_by" in result.failure_details
        assert "duplicate_count" in result.failure_details
        assert "all_duplicates" in result.failure_details

    def test_failure_details_duplicate_resource_correct(
        self, validator, validation_rule, project_with_duplicate
    ):
        """Test that duplicate_resource identifies the redundant dependency."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        # skill-a is the duplicate
        assert result.failure_details["duplicate_resource"] == "skill-a"

    def test_failure_details_declared_by_correct(
        self, validator, validation_rule, project_with_duplicate
    ):
        """Test that declared_by identifies who already declares the dependency."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        # skill-b already declares skill-a
        assert result.failure_details["declared_by"] == "skill-b"

    def test_message_includes_duplicate_details(
        self, validator, validation_rule, project_with_duplicate
    ):
        """Test that observed_issue message includes duplicate details."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        # Message should contain duplicate resource and declarer
        assert "skill-a" in result.observed_issue
        assert "skill-b" in result.observed_issue
        assert "redundant" in result.observed_issue.lower()

    def test_all_duplicates_structure(self, validator, validation_rule, project_with_duplicate):
        """Test that all_duplicates contains detailed info for each duplicate."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        # Each duplicate should have file, duplicate_resource, and declared_by
        for duplicate in result.failure_details["all_duplicates"]:
            assert "file" in duplicate
            assert "duplicate_resource" in duplicate
            assert "declared_by" in duplicate

    def test_multiple_duplicates_in_bundle(
        self, validator, validation_rule, project_with_multiple_duplicates
    ):
        """Test handling of multiple duplicates in same bundle."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d"]:
            skill_path = (
                project_with_multiple_duplicates / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_multiple_duplicates,
                )
            )

        # skill-d has 2 redundant dependencies
        result = validator.validate(validation_rule, bundles[3], bundles)

        assert result is not None
        assert result.failure_details["duplicate_count"] >= 1
        assert len(result.failure_details["all_duplicates"]) >= 1

    def test_multiple_duplicates_message_format(
        self, validator, validation_rule, project_with_multiple_duplicates
    ):
        """Test message formatting for multiple duplicates."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d"]:
            skill_path = (
                project_with_multiple_duplicates / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_multiple_duplicates,
                )
            )

        result = validator.validate(validation_rule, bundles[3], bundles)

        # Message should mention multiple duplicates if count > 1
        if result and result.failure_details["duplicate_count"] > 1:
            assert "duplicates detected" in result.observed_issue.lower()

    def test_no_duplicates_returns_none(self, validator, validation_rule, tmp_path):
        """Test that no duplicates returns None (no failure_details)."""
        # skill-a has no dependencies
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\nname: skill-a\n---\n")

        # skill-b depends only on skill-a (no redundancy)
        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / "SKILL.md").write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
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

        result = validator.validate(validation_rule, bundles[1], bundles)

        assert result is None

    def test_transitive_duplicate_detection(
        self, validator, validation_rule, project_with_multiple_duplicates
    ):
        """Test detection of transitive duplicates (A→B→C, A also depends on C)."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c", "skill-d"]:
            skill_path = (
                project_with_multiple_duplicates / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_multiple_duplicates,
                )
            )

        result = validator.validate(validation_rule, bundles[3], bundles)

        # skill-d → skill-c → skill-b → skill-a
        # skill-d also directly declares skill-b and skill-a (both redundant)
        assert result is not None

    def test_failure_details_file_paths_match_violations(
        self, validator, validation_rule, project_with_duplicate
    ):
        """Test that file_paths in DocumentRule match files in failure_details."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        # Verify file_paths list contains files from all_duplicates
        for duplicate in result.failure_details["all_duplicates"]:
            assert duplicate["file"] in result.file_paths

    def test_failure_details_serializable(self, validator, validation_rule, project_with_duplicate):
        """Test that failure_details can be serialized (for JSON output)."""
        import json

        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        # Should be JSON serializable
        try:
            json.dumps(result.failure_details)
        except (TypeError, ValueError) as e:
            pytest.fail(f"failure_details not JSON serializable: {e}")

    def test_duplicate_count_matches_all_duplicates_length(
        self, validator, validation_rule, project_with_duplicate
    ):
        """Test that duplicate_count equals length of all_duplicates list."""
        bundles = []
        for skill_name in ["skill-a", "skill-b", "skill-c"]:
            skill_path = project_with_duplicate / ".claude" / "skills" / skill_name / "SKILL.md"
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
                    project_path=project_with_duplicate,
                )
            )

        result = validator.validate(validation_rule, bundles[2], bundles)

        assert result.failure_details["duplicate_count"] == len(
            result.failure_details["all_duplicates"]
        )

    def test_command_with_redundant_skill(self, validator, tmp_path):
        """Test detection of redundant dependency in command."""
        # Create skills
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        (skill_a_dir / "SKILL.md").write_text("---\nname: skill-a\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        (skill_b_dir / "SKILL.md").write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        # Create command that depends on both skill-b and skill-a (redundant)
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        (cmd_dir / "test-cmd.md").write_text(
            "---\ndescription: Test\nskills:\n  - skill-b\n  - skill-a\n---\n"
        )

        # Create bundles
        bundles = []
        for skill_name in ["skill-a", "skill-b"]:
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

        cmd_path = tmp_path / ".claude" / "commands" / "test-cmd.md"
        cmd_bundle = DocumentBundle(
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
            project_path=tmp_path,
        )
        bundles.append(cmd_bundle)

        rule = ValidationRule(
            rule_type="core:dependency_duplicate",
            description="Check for redundant dependencies",
            params={"resource_dirs": [".claude/skills", ".claude/commands"]},
            failure_message="Found redundant dependency",
            expected_behavior="Commands should declare only direct dependencies",
        )

        result = validator.validate(rule, cmd_bundle, bundles)

        # Command should have redundant dependency
        assert result is not None
        assert result.failure_details is not None
        assert "skill-a" in result.failure_details["duplicate_resource"]
