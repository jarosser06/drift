"""Markdown output formatter for drift analysis results."""

from typing import Dict, List, Tuple

from drift.cli.output.formatter import OutputFormatter
from drift.core.types import AnalysisResult, CompleteAnalysisResult, Learning


class MarkdownFormatter(OutputFormatter):
    """Formats drift analysis results as Markdown."""

    def get_format_name(self) -> str:
        """Get the name of this format.

        Returns:
            Format name
        """
        return "markdown"

    def format(self, result: CompleteAnalysisResult) -> str:
        """Format the analysis result as Markdown.

        Args:
            result: Complete analysis result to format

        Returns:
            Formatted Markdown string
        """
        lines = []

        # Header
        lines.append("# Drift Analysis Results")
        lines.append("")

        # Summary section
        lines.append("## Summary")
        lines.append(f"- Total conversations: {result.summary.total_conversations}")
        lines.append(f"- Total learnings: {result.summary.total_learnings}")

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

        # If no learnings found, show message and return
        if result.summary.total_learnings == 0:
            lines.append("## No Drift Detected")
            lines.append("")
            lines.append("No drift patterns were found in the analyzed conversations.")
            lines.append("This means the AI agent behavior aligned well with user expectations.")
            lines.append("")
            return "\n".join(lines)

        # Collect all learnings and categorize by scope
        conversation_level_types = {"workflow_bypass", "no_agents_configured"}

        all_turn_level = []
        all_conversation_level = []

        # Collect learnings with their analysis results
        for analysis_result in result.results:
            if not analysis_result.learnings:
                continue

            for learning in analysis_result.learnings:
                if learning.learning_type in conversation_level_types:
                    all_conversation_level.append((analysis_result, learning))
                else:
                    all_turn_level.append((analysis_result, learning))

        # Format turn-level issues grouped by type
        if all_turn_level:
            lines.append("## Turn-Level Issues")
            lines.append("")
            lines.extend(self._format_by_type(all_turn_level))

        # Format conversation-level issues grouped by type
        if all_conversation_level:
            lines.append("## Conversation-Level Issues")
            lines.append("")
            lines.extend(self._format_by_type(all_conversation_level))

        return "\n".join(lines)

    def _format_by_type(
        self, learnings_with_results: List[Tuple[AnalysisResult, Learning]]
    ) -> List[str]:
        """Format learnings grouped by learning type.

        Args:
            learnings_with_results: List of (AnalysisResult, Learning) tuples

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
            # Type header
            lines.append(f"### {learning_type}")
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

                # Observed vs expected behavior
                lines.append(f"**Observed:** {learning.observed_behavior}")
                lines.append(f"**Expected:** {learning.expected_behavior}")

                # Frequency
                lines.append(f"**Frequency:** {learning.frequency.value}")

                # Workflow element (if not unknown)
                if learning.workflow_element.value != "unknown":
                    lines.append(f"**Workflow element:** {learning.workflow_element.value}")

                # Context (if provided)
                if learning.context:
                    lines.append(f"**Context:** {learning.context}")

                lines.append("")

        return lines
