"""Test for document analysis prompt generation bug.

This test validates that the document analysis prompt correctly reflects
the actual files being analyzed, and doesn't hallucinate duplicate files
or missing files.
"""

from drift.core.analyzer import DriftAnalyzer
from drift.core.types import DocumentBundle, DocumentFile


class TestDocumentAnalysisPromptGeneration:
    """Test document analysis prompt generation edge cases."""

    def test_prompt_only_includes_actual_files(self, sample_drift_config, temp_dir):
        """Test that prompt only lists files that actually exist in the bundle."""
        # Create a bundle with a single file
        single_file = DocumentFile(
            relative_path="skill.md",
            content="---\ndescription: Test skill\n---\n\n# Test Skill",
            file_path=temp_dir / "skill.md",
        )

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[single_file],  # Only ONE file
        )

        # Create a mock rule type config
        from types import SimpleNamespace

        rule_type = SimpleNamespace(
            description="Test validation",
            phases=[
                SimpleNamespace(
                    prompt="Check the frontmatter for name field",
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        prompt = analyzer._build_document_analysis_prompt(bundle, "test_type", rule_type)

        # Validate prompt structure
        assert "**Files Being Analyzed:**" in prompt
        assert "skill.md" in prompt

        # CRITICAL: Should NOT mention SKILL.md (uppercase) if it doesn't exist
        assert "SKILL.md" not in prompt

        # Should only mention the file once
        skill_md_count = prompt.count("skill.md:")
        assert (
            skill_md_count == 1
        ), f"Expected skill.md to appear once, found {skill_md_count} times"

    def test_prompt_with_multiple_actual_files(self, sample_drift_config, temp_dir):
        """Test that prompt correctly lists multiple files when they exist."""
        # Create bundle with TWO actual files
        file1 = DocumentFile(
            relative_path="skill1.md",
            content="---\nname: skill1\n---\n\n# Skill 1",
            file_path=temp_dir / "skill1.md",
        )
        file2 = DocumentFile(
            relative_path="skill2.md",
            content="---\nname: skill2\n---\n\n# Skill 2",
            file_path=temp_dir / "skill2.md",
        )

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="skill",
            bundle_strategy="collection",
            project_path=temp_dir,
            files=[file1, file2],  # Two files
        )

        from types import SimpleNamespace

        rule_type = SimpleNamespace(
            description="Test validation",
            phases=[
                SimpleNamespace(
                    prompt="Check all files",
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        prompt = analyzer._build_document_analysis_prompt(bundle, "test_type", rule_type)

        # Should list BOTH files
        assert "skill1.md" in prompt
        assert "skill2.md" in prompt

        # Each file should appear exactly once
        assert prompt.count("skill1.md:") == 1
        assert prompt.count("skill2.md:") == 1

    def test_prompt_includes_file_content(self, sample_drift_config, temp_dir):
        """Test that prompt includes actual file content, not just paths."""
        file_content = "---\ndescription: Test\n---\n\n# Test Content\nSome body text"

        single_file = DocumentFile(
            relative_path="test.md",
            content=file_content,
            file_path=temp_dir / "test.md",
        )

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="skill",
            bundle_strategy="individual",
            project_path=temp_dir,
            files=[single_file],
        )

        from types import SimpleNamespace

        rule_type = SimpleNamespace(
            description="Test validation",
            phases=[
                SimpleNamespace(
                    prompt="Check content",
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        prompt = analyzer._build_document_analysis_prompt(bundle, "test_type", rule_type)

        # Should include file content
        assert "Test Content" in prompt
        assert "Some body text" in prompt

    def test_prompt_with_case_sensitive_filenames(self, sample_drift_config, temp_dir):
        """Test that prompt distinguishes between SKILL.md and skill.md."""
        # Create bundle with BOTH uppercase and lowercase files
        uppercase_file = DocumentFile(
            relative_path="SKILL.md",
            content="---\nname: uppercase\n---\n\n# Uppercase",
            file_path=temp_dir / "SKILL.md",
        )
        lowercase_file = DocumentFile(
            relative_path="skill.md",
            content="---\nname: lowercase\n---\n\n# Lowercase",
            file_path=temp_dir / "skill.md",
        )

        bundle = DocumentBundle(
            bundle_id="test_bundle",
            bundle_type="skill",
            bundle_strategy="collection",
            project_path=temp_dir,
            files=[uppercase_file, lowercase_file],
        )

        from types import SimpleNamespace

        rule_type = SimpleNamespace(
            description="Test validation",
            phases=[
                SimpleNamespace(
                    prompt="Check files",
                )
            ],
        )

        analyzer = DriftAnalyzer(config=sample_drift_config, project_path=temp_dir)
        prompt = analyzer._build_document_analysis_prompt(bundle, "test_type", rule_type)

        # Should list BOTH files with correct casing
        assert "SKILL.md" in prompt
        assert "skill.md" in prompt

        # Should have different content
        assert "# Uppercase" in prompt
        assert "# Lowercase" in prompt
