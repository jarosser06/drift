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

        # Don't color the total rules count
        lines.append(f"- Total rules: {result.summary.total_rule_violations}")

        # Rules checked - show even if 0
        if result.summary.rules_checked is not None:
            lines.append(f"- Rules checked: {len(result.summary.rules_checked)}")
            # Always show counts, even if 0
            passed_count = len(result.summary.rules_passed) if result.summary.rules_passed else 0
            count_str = self._colorize(
                str(passed_count), self.GREEN if passed_count > 0 else self.RESET
            )
            lines.append(f"- Rules passed: {count_str}")

            warned_count = len(result.summary.rules_warned) if result.summary.rules_warned else 0
            if warned_count > 0:
                count_str = self._colorize(str(warned_count), self.YELLOW)
                lines.append(f"- Rules warned: {count_str}")

            failed_count = len(result.summary.rules_failed) if result.summary.rules_failed else 0
            if failed_count > 0:
                count_str = self._colorize(str(failed_count), self.RED)
                lines.append(f"- Rules failed: {count_str}")

            errored_count = len(result.summary.rules_errored) if result.summary.rules_errored else 0
            if errored_count > 0:
                count_str = self._colorize(str(errored_count), self.YELLOW)
                lines.append(f"- Rules errored: {count_str}")

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

        # Show rules that passed
        if result.summary.rules_passed:
            header = self._colorize("## Rules Passed ✓", self.GREEN)
            lines.append(header)
            lines.append("")
            for rule in sorted(result.summary.rules_passed):
                lines.append(f"- **{rule}**: No issues found")
            lines.append("")

        # Show rules that errored
        if result.summary.rules_errored:
            header = self._colorize("## Rules Errored ⚠", self.YELLOW)
            lines.append(header)
            lines.append("")
            for rule in sorted(result.summary.rules_errored):
                error_msg = result.summary.rule_errors.get(rule, "Unknown error")
                lines.append(f"- **{rule}**: {error_msg}")
            lines.append("")

        # If no rules found, show message
        if result.summary.total_rule_violations == 0:
            header = self._colorize("## No Rule Violations Detected", self.GREEN)
            lines.append(header)
            lines.append("")
            lines.append("No drift patterns were found in the analyzed data.")
            lines.append("This means the AI agent behavior aligned well with user expectations.")
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
        """Format rules grouped by learning type.

        Args:
            learnings_with_results: List of (AnalysisResult, Rule) tuples
            color: ANSI color code to use for this scope (RED for project, YELLOW for conversation)

        Returns:
            List of formatted lines
        """
        lines = []

        # Group by learning type
        by_type: Dict[str, List[Tuple[AnalysisResult, Rule]]] = {}
        for analysis_result, learning in learnings_with_results:
            rule_type = learning.rule_type
            if rule_type not in by_type:
                by_type[rule_type] = []
            by_type[rule_type].append((analysis_result, learning))

        # Format each learning type
        for rule_type, items in sorted(by_type.items()):
            # Type header - use provided color for scope
            lines.append(self._colorize(f"### {rule_type}", color))
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
                    hasattr(learning, "source_type") and learning.source_type == "resource_missing"
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
                lines.append(f"**Observed:** {self._colorize(learning.observed_behavior, color)}")
                lines.append(
                    f"**Expected:** {self._colorize(learning.expected_behavior, self.GREEN)}"
                )

                # Context (if provided) - don't color it
                if learning.context:
                    lines.append(f"**Context:** {learning.context}")

                lines.append("")

        return lines
