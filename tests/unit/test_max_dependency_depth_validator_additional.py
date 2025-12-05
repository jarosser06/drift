"""Additional tests for Claude Max Dependency Depth Validator to achieve 95%+ coverage."""

import pytest

from drift.config.models import ValidationRule, ValidationType
from drift.core.types import DocumentBundle, DocumentFile
from drift.validation.validators import ClaudeMaxDependencyDepthValidator


class TestMaxDependencyDepthValidatorExceptionHandling:
    """Test exception handling and edge cases in MaxDependencyDepthValidator."""

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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        # Should not raise exception - malformed files are skipped (lines 72-74)
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        # Should handle missing dependencies gracefully
        result = validator.validate(rule, bundle, [bundle])
        # Depth will be 1 (to the missing dependency)
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        # Should not raise exception (lines 72-74 exception handling)
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        # Should skip files without recognized resource type (line 82)
        result = validator.validate(rule, bundle, [bundle])
        assert result is None

    def test_handles_keyerror_during_depth_calculation(self, tmp_path):
        """Test validator handles KeyError when resource not in graph."""
        # Create a valid skill file
        skill_dir = tmp_path / ".claude" / "skills" / "orphan"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: orphan\n---\n")

        # Create bundle but don't include it in all_bundles
        # This will cause resource to not be in graph during depth calculation
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 3},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 3",
        )

        # Should handle KeyError gracefully (lines 90-92)
        result = validator.validate(rule, bundle, [other_bundle])
        assert result is None

    def test_multiple_files_in_bundle_with_violations(self, tmp_path):
        """Test validator with multiple files in a single bundle."""
        # Create two skills with different depths
        # skill-a → skill-b → skill-c → skill-d (depth 3)
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_file = skill_a_dir / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_file = skill_b_dir / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-c\n---\n")

        skill_c_dir = tmp_path / ".claude" / "skills" / "skill-c"
        skill_c_dir.mkdir(parents=True)
        skill_c_file = skill_c_dir / "SKILL.md"
        skill_c_file.write_text("---\nname: skill-c\nskills:\n  - skill-d\n---\n")

        skill_d_dir = tmp_path / ".claude" / "skills" / "skill-d"
        skill_d_dir.mkdir(parents=True)
        skill_d_file = skill_d_dir / "SKILL.md"
        skill_d_file.write_text("---\nname: skill-d\n---\n")

        # Create bundle with multiple files
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

        # Create all bundles
        all_bundles = [bundle]
        for name, path in [("skill-c", skill_c_file), ("skill-d", skill_d_file)]:
            all_bundles.append(
                DocumentBundle(
                    bundle_id=name,
                    bundle_type="skill",
                    bundle_strategy="individual",
                    files=[
                        DocumentFile(
                            file_path=str(path),
                            relative_path=f".claude/skills/{name}/SKILL.md",
                            content=path.read_text(),
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

        result = validator.validate(rule, bundle, all_bundles)
        assert result is not None
        # skill-a has depth 3, should violate max_depth of 2
        assert "3" in result.observed_issue
        assert "skill-a" in result.observed_issue

    def test_agent_with_deep_transitive_dependencies(self, tmp_path):
        """Test validator with agent that has deep transitive dependencies."""
        # Agent → Command → Skill A → Skill B → Skill C
        agent_dir = tmp_path / ".claude" / "agents"
        agent_dir.mkdir(parents=True)
        agent_file = agent_dir / "test-agent.md"
        agent_file.write_text("---\ndescription: Test\nskills:\n  - skill-a\n---\n")

        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_file = skill_a_dir / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_file = skill_b_dir / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\nskills:\n  - skill-c\n---\n")

        skill_c_dir = tmp_path / ".claude" / "skills" / "skill-c"
        skill_c_dir.mkdir(parents=True)
        skill_c_file = skill_c_dir / "SKILL.md"
        skill_c_file.write_text("---\nname: skill-c\n---\n")

        bundles = []
        for name, path, btype in [
            ("test-agent", agent_file, "agent"),
            ("skill-a", skill_a_file, "skill"),
            ("skill-b", skill_b_file, "skill"),
            ("skill-c", skill_c_file, "skill"),
        ]:
            rel_path = (
                ".claude/agents/test-agent.md"
                if btype == "agent"
                else f".claude/skills/{name}/SKILL.md"
            )
            bundles.append(
                DocumentBundle(
                    bundle_id=name,
                    bundle_type=btype,
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

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/agents", ".claude/skills"], "max_depth": 2},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 2",
        )

        # Check agent which has depth 3
        result = validator.validate(rule, bundles[0], bundles)
        assert result is not None
        assert "3" in result.observed_issue
        assert "test-agent" in result.observed_issue

    def test_zero_max_depth(self, tmp_path):
        """Test validator with max_depth of 0 (no dependencies allowed)."""
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_file = skill_a_dir / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_file = skill_b_dir / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\n---\n")

        bundles = [
            DocumentBundle(
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
            ),
            DocumentBundle(
                bundle_id="skill-b",
                bundle_type="skill",
                bundle_strategy="individual",
                files=[
                    DocumentFile(
                        file_path=str(skill_b_file),
                        relative_path=".claude/skills/skill-b/SKILL.md",
                        content=skill_b_file.read_text(),
                    )
                ],
                project_path=tmp_path,
            ),
        ]

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 0},
            failure_message="Dependency chain too deep",
            expected_behavior="No dependencies allowed",
        )

        # skill-a has depth 1, should violate max_depth of 0
        result = validator.validate(rule, bundles[0], bundles)
        assert result is not None
        assert "1" in result.observed_issue
        assert "0" in result.observed_issue

    def test_very_large_max_depth(self, tmp_path):
        """Test validator with very large max_depth that shouldn't trigger."""
        skill_a_dir = tmp_path / ".claude" / "skills" / "skill-a"
        skill_a_dir.mkdir(parents=True)
        skill_a_file = skill_a_dir / "SKILL.md"
        skill_a_file.write_text("---\nname: skill-a\nskills:\n  - skill-b\n---\n")

        skill_b_dir = tmp_path / ".claude" / "skills" / "skill-b"
        skill_b_dir.mkdir(parents=True)
        skill_b_file = skill_b_dir / "SKILL.md"
        skill_b_file.write_text("---\nname: skill-b\n---\n")

        bundles = [
            DocumentBundle(
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
            ),
            DocumentBundle(
                bundle_id="skill-b",
                bundle_type="skill",
                bundle_strategy="individual",
                files=[
                    DocumentFile(
                        file_path=str(skill_b_file),
                        relative_path=".claude/skills/skill-b/SKILL.md",
                        content=skill_b_file.read_text(),
                    )
                ],
                project_path=tmp_path,
            ),
        ]

        validator = ClaudeMaxDependencyDepthValidator()
        rule = ValidationRule(
            rule_type=ValidationType.MAX_DEPENDENCY_DEPTH,
            description="Check dependency depth",
            params={"resource_dirs": [".claude/skills"], "max_depth": 1000},
            failure_message="Dependency chain too deep",
            expected_behavior="Dependencies should not exceed depth 1000",
        )

        # skill-a has depth 1, should not violate max_depth of 1000
        result = validator.validate(rule, bundles[0], bundles)
        assert result is None
