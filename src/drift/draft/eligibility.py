"""Draft eligibility checker for Drift rules.

Determines whether a rule supports draft functionality based on its
configuration (document_bundle, bundle_strategy, scope).
"""

from typing import Optional, Tuple

from drift.config.models import BundleStrategy, RuleDefinition


class DraftEligibility:
    """Determines if a rule supports draft functionality."""

    @staticmethod
    def check(rule: RuleDefinition) -> Tuple[bool, Optional[str]]:
        """Check if rule is eligible for draft.

        A rule is eligible for draft if it:
        - Has a document_bundle configuration
        - Has file_patterns defined in document_bundle
        - Uses bundle_strategy: individual (not collection)
        - Has scope: project_level

        Parameters
        ----------
        rule : RuleDefinition
            The rule to check for draft eligibility.

        Returns
        -------
        Tuple[bool, Optional[str]]
            A tuple of (eligible, error_message). If eligible=True,
            error_message=None. If eligible=False, error_message contains
            the reason for ineligibility.

        Examples
        --------
        >>> rule = RuleDefinition(...)
        >>> eligible, error = DraftEligibility.check(rule)
        >>> if not eligible:
        ...     print(f"Rule not eligible: {error}")
        """
        # Must have document_bundle
        if not rule.document_bundle:
            return False, "Rule doesn't have document_bundle configuration"

        # Must have file_patterns
        if not rule.document_bundle.file_patterns:
            return False, "Rule doesn't have file_patterns defined"

        # Must use individual strategy
        if rule.document_bundle.bundle_strategy != BundleStrategy.INDIVIDUAL:
            return (
                False,
                "Rule uses 'collection' strategy. Draft only supports 'individual' strategy",
            )

        # Must be project_level scope
        if rule.scope != "project_level":
            return (
                False,
                f"Rule has scope '{rule.scope}'. Draft only supports 'project_level' rules",
            )

        return True, None
