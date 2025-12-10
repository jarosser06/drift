"""Integration tests for draft workflow end-to-end."""


import yaml

from drift.config.loader import ConfigLoader
from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    PhaseDefinition,
    RuleDefinition,
)
from drift.draft import DraftEligibility, FileExistenceChecker, FilePatternResolver, PromptGenerator


class TestDraftWorkflow:
    """Integration tests for complete draft workflow."""

    def test_draft_workflow_skill_validation(self, temp_dir):
        """Test complete workflow: eligibility check -> resolve -> generate."""
        # Create .drift_rules.yaml with skill validation rule
        rules_file = temp_dir / ".drift_rules.yaml"
        rules_content = {
            "skill_validation": {
                "description": "Validate skill documentation structure and content",
                "scope": "project_level",
                "context": "Skills need consistent structure",
                "requires_project_context": True,
                "document_bundle": {
                    "bundle_type": "skill",
                    "file_patterns": [".claude/skills/*/SKILL.md"],
                    "bundle_strategy": "individual",
                },
                "phases": [
                    {
                        "name": "check_frontmatter",
                        "type": "core:yaml_frontmatter",
                        "params": {
                            "required_fields": ["title", "description", "version"],
                        },
                    },
                    {
                        "name": "check_sections",
                        "type": "core:regex_match",
                        "params": {
                            "pattern": "^## Usage",
                        },
                    },
                ],
            }
        }

        with open(rules_file, "w") as f:
            yaml.dump(rules_content, f)

        # Create skill directory structure
        skills_dir = temp_dir / ".claude" / "skills"
        (skills_dir / "testing").mkdir(parents=True)
        (skills_dir / "linting").mkdir(parents=True)

        # Load configuration
        config = ConfigLoader.load_config(temp_dir, rules_files=[str(rules_file)])

        # Get rule
        rule_name = "skill_validation"
        rule = config.rule_definitions[rule_name]

        # Step 1: Check eligibility
        eligible, error = DraftEligibility.check(rule)
        assert eligible is True
        assert error is None

        # Step 2: Resolve file patterns - wildcard patterns now return empty
        resolver = FilePatternResolver(temp_dir)
        target_files = []
        for pattern in rule.document_bundle.file_patterns:
            resolved = resolver.resolve(pattern)
            target_files.extend(resolved)

        # Wildcard patterns return empty list
        assert len(target_files) == 0

        # Step 3: With wildcard pattern, must provide specific target file
        # Simulate user providing --target-file
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        # Step 4: Check file existence
        any_exist, existing = FileExistenceChecker.check(target_files)
        assert any_exist is False
        assert existing == []

        # Step 5: Generate prompt
        generator = PromptGenerator()
        prompt = generator.generate(rule_name, rule, target_files, temp_dir)

        # Verify prompt content
        assert "# Draft Prompt: skill_validation" in prompt
        assert "Validate skill documentation structure and content" in prompt
        assert "Skills need consistent structure" in prompt
        assert ".claude/skills/testing/SKILL.md" in prompt
        assert "### YAML Frontmatter" in prompt
        assert "`title`" in prompt
        assert "`description`" in prompt
        assert "`version`" in prompt
        assert "### Content Pattern" in prompt
        assert "^## Usage" in prompt

    def test_draft_workflow_with_existing_files(self, temp_dir):
        """Test workflow when target file already exists."""
        # Create skill directory
        skills_dir = temp_dir / ".claude" / "skills"
        testing_dir = skills_dir / "testing"
        testing_dir.mkdir(parents=True)

        # Create file
        (testing_dir / "SKILL.md").write_text("# Existing skill")

        # With wildcard pattern, must provide specific target file
        target_files = [testing_dir / "SKILL.md"]

        # Check existence
        any_exist, existing = FileExistenceChecker.check(target_files)
        assert any_exist is True
        assert len(existing) == 1
        assert testing_dir / "SKILL.md" in existing

    def test_draft_workflow_command_validation(self, temp_dir):
        """Test workflow with command validation rule."""
        # Create command validation rule
        rule = RuleDefinition(
            description="Validate command documentation",
            scope="project_level",
            context="Commands need clear documentation",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="command",
                file_patterns=[".claude/commands/*.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="check_size",
                    type="core:token_count",
                    params={"max_tokens": 1500},
                ),
                PhaseDefinition(
                    name="check_description",
                    type="core:regex_match",
                    params={"pattern": r"^# "},
                ),
            ],
        )

        # Create commands directory
        commands_dir = temp_dir / ".claude" / "commands"
        commands_dir.mkdir(parents=True)

        # Check eligibility
        eligible, error = DraftEligibility.check(rule)
        assert eligible is True

        # Resolve patterns - commands use *.md not */COMMAND.md
        resolver = FilePatternResolver(temp_dir)
        target_files = []
        for pattern in rule.document_bundle.file_patterns:
            resolved = resolver.resolve(pattern)
            target_files.extend(resolved)

        # No .md files exist yet
        assert len(target_files) == 0

        # Generate prompt anyway (can provide guidance)
        # Note: In real workflow, we'd check if this should error or proceed

    def test_draft_workflow_with_custom_prompt(self, temp_dir):
        """Test workflow with custom draft_instructions."""
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
            draft_instructions=(
                "# Create {bundle_type}\n\n"
                "Generate a new {bundle_type} file at: {file_path}\n\n"
                "**Purpose**: {description}\n\n"
                "**Context**: {context}\n\n"
                "Files to create:\n{file_paths}"
            ),
        )

        # Create skill directory
        skills_dir = temp_dir / ".claude" / "skills" / "testing"
        skills_dir.mkdir(parents=True)

        # Resolve patterns
        resolver = FilePatternResolver(temp_dir)
        target_files = []
        for pattern in rule.document_bundle.file_patterns:
            resolved = resolver.resolve(pattern)
            target_files.extend(resolved)

        # Generate prompt
        generator = PromptGenerator()
        prompt = generator.generate("skill_validation", rule, target_files, temp_dir)

        # Verify custom template was used
        assert "# Create skill" in prompt
        assert "Generate a new skill file at:" in prompt
        assert "**Purpose**: Test skill validation" in prompt
        assert "**Context**: Skills need documentation" in prompt

    def test_draft_workflow_with_real_drift_rules(self, temp_dir):
        """Test workflow using actual .drift_rules.yaml from project."""
        # Create a realistic .drift_rules.yaml
        rules_file = temp_dir / ".drift_rules.yaml"
        rules_content = {
            "skill_structure": {
                "description": "Validate skill file structure and required sections",
                "scope": "project_level",
                "context": "Skills must follow consistent structure for discoverability",
                "requires_project_context": True,
                "document_bundle": {
                    "bundle_type": "skill",
                    "file_patterns": [".claude/skills/*/SKILL.md"],
                    "bundle_strategy": "individual",
                },
                "phases": [
                    {
                        "name": "frontmatter_validation",
                        "type": "core:yaml_frontmatter",
                        "params": {
                            "required_fields": [
                                "title",
                                "description",
                                "version",
                                "author",
                            ],
                        },
                    },
                    {
                        "name": "usage_section",
                        "type": "core:regex_match",
                        "params": {"pattern": "^## Usage"},
                    },
                    {
                        "name": "examples_section",
                        "type": "core:regex_match",
                        "params": {"pattern": "^## Examples"},
                    },
                    {
                        "name": "size_limit",
                        "type": "core:token_count",
                        "params": {"max_tokens": 2000},
                    },
                ],
            },
            "command_brevity": {
                "description": "Ensure commands are concise and focused",
                "scope": "project_level",
                "context": "Commands should be short references, not full documentation",
                "requires_project_context": True,
                "document_bundle": {
                    "bundle_type": "command",
                    "file_patterns": [".claude/commands/*.md"],
                    "bundle_strategy": "individual",
                },
                "phases": [
                    {
                        "name": "token_limit",
                        "type": "core:token_count",
                        "params": {"max_tokens": 1500},
                    },
                ],
            },
        }

        with open(rules_file, "w") as f:
            yaml.dump(rules_content, f)

        # Create directory structures
        (temp_dir / ".claude" / "skills" / "testing").mkdir(parents=True)
        (temp_dir / ".claude" / "skills" / "code-review").mkdir(parents=True)
        (temp_dir / ".claude" / "commands").mkdir(parents=True)

        # Load config
        config = ConfigLoader.load_config(temp_dir, rules_files=[str(rules_file)])

        # Test skill_structure rule
        rule = config.rule_definitions["skill_structure"]
        eligible, error = DraftEligibility.check(rule)
        assert eligible is True

        resolver = FilePatternResolver(temp_dir)
        target_files = []
        for pattern in rule.document_bundle.file_patterns:
            target_files.extend(resolver.resolve(pattern))

        # Wildcard patterns return empty list
        assert len(target_files) == 0

        # Provide specific target file
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        generator = PromptGenerator()
        prompt = generator.generate("skill_structure", rule, target_files, temp_dir)

        # Verify all requirements are extracted
        assert "### YAML Frontmatter" in prompt
        assert "`title`" in prompt
        assert "`author`" in prompt
        assert "### Content Pattern" in prompt
        # Note: When multiple phases of same type exist, only last one is captured
        # due to dict key collision (known limitation of current implementation)
        assert "^## Examples" in prompt  # Last regex_match phase
        assert "### Token Count" in prompt
        assert "2000" in prompt

    def test_draft_workflow_ineligible_rule_fails_early(self, temp_dir):
        """Test that ineligible rules fail at eligibility check."""
        # Conversation-level rule (ineligible)
        rule = RuleDefinition(
            description="Check for incomplete work",
            scope="conversation_level",  # Not project_level
            context="Work should be complete",
            requires_project_context=False,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        # Eligibility check should fail
        eligible, error = DraftEligibility.check(rule)
        assert eligible is False
        assert "conversation_level" in error
        assert "project_level" in error

        # Workflow should not proceed past this point

    def test_draft_workflow_validates_output_format(self, temp_dir):
        """Test that generated prompt has correct markdown format."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="test",
                    type="core:file_exists",
                    params={"file_path": "test.md"},
                )
            ],
        )

        skills_dir = temp_dir / ".claude" / "skills" / "testing"
        skills_dir.mkdir(parents=True)

        # Provide specific target file
        target_files = [skills_dir / "SKILL.md"]

        generator = PromptGenerator()
        prompt = generator.generate("test_rule", rule, target_files, temp_dir)

        # Verify markdown structure
        lines = prompt.split("\n")

        # Should start with h1
        assert lines[0].startswith("# Draft Prompt:")

        # Should have sections
        assert any("## Target Files to Create" in line for line in lines)
        assert any("## Validation Requirements" in line for line in lines)
        assert any("## Instructions" in line for line in lines)

        # Should have code blocks for verification commands
        assert "```bash" in prompt
        assert "drift --rules test_rule --no-llm" in prompt
        assert "drift --rules test_rule" in prompt

    def test_draft_workflow_handles_multiple_patterns(self, temp_dir):
        """Test workflow with rule that has multiple file patterns."""
        rule = RuleDefinition(
            description="Test rule with multiple patterns",
            scope="project_level",
            context="Test",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="mixed",
                file_patterns=[
                    ".claude/skills/*/SKILL.md",
                    ".claude/agents/*/AGENT.md",
                ],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        # Create directory structure
        (temp_dir / ".claude" / "skills" / "testing").mkdir(parents=True)

        resolver = FilePatternResolver(temp_dir)
        target_files = []
        for pattern in rule.document_bundle.file_patterns:
            target_files.extend(resolver.resolve(pattern))

        # Wildcard patterns return empty list
        assert len(target_files) == 0

        # Provide single specific target file
        target_files = [temp_dir / ".claude" / "skills" / "testing" / "SKILL.md"]

        generator = PromptGenerator()
        prompt = generator.generate("test_rule", rule, target_files, temp_dir)

        # Prompt should list the target file
        assert "skills/testing/SKILL.md" in prompt
