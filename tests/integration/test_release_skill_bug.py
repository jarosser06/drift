"""Integration test to reproduce the release skill bug.

This test simulates the real drift validation scenario where only skill.md exists
but the system reports finding both SKILL.md and skill.md.
"""

from drift.config.models import BundleStrategy, DocumentBundleConfig
from drift.documents.loader import DocumentLoader


class TestReleaseSkillBug:
    """Test to reproduce the release skill bundle loading bug."""

    def test_skill_bundle_only_loads_existing_files(self, temp_dir):
        """Test that skill bundle only includes files that actually exist."""
        # Create a skill directory with ONLY lowercase skill.md
        skill_dir = temp_dir / ".claude" / "skills" / "release"
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write ONLY lowercase skill.md
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("---\nname: release\ndescription: Test skill\n---\n\n# Test")

        # Verify file exists
        assert skill_file.exists()
        # Note: On case-insensitive filesystems, SKILL.md and skill.md refer to same file
        # so we can't assert that (skill_dir / "SKILL.md").exists() == False

        # Create bundle config matching drift's skill_validation config
        bundle_config = DocumentBundleConfig(
            bundle_type="skill",
            bundle_strategy=BundleStrategy.INDIVIDUAL,
            file_patterns=[".claude/skills/*/SKILL.md", ".claude/skills/*/skill.md"],
        )

        # Load bundles using DocumentLoader
        loader = DocumentLoader(temp_dir)
        bundles = loader.load_bundles(bundle_config)

        # Should have exactly ONE bundle for the release skill
        assert len(bundles) == 1, f"Expected 1 bundle, got {len(bundles)}"

        bundle = bundles[0]

        # The bundle should have exactly ONE file (skill.md)
        assert len(bundle.files) == 1, (
            f"Expected 1 file in bundle, got {len(bundle.files)}: "
            f"{[f.relative_path for f in bundle.files]}"
        )

        # The file should be skill.md (lowercase), NOT SKILL.md
        file_path = bundle.files[0].relative_path
        assert "skill.md" in file_path.lower()

        # CRITICAL: Should NOT have both SKILL.md and skill.md in the same bundle
        file_paths = [f.relative_path for f in bundle.files]
        lowercase_count = sum(1 for p in file_paths if "skill.md" in p.lower())
        assert (
            lowercase_count == 1
        ), f"File appears {lowercase_count} times in bundle (expected 1): {file_paths}"

    def test_discover_files_deduplication_on_case_insensitive_fs(self, temp_dir):
        """Test that _discover_files properly deduplicates on case-insensitive filesystems."""
        # Create skill directory with lowercase file
        skill_dir = temp_dir / ".claude" / "skills" / "test"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "skill.md"
        skill_file.write_text("test content")

        loader = DocumentLoader(temp_dir)

        # Search for both uppercase and lowercase patterns
        # On case-insensitive FS, both patterns match the same physical file
        found_files = loader._discover_files(
            [".claude/skills/*/SKILL.md", ".claude/skills/*/skill.md"]
        )

        # Should only return ONE file, not two
        assert len(found_files) == 1, f"Expected 1 file, got {len(found_files)}: {found_files}"

        # The returned file should match what actually exists
        assert found_files[0].name.lower() == "skill.md"

    def test_prompt_generation_matches_actual_files(self, temp_dir):
        """Test that the generated LLM prompt only mentions files that exist."""
        # Setup
        skill_dir = temp_dir / ".claude" / "skills" / "release"
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "skill.md"
        skill_file.write_text("---\nname: release\n---\n\n# Release Skill")

        bundle_config = DocumentBundleConfig(
            bundle_type="skill",
            bundle_strategy=BundleStrategy.INDIVIDUAL,
            file_patterns=[".claude/skills/*/SKILL.md", ".claude/skills/*/skill.md"],
        )

        loader = DocumentLoader(temp_dir)
        bundles = loader.load_bundles(bundle_config)

        assert len(bundles) == 1
        bundle = bundles[0]

        # Generate the prompt that would be sent to LLM
        formatted_prompt = loader.format_bundle_for_llm(bundle)

        # Count how many times skill.md appears in the prompt
        skill_md_occurrences = formatted_prompt.lower().count("skill.md")

        # Should appear exactly ONCE (as the file path header)
        assert skill_md_occurrences == 1, (
            f"skill.md appears {skill_md_occurrences} times in prompt, expected 1.\n"
            f"Prompt:\n{formatted_prompt}"
        )

        # Should NOT mention SKILL.md (uppercase)
        assert "SKILL.md" not in formatted_prompt, (
            f"Prompt incorrectly mentions SKILL.md which doesn't exist.\n"
            f"Prompt:\n{formatted_prompt}"
        )
