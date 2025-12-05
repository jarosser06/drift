"""Additional tests for Claude Circular Dependencies Validator to achieve 95%+ coverage."""

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeCircularDependenciesValidator


class TestCircularDependenciesValidatorExceptionHandling:
    """Test exception handling and edge cases in CircularDependenciesValidator."""

    @pytest.fixture
    def project_root(self, tmp_path):
        """Create temporary project structure."""
        (tmp_path / ".claude" / "skills" / "skill-a").mkdir(parents=True)
        return tmp_path

    def test_handles_file_with_invalid_yaml(self, tmp_path):
        """Test validator handles files with invalid YAML gracefully."""
        # Create a file with malformed YAML
        skill_dir = tmp_path / ".claude" / "skills" / "bad-yaml"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: bad-yaml\nskills: [broken yaml\n---\n")

        bundle = DocumentBundle(
            bundle_id="bad-yaml",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_file),
                    relative_path=".claude/skills/bad-yaml/SKILL.md",
                    content=skill_file.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        # Should not raise exception - malformed files are skipped (lines 68-70)
        result = validator.validate(rule, bundle, [bundle])
        assert result is None

    def test_handles_missing_resource_in_graph(self, tmp_path):
        """Test validator handles resources not in graph gracefully."""
        # Create skill that references non-existent dependency
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_file = skill_a_dir / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - nonexistent\n---\n")

        bundle = DocumentBundle(
            bundle_id="skill-a",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_a_file),
                    relative_path=".claude/skills/skill-a/SKILL.md",
                    content=skill_a_file.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        # Should handle missing dependencies gracefully
        result = validator.validate(rule, bundle, [bundle])
        assert result is None

    def test_handles_file_that_cannot_be_loaded(self, tmp_path):
        """Test validator handles files that raise exceptions during load."""
        # Create a file with content that will cause parsing issues
        skill_dir = tmp_path / ".claude" / "skills" / "problematic"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        # Write content that might cause issues
        skill_file.write_text("---\n!!python/object:dict\n---\n")

        bundle = DocumentBundle(
            bundle_id="problematic",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_file),
                    relative_path=".claude/skills/problematic/SKILL.md",
                    content=skill_file.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        # Should not raise exception (lines 68-70 exception handling)
        result = validator.validate(rule, bundle, [bundle])
        assert result is None

    def test_validates_file_without_resource_type(self, tmp_path):
        """Test validator skips files that don't match known resource types."""
        # Create a file that doesn't match skill/command/agent patterns
        other_dir = tmp_path / "other"
        other_dir.mkdir(parents=True)
        other_file = other_dir / "README.md"
        other_file.write_text("# Some documentation\n")

        bundle = DocumentBundle(
            bundle_id="other",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(other_file),
                    relative_path="other/README.md",
                    content=other_file.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        # Should skip files without recognized resource type (line 78)
        result = validator.validate(rule, bundle, [bundle])
        assert result is None

    def test_handles_keyerror_during_cycle_detection(self, tmp_path):
        """Test validator handles KeyError when resource not in graph."""
        # Create a valid skill file
        skill_dir = tmp_path / ".claude" / "skills" / "orphan"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: orphan\n---\n")

        # Create bundle but don't include it in all_bundles
        # This will cause resource to not be in graph during cycle detection
        bundle = DocumentBundle(
            bundle_id="orphan",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_file),
                    relative_path=".claude/skills/orphan/SKILL.md",
                    content=skill_file.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        # Create different bundle for all_bundles to create mismatch
        other_skill_dir = tmp_path / ".claude" / "skills" / "other"
        other_skill_dir.mkdir(parents=True)
        other_skill_file = other_skill_dir / "SKILL.md"
        other_skill_file.write_text("---\nname: other\n---\n")

        other_bundle = DocumentBundle(
            bundle_id="other",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(other_skill_file),
                    relative_path=".claude/skills/other/SKILL.md",
                    content=other_skill_file.read_text(),
                )
            ],
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        # Should handle KeyError gracefully (lines 87-89)
        result = validator.validate(rule, bundle, [other_bundle])
        assert result is None

    def test_multiple_files_in_bundle_with_cycles(self, tmp_path):
        """Test validator with multiple files in a single bundle."""
        # Create two skills with a cycle
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_file = skill_a_dir / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_file = skill_b_dir / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        # Create bundle with both files
        bundle = DocumentBundle(
            bundle_id="multi",
            bundle_type="skill",
            bundle_strategy="individual",
            files=[
                DocumentFile(
                    file_path=str(skill_a_file),
                    relative_path=".claude/skills/skill-a/SKILL.md",
                    content=skill_a_file.read_text(),
                ),
                DocumentFile(
                    file_path=str(skill_b_file),
                    relative_path=".claude/skills/skill-b/SKILL.md",
                    content=skill_b_file.read_text(),
                ),
            ],
            project_path=tmp_path,
        )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        result = validator.validate(rule, bundle, [bundle])
        assert result is not None
        # Should detect cycles from both files
        assert "skill-a" in result.observed_issue or "skill-b" in result.observed_issue

    def test_command_with_transitive_cycle(self, tmp_path):
        """Test validator detects cycles through command dependencies."""
        # Command → Skill A → Skill B → Skill A
        cmd_dir = tmp_path / ".claude" / "commands"
        cmd_dir.mkdir(parents=True)
        cmd_file = cmd_dir / "test.md"
        cmd_file.write_text("---\ndescription: Test\nskills:\n  - skill-a\n---\n")

        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_file = skill_a_dir / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_file = skill_b_dir / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-a\n---\n")

        bundles = []
        for name, path in [
            ("test", cmd_file),
            ("skill-a", skill_a_file),
            ("skill-b", skill_b_file),
        ]:
            bundle_type = "command" if "test" in name else "skill"
            rel_path = (
                ".claude/commands/test.md"
                if bundle_type == "command"
                else f".claude/skills/{name}/SKILL.md"
            )
            bundles.append(
                DocumentBundle(
                    bundle_id=name,
                    bundle_type=bundle_type,
                    bundle_strategy="individual",
                    files=[
                        DocumentFile(
                            file_path=str(path),
                            relative_path=rel_path,
                            content=path.read_text(),
                        )
                    ],
                    project_path=tmp_path,
                )
            )

        validator = ClaudeCircularDependenciesValidator()
        rule = ValidationRule(
            rule_type=ValidationType.CIRCULAR_DEPENDENCIES,
            description="Check for circular dependencies",
            params={"resource_dirs": [".claude/skills", ".claude/commands"]},
            failure_message="Found circular dependency",
            expected_behavior="Dependencies should not form cycles",
        )

        # Check skill-a which has a cycle
        result = validator.validate(rule, bundles[1], bundles)
        assert result is not None
        assert "cycle" in result.observed_issue.lower()
