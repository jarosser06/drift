"""JSON output formatter for drift analysis results."""

import json
from typing import Any, Dict

from drift.cli.output.formatter import OutputFormatter
from drift.core.types import CompleteAnalysisResult


class JsonFormatter(OutputFormatter):
    """Formats drift analysis results as JSON."""

    def get_format_name(self) -> str:
        """Get the name of this format.

        Returns:
            Format name
        """
        return "json"

    def format(self, result: CompleteAnalysisResult) -> str:
        """Format the analysis result as JSON.

        Args:
            result: Complete analysis result to format

        Returns:
            Formatted JSON string
        """
        # Build output structure
        output = {
            "metadata": {
                "generated_at": result.metadata.get("generated_at"),
                "session_id": result.metadata.get("session_id"),
                "total_conversations": result.summary.total_conversations,
                "total_rule_violations": result.summary.total_rule_violations,
                "config_used": result.metadata.get("config_used", {}),
                "execution_details": result.metadata.get("execution_details", []),
            },
            "summary": {
                "conversations_analyzed": result.summary.total_conversations,
                "total_rule_violations": result.summary.total_rule_violations,
                "conversations_with_drift": result.summary.conversations_with_drift,
                "conversations_without_drift": result.summary.conversations_without_drift,
                "by_group": result.summary.by_group,
                "by_type": result.summary.by_type,
                "by_agent": result.summary.by_agent,
            },
            "results": [],
        }

        # Add conversation results
        for analysis_result in result.results:
            conversation_data: Dict[str, Any] = {
                "session_id": analysis_result.session_id,
                "agent_tool": analysis_result.agent_tool,
                "conversation_file": analysis_result.conversation_file,
                "project_path": analysis_result.project_path,
                "analysis_timestamp": (
                    analysis_result.analysis_timestamp.isoformat()
                    if analysis_result.analysis_timestamp
                    else None
                ),
                "rules": [],
            }

            # Add rules
            for learning in analysis_result.rules:
                learning_data: Dict[str, Any] = {
                    "turn_number": learning.turn_number,
                    "turn_uuid": learning.turn_uuid,
                    "agent_tool": learning.agent_tool,
                    "conversation_file": learning.conversation_file,
                    "observed_behavior": learning.observed_behavior,
                    "expected_behavior": learning.expected_behavior,
                    "rule_type": learning.rule_type,
                    "workflow_element": learning.workflow_element.value,
                    "turns_to_resolve": learning.turns_to_resolve,
                    "turns_involved": learning.turns_involved,
                    "context": learning.context,
                }

                # Add optional document-specific fields
                if hasattr(learning, "affected_files") and learning.affected_files:
                    learning_data["affected_files"] = learning.affected_files
                if hasattr(learning, "bundle_id") and learning.bundle_id:
                    learning_data["bundle_id"] = learning.bundle_id

                learnings_list = conversation_data.get("rules")
                if isinstance(learnings_list, list):
                    learnings_list.append(learning_data)

            results_list = output.get("results")
            if isinstance(results_list, list):
                results_list.append(conversation_data)

        # Convert to JSON with nice formatting
        return json.dumps(output, indent=2, sort_keys=False, ensure_ascii=False)
