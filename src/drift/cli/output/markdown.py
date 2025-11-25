"""Markdown output formatter for drift analysis results."""

import logging
import sys
from typing import Dict, List, Optional, Tuple

from drift.cli.output.formatter import OutputFormatter
from drift.config.models import DriftConfig, SeverityLevel
from drift.core.types import AnalysisResult, CompleteAnalysisResult, Learning

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

    def __init__(self, config: Optional[DriftConfig] = None, detailed: bool = False):
        """Initialize formatter.

        Args:
            config: Optional drift configuration for accessing learning type metadata
            detailed: Whether to include detailed execution information
        """
        self.config = config
        self.detailed = detailed
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

    def _get_severity(self, learning_type: str) -> SeverityLevel:
        """Get severity for a learning type.

        Args:
            learning_type: The learning type name

        Returns:
            Severity level (defaults based on scope if not explicitly set)
        """
        if not self.config or learning_type not in self.config.drift_learning_types:
            # Default to WARNING if no config
            return SeverityLevel.WARNING

        type_config = self.config.drift_learning_types[learning_type]

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

        # Don't color the total learnings count
        lines.append(f"- Total learnings: {result.summary.total_learnings}")

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
                f"{learning_type} ({count})"
                for learning_type, count in result.summary.by_type.items()
            )
            lines.append(f"- By type: {type_counts}")

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

        # If no learnings found, show message
        if result.summary.total_learnings == 0:
            header = self._colorize("## No Drift Detected", self.GREEN)
            lines.append(header)
            lines.append("")
            lines.append("No drift patterns were found in the analyzed data.")
            lines.append("This means the AI agent behavior aligned well with user expectations.")
            lines.append("")

            # Still show execution details if detailed flag is set
            if self.detailed:
                execution_details = result.metadata.get("execution_details", [])
                if execution_details:
                    lines.append("## Test Execution Details")
                    lines.append("")
                    lines.extend(self._format_execution_details(execution_details))

            return "\n".join(lines)

        # Collect all learnings and categorize by severity
        all_failures = []  # Red - fails
        all_warnings = []  # Yellow - warnings
        all_passes = []  # Green - passes (shouldn't happen, but log if it does)

        # Collect learnings with their analysis results
        for analysis_result in result.results:
            if not analysis_result.learnings:
                continue

            for learning in analysis_result.learnings:
                # Determine severity from config
                severity = self._get_severity(learning.learning_type)

                if severity == SeverityLevel.FAIL:
                    all_failures.append((analysis_result, learning))
                elif severity == SeverityLevel.WARNING:
                    all_warnings.append((analysis_result, learning))
                else:  # PASS
                    # This shouldn't happen - log a warning
                    logger.warning(
                        f"Learning type '{learning.learning_type}' has severity=PASS but "
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

        # Add execution details if detailed flag is set
        if self.detailed:
            execution_details = result.metadata.get("execution_details", [])
            if execution_details:
                lines.append("## Test Execution Details")
                lines.append("")
                lines.extend(self._format_execution_details(execution_details))

        return "\n".join(lines)

    def _format_by_type(
        self, learnings_with_results: List[Tuple[AnalysisResult, Learning]], color: str
    ) -> List[str]:
        """Format learnings grouped by learning type.

        Args:
            learnings_with_results: List of (AnalysisResult, Learning) tuples
            color: ANSI color code to use for this scope (RED for project, YELLOW for conversation)

        Returns:
            List of formatted lines
        """
        lines = []

        # Group by learning type
        by_type: Dict[str, List[Tuple[AnalysisResult, Learning]]] = {}
        for analysis_result, learning in learnings_with_results:
            learning_type = learning.learning_type
            if learning_type not in by_type:
                by_type[learning_type] = []
            by_type[learning_type].append((analysis_result, learning))

        # Format each learning type
        for learning_type, items in sorted(by_type.items()):
            # Type header - use provided color for scope
            lines.append(self._colorize(f"### {learning_type}", color))
            lines.append("")

            # Add learning type context/description if available - don't color it
            if self.config and learning_type in self.config.drift_learning_types:
                type_config = self.config.drift_learning_types[learning_type]
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
                lines.append(f"**Turn:** {learning.turn_number}")

                # Observed vs expected behavior - color based on scope
                # Observed behavior uses the scope color (red/yellow)
                # Expected behavior is always green (the goal)
                lines.append(f"**Observed:** {self._colorize(learning.observed_behavior, color)}")
                lines.append(
                    f"**Expected:** {self._colorize(learning.expected_behavior, self.GREEN)}"
                )

                # Frequency
                lines.append(f"**Frequency:** {learning.frequency.value}")

                # Workflow element (if not unknown)
                if learning.workflow_element.value != "unknown":
                    lines.append(f"**Workflow element:** {learning.workflow_element.value}")

                # Context (if provided) - don't color it
                if learning.context:
                    lines.append(f"**Context:** {learning.context}")

                lines.append("")

        return lines

    def _format_execution_details(self, execution_details: List[dict]) -> List[str]:
        """Format execution details for markdown output.

        Args:
            execution_details: List of execution detail dictionaries

        Returns:
            List of formatted lines
        """
        lines = []

        # Group by status
        passed = [d for d in execution_details if d.get("status") == "passed"]
        failed = [d for d in execution_details if d.get("status") == "failed"]
        errored = [d for d in execution_details if d.get("status") == "errored"]

        # Show passed rules
        if passed:
            lines.append(self._colorize("### Passed Rules ✓", self.GREEN))
            lines.append("")
            for detail in passed:
                lines.append(f"- **{detail['rule_name']}**")

                # Show rule description
                rule_desc = detail.get(
                    "rule_description", detail.get("description", "No description")
                )
                lines.append(f"  - Description: {rule_desc}")

                # Show rule context (why it's important)
                rule_context = detail.get("rule_context")
                if rule_context:
                    lines.append(f"  - Context: {rule_context}")

                # Show execution context if available
                exec_context = detail.get("execution_context")
                if exec_context:
                    bundle_type = exec_context.get("bundle_type", "unknown")
                    bundle_id = exec_context.get("bundle_id", "unknown")
                    lines.append(f"  - Bundle: {bundle_type} ({bundle_id})")

                    files = exec_context.get("files", [])
                    if files:
                        files_str = ", ".join(files[:5])  # Show first 5 files
                        if len(files) > 5:
                            files_str += f" ... ({len(files)} total)"
                        lines.append(f"  - Files checked: {files_str}")

                # Show validation details if available
                validation = detail.get("validation_results")
                if validation:
                    rule_type = validation.get("rule_type", "unknown")
                    lines.append(f"  - Validation: {rule_type}")

                    params = validation.get("params", {})
                    if params:
                        # Show key validation parameters
                        for key, value in params.items():
                            lines.append(f"    - {key}: {value}")

            lines.append("")

        # Show failed rules with details
        if failed:
            lines.append(self._colorize("### Failed Rules ✗", self.RED))
            lines.append("")
            for detail in failed:
                lines.append(f"- **{detail['rule_name']}**")

                # Show rule description
                rule_desc = detail.get(
                    "rule_description", detail.get("description", "No description")
                )
                lines.append(f"  - Description: {rule_desc}")

                # Show rule context (why it's important)
                rule_context = detail.get("rule_context")
                if rule_context:
                    lines.append(f"  - Context: {rule_context}")

                # Show execution context if available
                exec_context = detail.get("execution_context")
                if exec_context:
                    bundle_type = exec_context.get("bundle_type", "unknown")
                    bundle_id = exec_context.get("bundle_id", "unknown")
                    lines.append(f"  - Bundle: {bundle_type} ({bundle_id})")

                    files = exec_context.get("files", [])
                    if files:
                        files_str = ", ".join(files[:5])  # Show first 5 files
                        if len(files) > 5:
                            files_str += f" ... ({len(files)} total)"
                        lines.append(f"  - Files checked: {files_str}")
                    else:
                        lines.append("  - Files checked: none")

                # Show validation details if available
                validation = detail.get("validation_results")
                if validation:
                    rule_type = validation.get("rule_type", "unknown")
                    lines.append(f"  - Validation: {rule_type}")

                    params = validation.get("params", {})
                    if params:
                        # Show key validation parameters
                        for key, value in params.items():
                            lines.append(f"    - {key}: {value}")

                # Show phase results if available
                if "phase_results" in detail:
                    for phase in detail["phase_results"]:
                        findings_count = phase.get("findings_count", 0)
                        lines.append(
                            f"  - Phase {phase['phase_number']}: {findings_count} findings"
                        )
            lines.append("")

        # Show errored rules
        if errored:
            lines.append(self._colorize("### Errored Rules ⚠", self.YELLOW))
            lines.append("")
            for detail in errored:
                lines.append(
                    f"- **{detail['rule_name']}**: {detail.get('description', 'No description')}"
                )
            lines.append("")

        return lines
