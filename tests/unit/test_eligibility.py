"""Unit tests for draft eligibility checker."""


from drift.config.models import (
    BundleStrategy,
    DocumentBundleConfig,
    PhaseDefinition,
    RuleDefinition,
)
from drift.draft.eligibility import DraftEligibility


class TestDraftEligibility:
    """Tests for DraftEligibility class."""

    def test_eligible_rule_with_all_requirements(self):
        """Test that a rule with all requirements is eligible."""
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

        eligible, error = DraftEligibility.check(rule)
        assert eligible is True
        assert error is None

    def test_ineligible_rule_no_document_bundle(self):
        """Test that a rule without document_bundle is ineligible."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
            document_bundle=None,
            phases=[
                PhaseDefinition(
                    name="test",
                    type="core:file_exists",
                    params={"file_path": "test.md"},
                )
            ],
        )

        eligible, error = DraftEligibility.check(rule)
        assert eligible is False
        assert error == "Rule doesn't have document_bundle configuration"

    def test_ineligible_rule_no_file_patterns(self):
        """Test that a rule without file_patterns is ineligible."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[],  # Empty list
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

        eligible, error = DraftEligibility.check(rule)
        assert eligible is False
        assert error == "Rule doesn't have file_patterns defined"

    def test_ineligible_rule_collection_strategy(self):
        """Test that a rule with collection strategy is ineligible."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.COLLECTION,  # Not INDIVIDUAL
            ),
            phases=[
                PhaseDefinition(
                    name="test",
                    type="core:file_exists",
                    params={"file_path": "test.md"},
                )
            ],
        )

        eligible, error = DraftEligibility.check(rule)
        assert eligible is False
        assert error == (
            "Rule uses 'collection' strategy. " "Draft only supports 'individual' strategy"
        )

    def test_ineligible_rule_conversation_level_scope(self):
        """Test that a rule with conversation_level scope is ineligible."""
        rule = RuleDefinition(
            description="Test rule",
            scope="conversation_level",  # Not project_level
            context="Test context",
            requires_project_context=False,
            document_bundle=DocumentBundleConfig(
                bundle_type="skill",
                file_patterns=[".claude/skills/*/SKILL.md"],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
            phases=[
                PhaseDefinition(
                    name="test",
                    type="prompt",
                    prompt="Test prompt",
                )
            ],
        )

        eligible, error = DraftEligibility.check(rule)
        assert eligible is False
        assert error == (
            "Rule has scope 'conversation_level'. " "Draft only supports 'project_level' rules"
        )

    def test_eligible_rule_with_multiple_file_patterns(self):
        """Test that a rule with multiple file patterns is eligible."""
        rule = RuleDefinition(
            description="Test rule",
            scope="project_level",
            context="Test context",
            requires_project_context=True,
            document_bundle=DocumentBundleConfig(
                bundle_type="mixed",
                file_patterns=[
                    ".claude/skills/*/SKILL.md",
                    ".claude/commands/*/COMMAND.md",
                ],
                bundle_strategy=BundleStrategy.INDIVIDUAL,
            ),
        )

        eligible, error = DraftEligibility.check(rule)
        assert eligible is True
        assert error is None

    def test_eligible_rule_without_phases(self):
        """Test that a rule without phases can still be eligible."""
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
            phases=None,
        )

        eligible, error = DraftEligibility.check(rule)
        assert eligible is True
        assert error is None

    def test_eligible_rule_with_draft_instructions(self):
        """Test that a rule with custom draft_instructions is eligible."""
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
            draft_instructions="Create a skill at {file_path}",
        )

        eligible, error = DraftEligibility.check(rule)
        assert eligible is True
        assert error is None
