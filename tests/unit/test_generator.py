"""Unit tests for draft prompt generator."""


from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    PhaseDefinition,
    RuleDefinition,
)
from drift.draft.generator import PromptGenerator


class TestPromptGenerator:
    """Tests for PromptGenerator class."""

    def test_generate_with_custom_draft_instructions(self, temp_dir):
        """Test generating prompt using custom draft_instructions template."""
        rule = RuleDefinition(
            description="Test skill validation",
            scope="project_level",
            context="Skills need documentation",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            draft_instructions="Create {bundle_type} at {file_path} with {description}",
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("skill_validation", rule, target_files, temp_dir)

        assert "Create skill at" in result
        assert ".claude/skills/testing/SKILL.md" in result
        assert "Test skill validation" in result

    def test_generate_from_phases_basic_structure(self, temp_dir):
        """Test generating prompt from phases has correct structure."""
        rule = RuleDefinition(
            description="Test validation rule",
            scope="project_level",
            context="Test context for optimization",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="file_check",
                    type="core:file_exists",
                    params={"file_path": "SKILL.md"},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        # Check basic structure
        assert "# Draft Prompt: test_rule" in result
        assert "**Description**: Test validation rule" in result
        assert "**Context**: Test context for optimization" in result
        assert "## Target Files to Create" in result
        assert ".claude/skills/testing/SKILL.md" in result
        assert "## Validation Requirements" in result
        assert "## Instructions" in result

    def test_generate_with_empty_context(self, temp_dir):
        """Test generating prompt when rule has empty context string."""
        rule = RuleDefinition(
            description="Test validation rule",
            scope="project_level",
            context="",  # Empty string instead of None (which is not allowed)
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        # Empty string is falsy, so context section should not be included
        assert "# Draft Prompt: test_rule" in result
        assert "**Context**:" not in result  # Empty context is not included

    def test_generate_extracts_file_exists_requirement(self, temp_dir):
        """Test extracting requirements from core:file_exists phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_file",
                    type="core:file_exists",
                    params={"file_path": "SKILL.md"},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### File Existence" in result
        # Should show actual target file path, not just filename from params
        assert "File must exist at: `.claude/skills/testing/SKILL.md`" in result

    def test_generate_extracts_yaml_frontmatter_requirement(self, temp_dir):
        """Test extracting requirements from core:yaml_frontmatter phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_frontmatter",
                    type="core:yaml_frontmatter",
                    params={
                        "required_fields": ["title", "description", "version"],
                    },
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### YAML Frontmatter" in result
        assert "YAML frontmatter required with fields:" in result
        assert "`title`" in result
        assert "`description`" in result
        assert "`version`" in result

    def test_generate_extracts_regex_match_requirement(self, temp_dir):
        """Test extracting requirements from core:regex_match phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_pattern",
                    type="core:regex_match",
                    params={"pattern": r"^## Usage"},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### Content Pattern" in result
        assert "Must match regex: `^## Usage`" in result

    def test_generate_extracts_list_match_requirement(self, temp_dir):
        """Test extracting requirements from core:list_match phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_items",
                    type="core:list_match",
                    params={"expected_items": ["item1", "item2", "item3"]},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### Required Items" in result
        assert "Must contain these items:" in result
        assert "`item1`" in result
        assert "`item2`" in result
        assert "`item3`" in result

    def test_generate_extracts_file_size_requirement(self, temp_dir):
        """Test extracting requirements from core:file_size phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_size",
                    type="core:file_size",
                    params={"min_size": 100, "max_size": 5000},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### File Size" in result
        assert "Maximum size: 5000 bytes" in result
        assert "Minimum size: 100 bytes" in result

    def test_generate_extracts_token_count_requirement(self, temp_dir):
        """Test extracting requirements from core:token_count phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_tokens",
                    type="core:token_count",
                    params={"min_tokens": 50, "max_tokens": 1500},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### Token Count" in result
        assert "Maximum tokens: 1500" in result
        assert "Minimum tokens: 50" in result

    def test_generate_extracts_block_line_count_requirement(self, temp_dir):
        """Test extracting requirements from core:block_line_count phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_block_size",
                    type="core:block_line_count",
                    params={"max_lines": 20, "block_pattern": r"```python"},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### Block Size" in result
        assert "Code blocks matching ````python`" in result
        assert "must not exceed 20 lines" in result

    def test_generate_extracts_markdown_link_requirement(self, temp_dir):
        """Test extracting requirements from core:markdown_link phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_links",
                    type="core:markdown_link",
                    params={},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### Links" in result
        assert "All markdown links must be valid" in result

    def test_generate_extracts_json_schema_requirement(self, temp_dir):
        """Test extracting requirements from core:json_schema phase."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "number"},
            },
            "required": ["name"],
        }

        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_json",
                    type="core:json_schema",
                    params={"schema": schema},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### JSON Schema" in result
        assert "Must be valid JSON matching schema:" in result
        assert "name:" in result or "type: string" in result

    def test_generate_extracts_yaml_schema_requirement(self, temp_dir):
        """Test extracting requirements from core:yaml_schema phase."""
        schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "version": {"type": "string"},
            },
            "required": ["title"],
        }

        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_yaml",
                    type="core:yaml_schema",
                    params={"schema": schema},
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### YAML Schema" in result
        assert "Must be valid YAML matching schema:" in result

    def test_generate_extracts_prompt_requirements(self, temp_dir):
        """Test extracting requirements from prompt-based phase."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="quality_check",
                    type="prompt",
                    prompt=(
                        "Check the following requirements:\n"
                        "- MUST include usage examples\n"
                        "- REQUIRED to have clear descriptions\n"
                        "* Should follow best practices"
                    ),
                )
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "### Quality Check" in result
        assert "MUST include usage examples" in result
        assert "REQUIRED to have clear descriptions" in result

    def test_generate_multiple_target_files(self, temp_dir):
        """Test generating prompt with multiple target files."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        generator = PromptGenerator()
        target_files = [
            temp_dir / ".claude" / "skills" / "testing" / "SKILL.md",
            temp_dir / ".claude" / "skills" / "linting" / "SKILL.md",
            temp_dir / ".claude" / "skills" / "code-review" / "SKILL.md",
        ]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "## Target Files to Create" in result
        assert ".claude/skills/testing/SKILL.md" in result
        assert ".claude/skills/linting/SKILL.md" in result
        assert ".claude/skills/code-review/SKILL.md" in result

    def test_generate_includes_verification_instructions(self, temp_dir):
        """Test that generated prompt includes drift verification commands."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        assert "drift --rules test_rule --no-llm" in result
        assert "drift --rules test_rule" in result

    def test_render_template_placeholders(self, temp_dir):
        """Test that template placeholders are correctly replaced."""
        rule = RuleDefinition(
            description="Validate skill documentation",
            scope="project_level",
            context="Skills need proper docs",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            draft_instructions=(
                "Rule: {rule_name}\n"
                "Description: {description}\n"
                "Context: {context}\n"
                "Type: {bundle_type}\n"
                "File: {file_path}\n"
                "Files: {file_paths}"
            ),
        )

        generator = PromptGenerator()
        target_files = [
            temp_dir / ".claude" / "skills" / "testing" / "SKILL.md",
            temp_dir / ".claude" / "skills" / "linting" / "SKILL.md",
        ]

        result = generator.generate("skill_validation", rule, target_files, temp_dir)

        assert "Rule: skill_validation" in result
        assert "Description: Validate skill documentation" in result
        assert "Context: Skills need proper docs" in result
        assert "Type: skill" in result
        assert "File: .claude/skills/testing/SKILL.md" in result
        assert ".claude/skills/testing/SKILL.md, .claude/skills/linting/SKILL.md" in result

    def test_generate_without_phases(self, temp_dir):
        """Test generating prompt when rule has no phases."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=None,
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        # Should still generate basic prompt without requirements section
        assert "# Draft Prompt: test_rule" in result
        assert "## Target Files to Create" in result
        assert "## Instructions" in result
        # No validation requirements section
        assert "## Validation Requirements" not in result

    def test_generate_extracts_multiple_phase_types(self, temp_dir):
        """Test extracting requirements from multiple different phase types."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_file",
                    type="core:file_exists",
                    params={"file_path": "SKILL.md"},
                ),
                PhaseDefinition(
                    name="check_frontmatter",
                    type="core:yaml_frontmatter",
                    params={"required_fields": ["title"]},
                ),
                PhaseDefinition(
                    name="check_size",
                    type="core:token_count",
                    params={"max_tokens": 1500},
                ),
            ],
        )

        generator = PromptGenerator()
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        result = generator.generate("test_rule", rule, target_files, temp_dir)

        # Should include all requirements
        assert "### File Existence" in result
        assert "### YAML Frontmatter" in result
        assert "### Token Count" in result
