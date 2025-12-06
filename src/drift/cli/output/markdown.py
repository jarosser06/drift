"""Markdown output formatter for drift analysis results."""

import logging
import sys
from typing import Dict, List, Optional, Tuple

from drift.cli.output.formatter import OutputFormatter
from drift.config.models import DriftConfig, SeverityLevel
from drift.core.types import AnalysisResult, CompleteAnalysisResult, Rule

logger = logging.getLogger(__name__)


class MarkdownFormatter(OutputFormatter):
    """Formats drift analysis results as Markdown."""

    # ANSI color codes
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    def __init__(self, config: Optional[DriftConfig] = None):
        """Initialize formatter.

        Args:
            config: Optional drift configuration for accessing learning type metadata
        """
        self.config = config
        # Check if stdout supports colors
        self.use_colors = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def get_format_name(self) -> str:
        """Get the name of this format.

        Returns:
            Format name
        """
        return "markdown"

    def _colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled.

        Args:
            text: Text to colorize
            color: ANSI color code

        Returns:
            Colorized text if colors enabled, otherwise plain text
        """
        if self.use_colors:
            return f"{color}{text}{self.RESET}"
        return text

    def _get_severity(self, rule_type: str) -> SeverityLevel:
        """Get severity for a learning type.

        Args:
            rule_type: The learning type name

        Returns:
            Severity level (defaults based on scope if not explicitly set)
        """
        if not self.config or rule_type not in self.config.rule_definitions:
            # Default to WARNING if no config
            return SeverityLevel.WARNING

        type_config = self.config.rule_definitions[rule_type]

        # If severity is explicitly set, use it
        if type_config.severity is not None:
            return type_config.severity

        # Otherwise default based on scope
        if type_config.scope == "project_level":
            return SeverityLevel.FAIL
        else:  # conversation_level
            return SeverityLevel.WARNING

    def _get_group_for_rule(self, rule_name: str) -> str:
        """Get the group name for a rule.

        Args:
            rule_name: Name of the rule

        Returns:
            Group name (uses default if rule not found or has no group)
        """
        if self.config and rule_name in self.config.rule_definitions:
            rule_def = self.config.rule_definitions[rule_name]
            return rule_def.group_name or self.config.default_group_name
        return "General"

    def format(self, result: CompleteAnalysisResult) -> str:
        """Format the analysis result as Markdown.

        Args:
            result: Complete analysis result to format

        Returns:
            Formatted Markdown string
        """
        lines = []

        # Header - bold but not colored
        lines.append("# Drift Analysis Results")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append(f"- Total conversations: {result.summary.total_conversations}")

        # Show total rules from config (count of rule definitions)
        if result.summary.rules_checked is not None:
            lines.append(f"- Total rules: {len(result.summary.rules_checked)}")

        # Total violations found
        lines.append(f"- Total violations: {result.summary.total_rule_violations}")

        # Total checks - show even if 0
        if result.summary.rules_checked is not None:
            lines.append(f"- Total checks: {result.summary.total_checks}")

        # Checks breakdown - show even if 0
        if result.summary.rules_checked is not None:
            # Always show counts, even if 0
            passed_count = result.summary.checks_passed
            count_str = self._colorize(
                str(passed_count), self.GREEN if passed_count > 0 else self.RESET
            )
            lines.append(f"- Checks passed: {count_str}")

            failed_count = result.summary.checks_failed
            if failed_count > 0:
                count_str = self._colorize(str(failed_count), self.RED)
                lines.append(f"- Checks failed: {count_str}")

            errored_count = result.summary.checks_errored
            if errored_count > 0:
                count_str = self._colorize(str(errored_count), self.YELLOW)
                lines.append(f"- Checks errored: {count_str}")

        # By group
        if result.summary.by_group:
            group_counts = ", ".join(
                f"{group} ({count})" for group, count in result.summary.by_group.items()
            )
            lines.append(f"- By group: {group_counts}")

        # By type
        if result.summary.by_type:
            type_counts = ", ".join(
                f"{rule_type} ({count})" for rule_type, count in result.summary.by_type.items()
            )
            lines.append(f"- By rule: {type_counts}")

        # By agent tool
        if result.summary.by_agent:
            agent_counts = ", ".join(
                f"{agent} ({count})" for agent, count in result.summary.by_agent.items()
            )
            lines.append(f"- By agent tool: {agent_counts}")

        lines.append("")

        # Show checks that passed
        if result.summary.rules_passed:
            header = self._colorize("## Checks Passed ✓", self.GREEN)
            lines.append(header)
            lines.append("")

            # Group passed rules by group name
            passed_by_group: Dict[str, List[str]] = {}
            for rule_name in result.summary.rules_passed:
                group_name = self._get_group_for_rule(rule_name)
                if group_name not in passed_by_group:
                    passed_by_group[group_name] = []
                passed_by_group[group_name].append(rule_name)

            # Display by group
            for group_name in sorted(passed_by_group.keys()):
                lines.append(f"### {group_name}")
                lines.append("")
                for rule in sorted(passed_by_group[group_name]):
                    lines.append(f"- **{rule}**: No issues found")
                lines.append("")

        # Show checks that errored
        if result.summary.rules_errored:
            header = self._colorize("## Checks Errored ⚠", self.YELLOW)
            lines.append(header)
            lines.append("")
            for rule in sorted(result.summary.rules_errored):
                error_msg = result.summary.rule_errors.get(rule, "Unknown error")
                lines.append(f"- **{rule}**: {error_msg}")
            lines.append("")

        # If no violations found, show message
        if result.summary.total_rule_violations == 0:
            header = self._colorize("## No Violations Detected", self.GREEN)
            lines.append(header)
            lines.append("")
            lines.append("No drift patterns were found in the analyzed data.")
            lines.append("")

            return "\n".join(lines)

        # Collect all rules and categorize by severity
        all_failures = []  # Red - fails
        all_warnings = []  # Yellow - warnings
        all_passes = []  # Green - passes (shouldn't happen, but log if it does)

        # Collect rules with their analysis results
        for analysis_result in result.results:
            if not analysis_result.rules:
                continue

            for learning in analysis_result.rules:
                # Determine severity from config
                severity = self._get_severity(learning.rule_type)

                if severity == SeverityLevel.FAIL:
                    all_failures.append((analysis_result, learning))
                elif severity == SeverityLevel.WARNING:
                    all_warnings.append((analysis_result, learning))
                else:  # PASS
                    # This shouldn't happen - log a warning
                    logger.warning(
                        f"Rule type '{learning.rule_type}' has severity=PASS but "
                        f"produced a learning. This indicates a misconfiguration. "
                        f"Session: {analysis_result.session_id}, Turn: {learning.turn_number}"
                    )
                    all_passes.append((analysis_result, learning))

        # Format failures (red)
        if all_failures:
            lines.append(self._colorize("## Failures", self.RED))
            lines.append("")
            lines.extend(self._format_by_type(all_failures, color=self.RED))

        # Format warnings (yellow)
        if all_warnings:
            lines.append(self._colorize("## Warnings", self.YELLOW))
            lines.append("")
            lines.extend(self._format_by_type(all_warnings, color=self.YELLOW))

        # Format passes (green) - should be rare/never
        if all_passes:
            lines.append(self._colorize("## Unexpected Passes", self.GREEN))
            lines.append("")
            lines.extend(self._format_by_type(all_passes, color=self.GREEN))

        return "\n".join(lines)

    def _format_by_type(
        self, learnings_with_results: List[Tuple[AnalysisResult, Rule]], color: str
    ) -> List[str]:
        """Format rules grouped by group name and then by rule type.

        Args:
            learnings_with_results: List of (AnalysisResult, Rule) tuples
            color: ANSI color code to use for this scope (RED for project, YELLOW for conversation)

        Returns:
            List of formatted lines
        """
        lines = []

        # Group by group name, then by rule type
        by_group: Dict[str, Dict[str, List[Tuple[AnalysisResult, Rule]]]] = {}
        for analysis_result, learning in learnings_with_results:
            group_name = learning.group_name or "General"
            rule_type = learning.rule_type

            if group_name not in by_group:
                by_group[group_name] = {}
            if rule_type not in by_group[group_name]:
                by_group[group_name][rule_type] = []

            by_group[group_name][rule_type].append((analysis_result, learning))

        # Format each group
        for group_name, by_type in sorted(by_group.items()):
            # Group header (e.g., "### Workflow Check")
            lines.append(self._colorize(f"### {group_name}", color))
            lines.append("")

            # Format each rule type within the group
            for rule_type, items in sorted(by_type.items()):
                # Type sub-header (e.g., "#### skill_completeness")
                lines.append(self._colorize(f"#### {rule_type}", color))
                lines.append("")

                # Add learning type context/description if available - don't color it
                if self.config and rule_type in self.config.rule_definitions:
                    type_config = self.config.rule_definitions[rule_type]
                    lines.append(f"*{type_config.context}*")
                    lines.append("")

                # Format each violation of this type
                for analysis_result, learning in items:
                    # Session info
                    session_info = f"**Session:** {analysis_result.session_id}"
                    if analysis_result.project_path:
                        project_name = analysis_result.project_path.split("/")[-1]
                        session_info += f" ({project_name})"
                    lines.append(session_info)

                    lines.append(f"**Agent Tool:** {analysis_result.agent_tool}")

                    # Show Turn or Source based on learning source type
                    if hasattr(learning, "source_type") and learning.source_type == "document":
                        # Show affected files for document rules
                        if hasattr(learning, "affected_files") and learning.affected_files:
                            if len(learning.affected_files) == 1:
                                # Single file - use singular "File:"
                                lines.append(f"**File:** {learning.affected_files[0]}")
                            else:
                                # Multiple files - show each on separate line for readability
                                lines.append("**Files:**")
                                for file_path in learning.affected_files:
                                    lines.append(f"  - {file_path}")
                        lines.append("**Source:** document_analysis")
                    elif (
                        hasattr(learning, "source_type")
                        and learning.source_type == "resource_missing"
                    ):
                        lines.append("**Source:** resource_validation")
                    else:
                        # Conversation-based learning - show turn number
                        if learning.turn_number > 0:
                            lines.append(f"**Turn:** {learning.turn_number}")
                        # else: turn_number=0 indicates not turn-specific, don't show it

                    # Observed vs expected behavior - color based on scope
                    # Observed behavior uses the scope color (red/yellow)
                    # Expected behavior is always green (the goal)
                    observed_text = self._colorize(learning.observed_behavior, color)
                    lines.append(f"**Observed:** {observed_text}")
                    lines.append(
                        f"**Expected:** {self._colorize(learning.expected_behavior, self.GREEN)}"
                    )

                    # Context (if provided) - don't color it
                    if learning.context:
                        lines.append(f"**Context:** {learning.context}")

                    lines.append("")

        return lines
