"""Main analysis orchestration for drift detection."""

import hashlib
import json
import logging
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from drift.agent_tools.base import AgentLoader
from drift.agent_tools.claude_code import ClaudeCodeLoader
from drift.config.loader import ConfigLoader
from drift.config.models import (
    BundleStrategy,
    DriftConfig,
    ProviderType,
    SeverityLevel,
    ValidationRule,
    ValidationType,
)
from drift.core.types import (
    AnalysisResult,
    AnalysisSummary,
    CompleteAnalysisResult,
    Conversation,
    DocumentBundle,
    DocumentLearning,
    FrequencyType,
    Learning,
    PhaseAnalysisResult,
    ResourceRequest,
    ResourceResponse,
    WorkflowElement,
)
from drift.documents.loader import DocumentLoader
from drift.providers.base import Provider
from drift.providers.bedrock import BedrockProvider
from drift.utils.temp import TempManager
from drift.validation.validators import ValidatorRegistry

logger = logging.getLogger(__name__)

# Centralized list of programmatic phase types
PROGRAMMATIC_PHASE_TYPES = [
    "file_exists",
    "file_not_exists",
    "regex_match",
    "regex_not_match",
    "file_count",
    "file_size",
    "cross_file_reference",
    "list_match",
    "list_regex_match",
]


def _has_programmatic_phases(phases: List[Any]) -> bool:
    """Check if any phases are programmatic (non-LLM) types.

    Args:
        phases: List of phase definitions

    Returns:
        True if any phase has a programmatic type
    """
    if not phases:
        return False

    return any(getattr(p, "type", "prompt") in PROGRAMMATIC_PHASE_TYPES for p in phases)


class DriftAnalyzer:
    """Main analyzer for detecting drift in AI agent conversations."""

    def __init__(self, config: Optional[DriftConfig] = None, project_path: Optional[Path] = None):
        """Initialize the drift analyzer.

        Args:
            config: Optional configuration (will load from files if not provided)
            project_path: Optional project path for project-specific config
        """
        self.config = config or ConfigLoader.load_config(project_path)
        self.project_path = project_path
        self.providers: Dict[str, Provider] = {}
        self.agent_loaders: Dict[str, AgentLoader] = {}
        self.temp_manager = TempManager(self.config.temp_dir)

        self._initialize_providers()
        self._initialize_agent_loaders()

    def _initialize_providers(self) -> None:
        """Initialize LLM providers based on config."""
        for model_name, model_config in self.config.models.items():
            # Get the provider config
            provider_name = model_config.provider
            if provider_name not in self.config.providers:
                raise ValueError(
                    f"Model '{model_name}' references unknown provider '{provider_name}'"
                )

            provider_config = self.config.providers[provider_name]

            # Create provider instance based on provider type
            if provider_config.provider == ProviderType.BEDROCK:
                self.providers[model_name] = BedrockProvider(provider_config, model_config)
            # Future: Add OpenAI and other providers
            # elif provider_config.provider == ProviderType.OPENAI:
            #     self.providers[model_name] = OpenAIProvider(provider_config, model_config)

    def _initialize_agent_loaders(self) -> None:
        """Initialize agent loaders based on config."""
        for tool_name, tool_config in self.config.get_enabled_agent_tools().items():
            if tool_name == "claude-code":
                self.agent_loaders[tool_name] = ClaudeCodeLoader(tool_config.conversation_path)
            # Future: Add other agent loaders
            # elif tool_name == "cursor":
            #     self.agent_loaders[tool_name] = CursorLoader(tool_config.conversation_path)

    def analyze(
        self,
        agent_tool: Optional[str] = None,
        learning_types: Optional[List[str]] = None,
        model_override: Optional[str] = None,
    ) -> CompleteAnalysisResult:
        """Run drift analysis on conversations.

        Args:
            agent_tool: Optional specific agent tool to analyze
            learning_types: Optional list of specific learning types to check
            model_override: Optional model to use (overrides all config settings)

        Returns:
            Complete analysis results
        """
        # Create analysis session
        session_id = hashlib.md5(str(datetime.now()).encode()).hexdigest()[:8]
        self.temp_manager.create_analysis_dir(session_id)

        try:
            # Determine which agent tools to analyze
            tools_to_analyze = (
                {agent_tool: self.agent_loaders[agent_tool]} if agent_tool else self.agent_loaders
            )

            # Determine which learning types to check
            all_types = (
                {lt: self.config.drift_learning_types[lt] for lt in learning_types}
                if learning_types is not None
                else self.config.drift_learning_types
            )

            # Filter to only conversation-based rules (turn_level or conversation_level scopes)
            # Document and project level rules should be run via analyze_documents()
            types_to_check = {}
            for name, config in all_types.items():
                scope = getattr(config, "scope", "turn_level")
                if scope in ("turn_level", "conversation_level"):
                    types_to_check[name] = config

            # If no conversation-based rules, return empty result
            if not types_to_check:
                # Show which rules were filtered out
                filtered_rules = [
                    name
                    for name, config in all_types.items()
                    if getattr(config, "scope", "turn_level") in ("document_level", "project_level")
                ]
                if filtered_rules:
                    logger.warning(
                        "No conversation-based learning types configured. "
                        f"Skipped document/project-level rules (use --scope project): "
                        f"{', '.join(filtered_rules)}"
                    )
                return CompleteAnalysisResult(
                    metadata={
                        "generated_at": datetime.now().isoformat(),
                        "session_id": session_id,
                        "message": "No conversation-based learning types configured",
                        "skipped_rules": filtered_rules,
                        "execution_details": [],
                    },
                    summary=AnalysisSummary(
                        total_conversations=0,
                        total_learnings=0,
                        conversations_with_drift=0,
                        conversations_without_drift=0,
                        rules_checked=[],
                        rules_passed=[],
                        rules_warned=[],
                        rules_failed=[],
                        rules_errored=[],
                    ),
                    results=[],
                )

            # Check provider availability before starting analysis
            # Determine which models will be needed
            models_needed = set()
            for type_name in types_to_check.keys():
                type_config = self.config.drift_learning_types.get(type_name)
                type_model = getattr(type_config, "model", None) if type_config else None
                model_name = (
                    model_override
                    or type_model
                    or self.config.get_model_for_learning_type(type_name)
                )
                models_needed.add(model_name)

            # Check all required providers are available
            for model_name in models_needed:
                provider = self.providers.get(model_name)
                if not provider:
                    raise ValueError(f"Model '{model_name}' not found in configured providers")
                if not provider.is_available():
                    raise RuntimeError(
                        f"Provider for model '{model_name}' is not available. "
                        "Check credentials and configuration."
                    )

            # Load conversations from all selected agent tools
            all_conversations: List[Conversation] = []
            for tool_name, loader in tools_to_analyze.items():
                try:
                    conversations = loader.load_conversations(
                        mode=self.config.conversations.mode.value,
                        days=self.config.conversations.days,
                        project_path=self.project_path,
                    )
                    all_conversations.extend(conversations)
                except FileNotFoundError as e:
                    # Don't fail if conversations aren't found - just skip this agent tool
                    logger.warning(f"No conversations found for {tool_name}: {e}")
                    logger.info("Skipping conversation-based analysis for this tool.")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to load conversations from {tool_name}: {e}")
                    continue

            # If no conversations were loaded but we have rules to check, return empty result
            if not all_conversations:
                # List which rules were skipped
                skipped_rules = list(types_to_check.keys())
                logger.warning(
                    "No conversations available for analysis. "
                    f"Skipped conversation-based rules: {', '.join(skipped_rules)}"
                )
                return CompleteAnalysisResult(
                    metadata={
                        "generated_at": datetime.now().isoformat(),
                        "session_id": session_id,
                        "message": "No conversations available for analysis",
                        "skipped_rules": skipped_rules,
                        "execution_details": [],
                    },
                    summary=AnalysisSummary(
                        total_conversations=0,
                        total_learnings=0,
                        conversations_with_drift=0,
                        conversations_without_drift=0,
                        rules_checked=[],
                        rules_passed=[],
                        rules_warned=[],
                        rules_failed=[],
                        rules_errored=[],
                    ),
                    results=[],
                )

            # Analyze each conversation
            results: List[AnalysisResult] = []
            all_execution_details: List[dict] = []
            logger.info(f"Analyzing {len(all_conversations)} conversation(s)")
            for conversation in all_conversations:
                try:
                    logger.info(f"Analyzing conversation {conversation.session_id}")
                    result, exec_details = self._analyze_conversation(
                        conversation,
                        types_to_check,
                        model_override,
                    )
                    results.append(result)
                    all_execution_details.extend(exec_details)
                except Exception as e:
                    # Re-raise critical errors (API errors, config issues, etc)
                    error_msg = str(e)
                    if any(
                        keyword in error_msg
                        for keyword in [
                            "Bedrock API error",
                            "API error",
                            "provider is not available",
                            "client is not available",
                            "ValidationException",
                            "ThrottlingException",
                            "ServiceException",
                        ]
                    ):
                        raise
                    # Log non-critical errors with traceback
                    error_details = traceback.format_exc()
                    logger.warning(f"Failed to analyze conversation {conversation.session_id}: {e}")
                    logger.debug(f"Full traceback:\n{error_details}")
                    continue

            # Generate summary
            summary = self._generate_summary(results, types_to_check)

            # Save metadata
            self.temp_manager.save_metadata(
                {
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "conversations_analyzed": len(all_conversations),
                    "agent_tools": list(tools_to_analyze.keys()),
                    "learning_types": list(types_to_check.keys()),
                }
            )

            return CompleteAnalysisResult(
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "session_id": session_id,
                    "config_used": {
                        "default_model": self.config.default_model,
                        "conversation_mode": self.config.conversations.mode.value,
                    },
                    "execution_details": all_execution_details,
                },
                summary=summary,
                results=results,
            )

        finally:
            # Clean up temp directory on success
            # On error, preserve for debugging
            pass

    def _analyze_conversation(
        self,
        conversation: Conversation,
        learning_types: Dict[str, Any],
        model_override: Optional[str],
    ) -> tuple[AnalysisResult, List[dict]]:
        """Analyze a single conversation using multi-pass approach.

        Args:
            conversation: Conversation to analyze
            learning_types: Learning types to check
            model_override: Optional model override

        Returns:
            Tuple of (AnalysisResult, execution_details)
        """
        all_learnings: List[Learning] = []
        conversation_level_learnings: Dict[str, Learning] = {}
        skipped_due_to_client: List[str] = []
        rule_errors: Dict[str, str] = {}
        execution_details: List[dict] = []  # Track all rule executions

        # Perform one pass per learning type
        for type_name, type_config in learning_types.items():
            # Client filtering: skip if rule doesn't support this agent_tool
            supported_clients = getattr(type_config, "supported_clients", None)
            if supported_clients is not None and conversation.agent_tool not in supported_clients:
                skipped_due_to_client.append(type_name)
                continue

            learnings, error, phase_results = self._run_analysis_pass(
                conversation,
                type_name,
                type_config,
                model_override,
            )

            # Track errors
            if error:
                rule_errors[type_name] = error

            # Build execution detail entry
            exec_detail = {
                "rule_name": type_name,
                "description": type_config.description,
                "status": "errored" if error else ("failed" if learnings else "passed"),
            }

            # Add phase_results if this was multi-phase
            if phase_results:
                exec_detail["phase_results"] = [
                    {
                        "phase_number": pr.phase_number,
                        "final_determination": pr.final_determination,
                        "findings_count": len(pr.findings),
                    }
                    for pr in phase_results
                ]

                # Add resources_consulted if any learnings have them
                if learnings:
                    resources = learnings[0].resources_consulted
                    if resources:
                        exec_detail["resources_consulted"] = resources

            execution_details.append(exec_detail)

            # Scope-based limiting for conversation-level rules
            scope = getattr(type_config, "scope", "turn_level")
            if scope == "conversation_level":
                # Only keep first learning for conversation-level types
                if learnings and type_name not in conversation_level_learnings:
                    conversation_level_learnings[type_name] = learnings[0]
            else:
                # Turn-level learnings: keep all
                all_learnings.extend(learnings)

            # Save intermediate results
            self.temp_manager.save_pass_result(
                conversation.session_id,
                type_name,
                learnings,
            )

        # Add conversation-level learnings (max 1 per type)
        all_learnings.extend(conversation_level_learnings.values())

        # Log skipped rules if any
        if skipped_due_to_client:
            logger.info(
                f"Skipped {len(skipped_due_to_client)} rule(s) for {conversation.agent_tool} "
                f"(not supported by client): {', '.join(skipped_due_to_client)}"
            )

        return (
            AnalysisResult(
                session_id=conversation.session_id,
                agent_tool=conversation.agent_tool,
                conversation_file=conversation.file_path,
                project_path=conversation.project_path,
                learnings=all_learnings,
                analysis_timestamp=datetime.now(),
                error=None,
                rule_errors=rule_errors,
            ),
            execution_details,
        )

    def _run_analysis_pass(
        self,
        conversation: Conversation,
        learning_type: str,
        type_config: Any,
        model_override: Optional[str],
    ) -> tuple[List[Learning], Optional[str], Optional[List[PhaseAnalysisResult]]]:
        """Run a single analysis pass for one learning type.

        Args:
            conversation: Conversation to analyze
            learning_type: Name of the learning type
            type_config: Configuration for this learning type
            model_override: Optional model override

        Returns:
            Tuple of (learnings, error_message, phase_results).
            error_message is None if successful.
            phase_results is None for single-phase analysis,
            List[PhaseAnalysisResult] for multi-phase.
        """
        # Check if multi-phase (>1 phase) or single-phase (1 phase)
        phases = getattr(type_config, "phases", [])
        if len(phases) > 1:
            # Route to multi-phase analysis - returns phase_results
            return self._run_multi_phase_analysis(
                conversation, learning_type, type_config, model_override
            )

        # Determine which model to use (from phase)
        phase_model = phases[0].model if phases else None
        model_name = (
            model_override or phase_model or self.config.get_model_for_learning_type(learning_type)
        )

        provider = self.providers.get(model_name)
        if not provider:
            raise ValueError(f"Model '{model_name}' not found in configured providers")

        if not provider.is_available():
            raise RuntimeError(
                f"Provider for model '{model_name}' is not available. "
                "Check credentials and configuration."
            )

        # Build prompt for this learning type
        prompt = self._build_analysis_prompt(conversation, learning_type, type_config)

        # Generate analysis
        logger.debug(f"Sending prompt to {model_name}:\n{prompt}")
        response = provider.generate(prompt)
        logger.debug(f"Raw response from {model_name}:\n{response}")

        # Parse response to extract learnings
        learnings = self._parse_analysis_response(
            response,
            conversation,
            learning_type,
        )

        # Single-phase analysis - no phase_results to return
        return learnings, None, None

    def _build_analysis_prompt(
        self,
        conversation: Conversation,
        learning_type: str,
        type_config: Any,
    ) -> str:
        """Build the prompt for analyzing a conversation.

        Args:
            conversation: Conversation to analyze
            learning_type: Name of the learning type
            type_config: Configuration for this learning type

        Returns:
            Formatted prompt string
        """
        # Format conversation for analysis
        conversation_text = self._format_conversation(conversation)

        description = getattr(type_config, "description", "")
        phases = getattr(type_config, "phases", [])
        detection_prompt = phases[0].prompt if phases else ""
        requires_project_context = getattr(type_config, "requires_project_context", False)

        # Build project context section if needed
        project_context_section = ""
        if requires_project_context and conversation.project_context:
            project_context_section = f"""
**Project Customizations for {conversation.agent_tool}:**
{conversation.project_context}

"""

        prompt = f"""You are analyzing an AI agent conversation to identify drift patterns.

**Drift Learning Type:** {learning_type}
**Description:** {description}

{project_context_section}**Detection Instructions:**
{detection_prompt}

**Conversation to Analyze:**
{conversation_text}

**Task:**
Analyze the above conversation and identify any instances of the "{learning_type}" drift pattern.

IMPORTANT: Only report drift that was NOT resolved in the conversation. If the user had to correct
the AI or ask for missing work, but it remained unresolved, that's drift. If the issue was fully
addressed and resolved within the conversation, do NOT report it.

For each unresolved instance found, extract:
1. Turn number where drift occurred
2. What was observed (the actual behavior - could be AI action or user
   behavior depending on the drift type)
3. What should have happened instead (the expected/optimal behavior)
4. Brief explanation of the drift

Return your analysis as a JSON array of objects with this structure:
[
  {{
    "turn_number": <int>,
    "observed_behavior": "<what actually happened>",
    "expected_behavior": "<what should have happened>",
    "context": "<brief explanation>"
  }}
]

If no unresolved instances of this drift pattern are found, return an empty array: []

IMPORTANT: Return ONLY valid JSON, no additional text or explanation."""

        return prompt

    @staticmethod
    def _format_conversation(conversation: Conversation) -> str:
        """Format conversation for inclusion in prompt.

        Args:
            conversation: Conversation to format

        Returns:
            Formatted conversation text
        """
        lines = []
        for turn in conversation.turns:
            lines.append(f"[Turn {turn.number}]")
            lines.append(f"User: {turn.user_message}")
            lines.append(f"AI: {turn.ai_message}")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _parse_analysis_response(
        response: str,
        conversation: Conversation,
        learning_type: str,
    ) -> List[Learning]:
        """Parse LLM response to extract learnings.

        Args:
            response: Raw LLM response
            conversation: Conversation that was analyzed
            learning_type: Type of learning

        Returns:
            List of Learning objects
        """
        import json
        import re

        # Extract JSON from response (in case there's extra text)
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if not json_match:
            # No learnings found
            return []

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis response as JSON: {response[:200]}")
            return []

        learnings = []
        for item in data:
            learning = Learning(
                turn_number=item.get("turn_number", 0),
                turn_uuid=None,  # Can be populated if we track UUIDs
                agent_tool=conversation.agent_tool,
                conversation_file=conversation.file_path,
                observed_behavior=item.get("observed_behavior", ""),
                expected_behavior=item.get("expected_behavior", ""),
                learning_type=learning_type,
                frequency=FrequencyType.ONE_TIME,
                workflow_element=WorkflowElement.UNKNOWN,
                turns_to_resolve=1,
                context=item.get("context", ""),
                resources_consulted=[],
                phases_count=1,
            )
            learnings.append(learning)

        return learnings

    def _generate_summary(
        self,
        results: List[AnalysisResult],
        types_checked: Optional[Dict[str, Any]] = None,
    ) -> AnalysisSummary:
        """Generate summary statistics from analysis results.

        Args:
            results: List of analysis results
            types_checked: Dict of learning types that were checked

        Returns:
            Analysis summary
        """
        summary = AnalysisSummary(
            total_conversations=len(results),
            total_learnings=0,
            conversations_with_drift=0,
            conversations_without_drift=0,
        )

        # Count learnings by type and agent
        by_type: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}
        by_frequency: Dict[str, int] = {}
        all_rule_errors: Dict[str, str] = {}

        for result in results:
            if result.learnings:
                summary.conversations_with_drift += 1
            else:
                summary.conversations_without_drift += 1

            for learning in result.learnings:
                summary.total_learnings += 1

                # By type
                by_type[learning.learning_type] = by_type.get(learning.learning_type, 0) + 1

                # By agent
                by_agent[learning.agent_tool] = by_agent.get(learning.agent_tool, 0) + 1

                # By frequency
                freq = learning.frequency.value
                by_frequency[freq] = by_frequency.get(freq, 0) + 1

            # Collect rule errors
            for rule_name, error_msg in result.rule_errors.items():
                all_rule_errors[rule_name] = error_msg

        summary.by_type = by_type
        summary.by_agent = by_agent
        summary.by_frequency = by_frequency

        # Track which rules were checked, passed, warned, failed, and errored
        if types_checked:
            summary.rules_checked = list(types_checked.keys())
            summary.rules_errored = list(all_rule_errors.keys())  # Rules with errors
            summary.rule_errors = all_rule_errors

            # Separate warnings from failures based on severity
            rules_warned = []
            rules_failed = []

            for learning_type in by_type.keys():
                # Get severity for this learning type
                severity = SeverityLevel.WARNING  # Default
                if learning_type in self.config.drift_learning_types:
                    type_config = self.config.drift_learning_types[learning_type]
                    if type_config.severity is not None:
                        severity = type_config.severity
                    elif type_config.scope == "project_level":
                        severity = SeverityLevel.FAIL
                    else:
                        severity = SeverityLevel.WARNING

                if severity == SeverityLevel.FAIL:
                    rules_failed.append(learning_type)
                elif severity == SeverityLevel.WARNING:
                    rules_warned.append(learning_type)
                # PASS shouldn't produce learnings, but if it does, treat as warning

            summary.rules_warned = rules_warned
            summary.rules_failed = rules_failed
            summary.rules_passed = [
                rule
                for rule in summary.rules_checked
                if rule not in rules_warned
                and rule not in rules_failed
                and rule not in summary.rules_errored
            ]

        return summary

    def analyze_documents(
        self,
        learning_types: Optional[List[str]] = None,
        model_override: Optional[str] = None,
    ) -> CompleteAnalysisResult:
        """Run drift analysis on project documents.

        Args:
            learning_types: Optional list of specific learning types to check
            model_override: Optional model to use (overrides all config settings)

        Returns:
            Complete analysis results with document learnings
        """
        if not self.project_path:
            raise ValueError("Project path required for document analysis")

        all_types = (
            {lt: self.config.drift_learning_types[lt] for lt in learning_types}
            if learning_types is not None
            else self.config.drift_learning_types
        )

        document_types = {}
        for name, config in all_types.items():
            # Include rules with document bundles
            if hasattr(config, "document_bundle") and config.document_bundle is not None:
                document_types[name] = config
            elif (
                hasattr(config, "validation_rules")
                and config.validation_rules is not None
                and hasattr(config.validation_rules, "document_bundle")
            ):
                document_types[name] = config
            # Also include project-level rules with programmatic phases (no document bundle needed)
            elif config.scope in ("project_level", "document_level"):
                phases = getattr(config, "phases", [])
                if _has_programmatic_phases(phases):
                    document_types[name] = config

        if not document_types:
            return CompleteAnalysisResult(
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "execution_details": [],
                },
                summary=AnalysisSummary(
                    total_conversations=0,
                    total_learnings=0,
                    conversations_with_drift=0,
                    conversations_without_drift=0,
                ),
                results=[],
            )

        doc_loader = DocumentLoader(self.project_path)

        all_document_learnings: List[DocumentLearning] = []
        all_execution_details: List[dict] = []

        logger.debug(
            f"analyze_documents: Processing {len(document_types)} document types: "
            f"{list(document_types.keys())}"
        )

        for type_name, type_config in document_types.items():
            logger.debug(f"analyze_documents: Processing type {type_name}")
            try:
                bundle_config = type_config.document_bundle
                logger.debug(f"analyze_documents: {type_name} document_bundle={bundle_config}")
                if bundle_config is None and hasattr(type_config, "validation_rules"):
                    logger.debug(
                        f"analyze_documents: {type_name} has validation_rules, "
                        "checking document_bundle"
                    )
                    if type_config.validation_rules is not None:
                        bundle_config = type_config.validation_rules.document_bundle
                        logger.debug(
                            f"analyze_documents: {type_name} got bundle_config "
                            f"from validation_rules: {bundle_config}"
                        )

                # Check if we can proceed without bundle_config (old phases format)
                phases = getattr(type_config, "phases", []) or []
                has_programmatic_phases = _has_programmatic_phases(phases)
                has_validation_rules = getattr(type_config, "validation_rules", None) is not None

                if bundle_config is None and not has_programmatic_phases:
                    logger.debug(
                        f"analyze_documents: {type_name} has no bundle_config and "
                        "no programmatic phases, skipping"
                    )
                    continue

                bundles = doc_loader.load_bundles(bundle_config) if bundle_config else []

                if not bundles:
                    if has_validation_rules or has_programmatic_phases:
                        # For old phases format without bundle_config, use default values
                        bundle_type = (
                            bundle_config.bundle_type if bundle_config else "project_files"
                        )
                        bundle_strategy = (
                            bundle_config.bundle_strategy.value
                            if bundle_config
                            else BundleStrategy.COLLECTION.value
                        )

                        empty_bundle = DocumentBundle(
                            bundle_id="empty",
                            bundle_type=bundle_type,
                            bundle_strategy=bundle_strategy,
                            files=[],
                            project_path=self.project_path,
                        )
                        learnings, exec_details = self._analyze_document_bundle(
                            empty_bundle, type_name, type_config, model_override, doc_loader
                        )
                        all_document_learnings.extend(learnings)
                        all_execution_details.extend(exec_details)
                    continue

                # At this point bundle_config must exist (bundles were loaded from it)
                assert bundle_config is not None

                if bundle_config.bundle_strategy == BundleStrategy.INDIVIDUAL:
                    for bundle in bundles:
                        learnings, exec_details = self._analyze_document_bundle(
                            bundle, type_name, type_config, model_override, doc_loader
                        )
                        all_document_learnings.extend(learnings)
                        all_execution_details.extend(exec_details)
                else:
                    if bundles:
                        combined_bundle = self._combine_bundles(bundles, type_config)
                        learnings, exec_details = self._analyze_document_bundle(
                            combined_bundle, type_name, type_config, model_override, doc_loader
                        )
                        if learnings:
                            all_document_learnings.append(learnings[0])
                        all_execution_details.extend(exec_details)

            except Exception as e:
                error_msg = str(e)
                if any(
                    keyword in error_msg
                    for keyword in [
                        "Bedrock API error",
                        "API error",
                        "provider is not available",
                        "client is not available",
                        "ValidationException",
                        "ThrottlingException",
                        "ServiceException",
                    ]
                ):
                    raise
                logger.warning(f"Failed to analyze documents for {type_name}: {e}")
                continue

        # Convert DocumentLearnings to Learnings for compatibility with AnalysisResult
        converted_learnings = []
        for doc_learning in all_document_learnings:
            # Map DocumentLearning fields to Learning fields
            learning = Learning(
                turn_number=1,  # Document learnings aren't tied to specific turns
                turn_uuid=None,
                agent_tool="documents",
                conversation_file="N/A",
                observed_behavior=doc_learning.observed_issue,
                expected_behavior=doc_learning.expected_quality,
                learning_type=doc_learning.learning_type,
                frequency=FrequencyType.ONE_TIME,
                workflow_element=WorkflowElement.UNKNOWN,
                turns_to_resolve=1,
                turns_involved=[],
                context=doc_learning.context,
                resources_consulted=[],
                phases_count=1,
            )
            converted_learnings.append(learning)

        result = AnalysisResult(
            session_id="document_analysis",
            agent_tool="documents",
            conversation_file="N/A",
            project_path=str(self.project_path),
            learnings=converted_learnings,
            analysis_timestamp=datetime.now(),
            error=None,
        )

        summary = AnalysisSummary(
            total_conversations=0,
            total_learnings=len(all_document_learnings),
            conversations_with_drift=0,
            conversations_without_drift=0,
        )

        by_type: Dict[str, int] = {}
        for doc_learning in all_document_learnings:
            by_type[doc_learning.learning_type] = by_type.get(doc_learning.learning_type, 0) + 1
        summary.by_type = by_type

        summary.rules_checked = list(document_types.keys())

        # Separate warnings from failures based on severity
        rules_warned = []
        rules_failed = []

        for learning_type in by_type.keys():
            # Get severity for this learning type
            severity = SeverityLevel.WARNING  # Default
            if learning_type in self.config.drift_learning_types:
                type_config = self.config.drift_learning_types[learning_type]
                if type_config.severity is not None:
                    severity = type_config.severity
                elif type_config.scope == "project_level":
                    severity = SeverityLevel.FAIL
                else:
                    severity = SeverityLevel.WARNING

            if severity == SeverityLevel.FAIL:
                rules_failed.append(learning_type)
            elif severity == SeverityLevel.WARNING:
                rules_warned.append(learning_type)

        summary.rules_warned = rules_warned
        summary.rules_failed = rules_failed
        summary.rules_passed = [
            rule
            for rule in summary.rules_checked
            if rule not in rules_warned and rule not in rules_failed
        ]

        logger.info(f"analyze_documents: Returning {len(all_execution_details)} execution details")
        logger.debug(f"analyze_documents: execution_details = {all_execution_details}")

        return CompleteAnalysisResult(
            metadata={
                "generated_at": datetime.now().isoformat(),
                "analysis_type": "documents",
                "project_path": str(self.project_path),
                "document_learnings": [
                    learning.model_dump() for learning in all_document_learnings
                ],
                "execution_details": all_execution_details,
            },
            summary=summary,
            results=[result] if all_document_learnings else [],
        )

    def _analyze_document_bundle(
        self,
        bundle: DocumentBundle,
        learning_type: str,
        type_config: Any,
        model_override: Optional[str],
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentLearning], List[dict]]:
        """Analyze a single document bundle.

        Args:
            bundle: Document bundle to analyze
            learning_type: Name of learning type
            type_config: Configuration for this learning type
            model_override: Optional model override
            loader: Optional document loader for resource access

        Returns:
            Tuple of (learnings, execution_details)
        """
        validation_rules = getattr(type_config, "validation_rules", None)
        logger.debug(
            f"_analyze_document_bundle for {learning_type}: validation_rules={validation_rules}"
        )

        if validation_rules is not None:
            logger.debug(
                f"_analyze_document_bundle: Calling _execute_validation_rules for {learning_type}"
            )
            return self._execute_validation_rules(bundle, learning_type, type_config, loader)

        phases = getattr(type_config, "phases", [])

        if phases:
            programmatic_phases = [
                p for p in phases if getattr(p, "type", "prompt") in PROGRAMMATIC_PHASE_TYPES
            ]

            if programmatic_phases:
                registry = ValidatorRegistry()
                learnings = []
                execution_details = []

                for phase in programmatic_phases:
                    rule = ValidationRule(
                        rule_type=ValidationType(phase.type),
                        description=type_config.description,
                        file_path=phase.file_path,
                        failure_message=phase.failure_message or type_config.description,
                        expected_behavior=(phase.expected_behavior or type_config.context),
                        **phase.params,
                    )

                    result = registry.execute_rule(rule, bundle)

                    # Track execution
                    exec_info = {
                        "rule_name": learning_type,
                        "rule_description": rule.description,
                        "rule_context": type_config.context,
                        "status": "passed" if result is None else "failed",
                        "execution_context": {
                            "bundle_id": bundle.bundle_id,
                            "bundle_type": bundle.bundle_type,
                            "files": [f.relative_path for f in bundle.files],
                        },
                        "validation_results": {
                            "rule_type": rule.rule_type.value
                            if hasattr(rule.rule_type, "value")
                            else str(rule.rule_type),
                            "params": getattr(rule, "params", {}),
                        },
                    }
                    execution_details.append(exec_info)

                    if result is not None:
                        result.learning_type = learning_type
                        learnings.append(result)

                return learnings, execution_details

        if len(phases) > 1:
            return self._run_multi_phase_document_analysis(
                bundle, learning_type, type_config, model_override, loader
            )

        prompt = self._build_document_analysis_prompt(bundle, learning_type, type_config)

        phase_model = phases[0].model if phases else None
        model_name = (
            model_override or phase_model or self.config.get_model_for_learning_type(learning_type)
        )

        provider = self.providers.get(model_name)
        if not provider:
            raise ValueError(f"Model '{model_name}' not found in configured providers")

        logger.debug(f"Sending prompt to {model_name}:\n{prompt}")
        response = provider.generate(prompt)
        logger.debug(f"Raw response from {model_name}:\n{response}")

        learnings = self._parse_document_analysis_response(response, bundle, learning_type)

        # No programmatic execution details for LLM-based analysis
        return learnings, []

    def _run_multi_phase_document_analysis(
        self,
        bundle: DocumentBundle,
        learning_type: str,
        type_config: Any,
        model_override: Optional[str] = None,
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentLearning], List[dict]]:
        """Run multi-phase analysis on a document bundle."""
        phases = getattr(type_config, "phases", [])
        if not phases:
            raise ValueError(
                f"Learning type '{learning_type}' routed to multi-phase analysis "
                "but no phases configured"
            )

        # For documents, we just run single-phase for now with the first phase
        # Multi-phase with resource requests doesn't make sense for static documents
        phase_model = phases[0].model if phases else None
        model_name = (
            model_override or phase_model or self.config.get_model_for_learning_type(learning_type)
        )

        provider = self.providers.get(model_name)
        if not provider:
            raise ValueError(f"Model '{model_name}' not found in configured providers")

        prompt = self._build_document_analysis_prompt(bundle, learning_type, type_config)
        logger.debug(f"Sending prompt to {model_name}:\n{prompt}")
        response = provider.generate(prompt)
        logger.debug(f"Raw response from {model_name}:\n{response}")
        learnings = self._parse_document_analysis_response(response, bundle, learning_type)

        # No programmatic execution details for LLM-based document analysis
        return learnings, []

    def _execute_validation_rules(
        self,
        bundle: DocumentBundle,
        learning_type: str,
        type_config: Any,
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentLearning], List[dict]]:
        """Execute rule-based validation on a bundle.

        Args:
            bundle: Document bundle to validate
            learning_type: Name of learning type
            type_config: Configuration for this learning type
            loader: Optional document loader for resource access

        Returns:
            Tuple of (learnings, execution_details).
            learnings: List of document learnings from failed validations
            execution_details: List of dicts with execution info for ALL rules
        """
        logger.debug(f"_execute_validation_rules called for {learning_type}")
        validation_config = getattr(type_config, "validation_rules", None)
        if not validation_config:
            raise ValueError(
                f"Learning type '{learning_type}' routed to programmatic validation "
                "but no validation_rules configured"
            )

        registry = ValidatorRegistry(loader)
        learnings = []
        execution_details = []

        logger.debug(
            f"_validate_document_bundle: Processing {len(validation_config.rules)} rules "
            f"for {learning_type}"
        )

        for rule in validation_config.rules:
            try:
                logger.debug(f"_validate_document_bundle: Executing rule {rule.description}")
                result = registry.execute_rule(rule, bundle)
                logger.debug(f"_validate_document_bundle: Rule result: {result}")

                # Track execution info for this rule
                exec_info = {
                    "rule_name": learning_type,
                    "rule_description": rule.description,
                    "status": "passed" if result is None else "failed",
                    "execution_context": {
                        "bundle_id": bundle.bundle_id,
                        "bundle_type": bundle.bundle_type,
                        "files": [f.relative_path for f in bundle.files],
                    },
                    "validation_results": {
                        "rule_type": rule.rule_type.value
                        if hasattr(rule.rule_type, "value")
                        else str(rule.rule_type),
                        "params": rule.params if hasattr(rule, "params") else {},
                    },
                }
                execution_details.append(exec_info)

                if result is not None:
                    # Validation failed - set the learning type name
                    result.learning_type = learning_type
                    learnings.append(result)

            except Exception as e:
                # Log error but continue with other rules
                logger.warning(f"Validation rule '{rule.description}' failed: {e}")

                # Track error in execution details
                exec_info = {
                    "rule_name": learning_type,
                    "rule_description": rule.description,
                    "status": "errored",
                    "error_message": str(e),
                }
                execution_details.append(exec_info)
                continue

        return learnings, execution_details

    def _build_document_analysis_prompt(
        self,
        bundle: DocumentBundle,
        learning_type: str,
        type_config: Any,
    ) -> str:
        """Build prompt for document analysis.

        Args:
            bundle: Document bundle to analyze
            learning_type: Name of learning type
            type_config: Configuration for this learning type

        Returns:
            Formatted prompt string
        """
        description = getattr(type_config, "description", "")
        phases = getattr(type_config, "phases", [])
        detection_prompt = phases[0].prompt if phases else ""

        # Format bundle content
        doc_loader = DocumentLoader(bundle.project_path)
        formatted_files = doc_loader.format_bundle_for_llm(bundle)

        # Build prompt with template variable substitution
        prompt = f"""You are analyzing project documentation to identify quality issues.

**Analysis Type:** {learning_type}
**Description:** {description}

**Project Root:** {bundle.project_path}

**Bundle Type:** {bundle.bundle_type}

**Files Being Analyzed:**
{formatted_files}

**Detection Instructions:**
{detection_prompt}

**Task:**
Analyze the above documentation and identify any instances of the "{learning_type}" pattern.

For each issue found, extract:
1. Which file(s) are involved (use relative paths from the Files Being Analyzed section)
2. What issue was observed
3. What the expected quality/behavior should be
4. Brief explanation

Return your analysis as a JSON array:
[
  {{
    "file_paths": ["path/to/file1.md", "path/to/file2.md"],
    "observed_issue": "<description of the problem>",
    "expected_quality": "<what should be present/correct>",
    "context": "<brief explanation>"
  }}
]

If no issues are found, return an empty array: []

IMPORTANT: Return ONLY valid JSON, no additional text or explanation."""

        return prompt

    def _parse_document_analysis_response(
        self,
        response: str,
        bundle: DocumentBundle,
        learning_type: str,
    ) -> List[DocumentLearning]:
        """Parse document analysis response from LLM.

        Args:
            response: Raw response from LLM
            bundle: Document bundle that was analyzed
            learning_type: Type of learning

        Returns:
            List of parsed document learnings
        """
        import json
        import re

        # Extract JSON from response
        json_match = re.search(r"\[[\s\S]*\]", response)
        if not json_match:
            return []

        try:
            items = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return []

        if not isinstance(items, list):
            return []

        # Convert to DocumentLearning objects
        learnings = []
        for item in items:
            if not isinstance(item, dict):
                continue

            learning = DocumentLearning(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=item.get("file_paths", []),
                observed_issue=item.get("observed_issue", ""),
                expected_quality=item.get("expected_quality", ""),
                learning_type=learning_type,
                context=item.get("context", ""),
            )
            learnings.append(learning)

        return learnings

    def _combine_bundles(
        self,
        bundles: List[DocumentBundle],
        type_config: Any,
    ) -> DocumentBundle:
        """Combine multiple bundles into a single mega-bundle for project-level analysis.

        Args:
            bundles: List of bundles to combine
            type_config: Learning type configuration

        Returns:
            Combined document bundle
        """
        all_files = []
        for bundle in bundles:
            all_files.extend(bundle.files)

        # Remove duplicates based on file path
        seen_paths = set()
        unique_files = []
        for file in all_files:
            if file.file_path not in seen_paths:
                seen_paths.add(file.file_path)
                unique_files.append(file)

        # Get document bundle config (either directly or from validation_rules)
        bundle_config = type_config.document_bundle
        if bundle_config is None and hasattr(type_config, "validation_rules"):
            bundle_config = type_config.validation_rules.document_bundle

        return DocumentBundle(
            bundle_id="combined_project_level",
            bundle_type=bundle_config.bundle_type,
            bundle_strategy="collection",
            files=unique_files,
            project_path=bundles[0].project_path,
        )

    def _run_multi_phase_analysis(
        self,
        conversation: Conversation,
        learning_type: str,
        type_config: Any,
        model_override: Optional[str],
    ) -> tuple[List[Learning], Optional[str], List[PhaseAnalysisResult]]:
        """Execute multi-phase analysis with resource requests.

        Returns:
            Tuple of (learnings, error_message, phase_results).
            error_message is None if successful.
            phase_results contains all PhaseAnalysisResult objects from execution.
        """
        # Get phases from config
        phases = getattr(type_config, "phases", [])
        if not phases:
            raise ValueError(
                f"Learning type '{learning_type}' routed to multi-phase analysis "
                "but no phases configured"
            )

        # Get agent loader for resource extraction
        agent_loader = self.agent_loaders.get(conversation.agent_tool)
        if not agent_loader:
            error_msg = f"No agent loader available for {conversation.agent_tool}"
            return [], error_msg, []

        # Track resources consulted
        resources_consulted: List[str] = []
        phase_results: List[PhaseAnalysisResult] = []

        logger.info(
            f"Starting multi-phase analysis for {learning_type} with {len(phases)} phase(s)"
        )

        # Phase 1: Initial analysis
        phase_idx = 0
        phase_def = phases[phase_idx]
        logger.info(f"Starting phase {phase_idx + 1}: {phase_def.name}")
        prompt = self._build_multi_phase_prompt(
            conversation=conversation,
            learning_type=learning_type,
            type_config=type_config,
            phase_idx=phase_idx,
            phase_def=phase_def,
            resources_loaded=[],
            previous_findings=[],
        )

        # Iterative analysis loop
        while phase_idx < len(phases):
            phase_def = phases[phase_idx]
            phase_type = getattr(phase_def, "type", "prompt")

            # Check if this is a programmatic phase
            if phase_type != "prompt":
                # Programmatic phases don't make sense in conversation context
                # They're for validating static documents/files
                phase_idx += 1
                continue

            # AI phase - get provider
            phase_model = (
                phase_def.model if hasattr(phase_def, "model") and phase_def.model else None
            )
            model_name = (
                model_override
                or phase_model
                or self.config.get_model_for_learning_type(learning_type)
            )

            provider = self.providers.get(model_name)
            if not provider:
                raise ValueError(f"Model '{model_name}' not found in configured providers")

            if not provider.is_available():
                raise RuntimeError(
                    f"Provider for model '{model_name}' is not available. "
                    "Check credentials and configuration."
                )

            # Call LLM
            logger.debug(f"Sending phase {phase_idx + 1} prompt to {model_name}:\n{prompt}")
            response = provider.generate(prompt)
            logger.debug(f"Raw response from {model_name} (phase {phase_idx + 1}):\n{response}")

            # Parse response
            phase_result = self._parse_phase_response(response, phase_idx + 1)
            phase_results.append(phase_result)
            num_requests = len(phase_result.resource_requests or [])
            logger.debug(
                f"Phase {phase_idx + 1} result: "
                f"{len(phase_result.findings)} finding(s), {num_requests} resource request(s)"
            )

            # Check termination
            if phase_result.final_determination:
                logger.info(f"Phase {phase_idx + 1} reached final determination")
                break

            if not phase_result.resource_requests:
                logger.info(f"Phase {phase_idx + 1} has no resource requests, ending analysis")
                break

            # Load requested resources
            num_requests = len(phase_result.resource_requests)
            logger.info(f"Phase {phase_idx + 1} requesting {num_requests} resource(s)")
            resources_loaded: List[ResourceResponse] = []
            for req in phase_result.resource_requests:
                # Validate resource is in available_resources
                # Check for exact match "type:id" or type-only match "type"
                resource_spec = f"{req.resource_type}:{req.resource_id}"
                if (
                    resource_spec not in phase_def.available_resources
                    and req.resource_type not in phase_def.available_resources
                ):
                    logger.debug(f"Resource {resource_spec} not in available_resources, skipping")
                    continue

                # Load resource
                logger.debug(f"Loading resource: {req.resource_type}:{req.resource_id}")
                resource = agent_loader.get_resource(
                    resource_type=req.resource_type,
                    resource_id=req.resource_id,
                    project_path=conversation.project_path,
                )
                resources_loaded.append(resource)

                # Track what was consulted
                if resource.found:
                    logger.debug(f"Resource found: {req.resource_type}:{req.resource_id}")
                    resources_consulted.append(f"{req.resource_type}:{req.resource_id}")
                else:
                    logger.debug(f"Resource not found: {req.resource_type}:{req.resource_id}")

            # Check if all requests failed
            if resources_loaded and all(not r.found for r in resources_loaded):
                # All resources missing - create missing resource learnings
                return self._create_missing_resource_learnings(
                    conversation=conversation,
                    learning_type=learning_type,
                    resources_loaded=resources_loaded,
                    phase_results=phase_results,
                )

            # Move to next phase
            phase_idx += 1
            if phase_idx < len(phases):
                phase_def = phases[phase_idx]
                logger.info(f"Starting phase {phase_idx + 1}: {phase_def.name}")
                prompt = self._build_multi_phase_prompt(
                    conversation=conversation,
                    learning_type=learning_type,
                    type_config=type_config,
                    phase_idx=phase_idx,
                    phase_def=phase_def,
                    resources_loaded=resources_loaded,
                    previous_findings=phase_result.findings,
                )

        # Finalize learnings from all phases
        learnings, error = self._finalize_multi_phase_learnings(
            conversation=conversation,
            learning_type=learning_type,
            phase_results=phase_results,
            resources_consulted=resources_consulted,
        )

        # Return learnings, error, AND phase_results (stop throwing them away!)
        return learnings, error, phase_results

    def _build_multi_phase_prompt(
        self,
        conversation: Conversation,
        learning_type: str,
        type_config: Any,
        phase_idx: int,
        phase_def: Any,
        resources_loaded: List[ResourceResponse],
        previous_findings: List[Dict[str, Any]],
    ) -> str:
        """Build prompt for multi-phase analysis."""
        context = getattr(type_config, "context", "")

        # Get phase-specific prompt
        phase_prompt = phase_def.prompt if hasattr(phase_def, "prompt") and phase_def.prompt else ""
        phase_name = phase_def.name if hasattr(phase_def, "name") else f"phase_{phase_idx + 1}"

        if phase_idx == 0:
            # Initial analysis - no resources yet
            conversation_text = self._format_conversation(conversation)

            # Use phase-specific prompt
            analysis_instructions = phase_prompt if phase_prompt else context

            prompt = f"""You are analyzing an AI agent conversation to identify drift patterns.

**Analysis Type**: {learning_type}
**Phase**: {phase_name}
**Description**: {type_config.description}
**Context**: {context}

**Analysis Instructions**:
{analysis_instructions}

**Conversation**:
{conversation_text}

**Task**:
Analyze this conversation for the drift pattern described above.

You can request specific project resources to validate your findings:
- command: Slash commands (e.g., "deploy", "test")
- skill: Skills (e.g., "api-design", "testing")
- agent: Custom agents (e.g., "code-reviewer")
- main_config: Main config file (CLAUDE.md or .mcp.json)

Return a JSON object with:
{{
  "findings": [
    {{
      "turn_number": <int>,
      "observed_behavior": "<what happened>",
      "expected_behavior": "<what should happen>",
      "context": "<explanation>"
    }}
  ],
  "resource_requests": [
    {{
      "resource_type": "command|skill|agent|main_config",
      "resource_id": "<name>",
      "reason": "<why you need this>"
    }}
  ],
  "final_determination": false
}}

If you need to verify findings by checking project files, set resource_requests.
If you're confident without additional resources, set final_determination=true.
"""
        else:
            # Subsequent phases - MUST INCLUDE CONVERSATION + loaded resources
            conversation_text = self._format_conversation(conversation)
            resources_section = self._format_loaded_resources(resources_loaded)
            findings_section = self._format_previous_findings(previous_findings)

            # Use phase-specific prompt if available
            default_instructions = (
                "Review the conversation, loaded resources, and previous findings. Determine:\n"
                "1. Do the resources confirm or refute your findings?\n"
                "2. Do you need additional resources to make a determination?\n"
                "3. Can you now provide a final determination?"
            )
            phase_instructions = phase_prompt if phase_prompt else default_instructions

            prompt_prefix = (
                f'You are in phase "{phase_name}" of multi-phase analysis '
                f"for drift pattern: {learning_type}"
            )
            prompt = f"""{prompt_prefix}

**Analysis Type**: {learning_type}
**Description**: {type_config.description}
**Context**: {context}

**Conversation**:
{conversation_text}

**Previous Findings**:
{findings_section}

**Resources Loaded**:
{resources_section}

**Phase Instructions**:
{phase_instructions}

Return JSON with the same format:
- Update "findings" if needed based on resources
- Add more "resource_requests" if needed
- Set "final_determination": true when ready
"""

        return prompt

    def _format_loaded_resources(self, resources: List[ResourceResponse]) -> str:
        """Format loaded resources for prompt."""
        if not resources:
            return "No resources loaded yet."

        sections = []
        for resource in resources:
            if resource.found:
                sections.append(
                    f"**{resource.request.resource_type}:{resource.request.resource_id}**\n"
                    f"File: {resource.file_path}\n"
                    f"Content:\n{resource.content}\n"
                )
            else:
                sections.append(
                    f"**{resource.request.resource_type}:"
                    f"{resource.request.resource_id}** - NOT FOUND\n"
                    f"Error: {resource.error}\n"
                )

        return "\n---\n".join(sections)

    def _format_previous_findings(self, findings: List[Dict[str, Any]]) -> str:
        """Format previous findings for prompt."""
        if not findings:
            return "No findings yet."

        sections = []
        for i, finding in enumerate(findings, 1):
            sections.append(
                f"{i}. Turn {finding.get('turn_number', 'N/A')}\n"
                f"   Observed: {finding.get('observed_behavior', 'N/A')}\n"
                f"   Expected: {finding.get('expected_behavior', 'N/A')}\n"
                f"   Context: {finding.get('context', 'N/A')}"
            )

        return "\n".join(sections)

    def _parse_phase_response(self, response: str, phase: int) -> PhaseAnalysisResult:
        """Parse LLM response for a phase."""
        # Extract JSON
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            return PhaseAnalysisResult(
                phase_number=phase,
                resource_requests=[],
                findings=[],
                final_determination=True,  # No requests = done
            )

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            return PhaseAnalysisResult(
                phase_number=phase,
                resource_requests=[],
                findings=[],
                final_determination=True,
            )

        # Parse resource requests
        requests = []
        for req_data in data.get("resource_requests", []):
            # Handle various naming conventions that LLM might use
            resource_type = (
                req_data.get("resource_type") or req_data.get("type") or req_data.get("resource")
            )
            resource_id = (
                req_data.get("resource_id")
                or req_data.get("name")
                or req_data.get("identifier")
                or req_data.get("id")
            )

            if not resource_type or not resource_id:
                logger.warning(f"Skipping resource request with missing fields: {req_data}")
                continue

            requests.append(
                ResourceRequest(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    reason=req_data.get("reason", ""),
                )
            )

        return PhaseAnalysisResult(
            phase_number=phase,
            resource_requests=requests,
            findings=data.get("findings", []),
            final_determination=data.get("final_determination", False),
        )

    def _create_missing_resource_learnings(
        self,
        conversation: Conversation,
        learning_type: str,
        resources_loaded: List[ResourceResponse],
        phase_results: List[PhaseAnalysisResult],
    ) -> tuple[List[Learning], Optional[str], List[PhaseAnalysisResult]]:
        """Create learnings when requested resources are missing.

        Returns:
            Tuple of (learnings, error_message). Always returns None for error since
            missing resources are valid learnings, not errors.
        """
        learnings = []

        for resource in resources_loaded:
            if not resource.found:
                # Missing resource IS the drift
                learning = Learning(
                    turn_number=1,  # Not turn-specific
                    turn_uuid=None,
                    agent_tool=conversation.agent_tool,
                    conversation_file=conversation.file_path,
                    observed_behavior=(
                        resource.error
                        or f"{resource.request.resource_type} "
                        f"'{resource.request.resource_id}' not found"
                    ),
                    expected_behavior=(
                        f"{resource.request.resource_type} "
                        f"'{resource.request.resource_id}' should exist in project"
                    ),
                    learning_type=f"missing_{resource.request.resource_type}",
                    frequency=FrequencyType.ONE_TIME,
                    workflow_element=WorkflowElement.UNKNOWN,
                    turns_to_resolve=1,
                    turns_involved=[],
                    context=resource.request.reason,
                    resources_consulted=[
                        f"{resource.request.resource_type}:{resource.request.resource_id}"
                    ],
                    phases_count=len(phase_results),
                )
                learnings.append(learning)

        return learnings, None, phase_results

    def _finalize_multi_phase_learnings(
        self,
        conversation: Conversation,
        learning_type: str,
        phase_results: List[PhaseAnalysisResult],
        resources_consulted: List[str],
    ) -> tuple[List[Learning], Optional[str]]:
        """Convert final phase results to Learning objects.

        Returns:
            Tuple of (learnings, error_message). error_message is set if findings are malformed.
        """
        # Get final findings (last phase)
        final_phase = phase_results[-1]

        learnings = []
        malformed_count = 0

        for finding in final_phase.findings:
            # Validate that finding has required fields
            observed = finding.get("observed_behavior", "").strip()
            expected = finding.get("expected_behavior", "").strip()

            # Track malformed findings
            if not observed or not expected:
                malformed_count += 1
                continue

            learning = Learning(
                turn_number=finding.get("turn_number", 0),
                turn_uuid=None,
                agent_tool=conversation.agent_tool,
                conversation_file=conversation.file_path,
                observed_behavior=observed,
                expected_behavior=expected,
                learning_type=learning_type,
                frequency=FrequencyType.ONE_TIME,
                workflow_element=WorkflowElement.UNKNOWN,
                turns_to_resolve=1,
                turns_involved=[],
                context=finding.get("context", ""),
                resources_consulted=resources_consulted,
                phases_count=len(phase_results),
            )
            learnings.append(learning)

        # Return error if we had malformed findings
        error = None
        if malformed_count > 0:
            error = (
                f"Multi-phase analysis returned {malformed_count} malformed finding(s) "
                f"with missing observed_behavior or expected_behavior fields"
            )

        return learnings, error

    def cleanup(self) -> None:
        """Clean up temporary files."""
        self.temp_manager.cleanup()
