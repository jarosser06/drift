"""Main analysis orchestration for drift detection.

Parallel Execution
------------------
Validation rules execute in parallel by default when multiple rules are present.
Single rules execute sequentially to avoid async overhead.

Configuration:
    parallel_execution:
      enabled: true  # Default

Thread Safety:
    Each parallel task gets its own ValidatorRegistry instance to prevent
    race conditions during file I/O.
"""

import asyncio
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
from drift.cache import ResponseCache
from drift.config.loader import ConfigLoader
from drift.config.models import (
    BundleStrategy,
    ClientType,
    DriftConfig,
    ProviderType,
    RuleDefinition,
    SeverityLevel,
    ValidationRule,
)
from drift.core.types import (
    AnalysisResult,
    AnalysisSummary,
    CompleteAnalysisResult,
    Conversation,
    DocumentBundle,
    DocumentRule,
    PhaseAnalysisResult,
    ResourceRequest,
    ResourceResponse,
    Rule,
    WorkflowElement,
)
from drift.documents.loader import DocumentLoader
from drift.providers.anthropic import AnthropicProvider
from drift.providers.base import Provider
from drift.providers.bedrock import BedrockProvider
from drift.providers.claude_code import ClaudeCodeProvider
from drift.utils.temp import TempManager
from drift.validation.validators import ValidatorRegistry

logger = logging.getLogger(__name__)


def _has_programmatic_phases(phases: List[Any], registry: ValidatorRegistry) -> bool:
    """Check if any phases are programmatic (non-LLM) types.

    Args:
        phases: List of phase definitions
        registry: ValidatorRegistry to check computation types

    Returns:
        True if any phase has a programmatic type
    """
    if not phases:
        return False

    for phase in phases:
        phase_type = getattr(phase, "type", "prompt")
        if phase_type == "prompt":
            continue

        try:
            # Check if this is a programmatic validator
            provider = getattr(phase, "provider", None)
            if registry.is_programmatic(phase_type, provider):
                return True
        except (ValueError, KeyError):
            # Unknown type - assume it's LLM-based
            continue

    return False


def _get_supported_clients_from_rule(
    rule_def: RuleDefinition, registry: ValidatorRegistry, agent_tool: str
) -> Optional[List[str]]:
    """Determine supported clients for a rule based on its validation rules.

    If the rule has explicit supported_clients, use that.
    Otherwise, derive it from the validators used in validation_rules.

    -- rule_def: The rule definition to check
    -- registry: ValidatorRegistry to check validator client support
    -- agent_tool: The agent tool from the conversation (e.g., "claude-code")

    Returns List[str] of supported clients, or None if all clients supported.
    """
    # If explicitly set, use that
    if rule_def.supported_clients is not None:
        return rule_def.supported_clients

    # If no validation rules, rule supports all clients (LLM-based rules)
    if not rule_def.validation_rules or not rule_def.validation_rules.rules:
        return None

    # Collect all client types from validators
    all_supported_clients = set()
    supports_all = False

    for val_rule in rule_def.validation_rules.rules:
        try:
            clients = registry.get_supported_clients(val_rule.rule_type)
            if ClientType.ALL in clients:
                supports_all = True
            else:
                # Convert ClientType enum to string for comparison with agent_tool
                for client in clients:
                    if client == ClientType.CLAUDE:
                        all_supported_clients.add("claude-code")
                    # Add more mappings here as needed for other client types
        except ValueError:
            # Unknown validator type - assume it supports all clients
            supports_all = True

    # If any validator supports ALL, the rule supports all clients
    if supports_all:
        return None

    # Return the list of supported client strings
    return list(all_supported_clients) if all_supported_clients else None


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

        # Initialize response cache
        cache_dir = Path(self.config.cache_dir).expanduser()
        if self.project_path:
            cache_dir = self.project_path / cache_dir
        self.cache = ResponseCache(
            cache_dir=cache_dir,
            default_ttl=self.config.cache_ttl,
            enabled=self.config.cache_enabled,
        )

        # Initialize validator registry for client filtering
        self.validator_registry = ValidatorRegistry()

        self._initialize_providers()
        self._initialize_agent_loaders()

    def _get_effective_group_name(self, rule_type: str) -> str:
        """Get the effective group name for a rule.

        If the rule has an explicit group_name, use that.
        Otherwise, use the default_group_name from config.

        -- rule_type: Name of the rule type

        Returns the effective group name to use.
        """
        if rule_type in self.config.rule_definitions:
            rule_def = self.config.rule_definitions[rule_type]
            return rule_def.group_name or self.config.default_group_name
        return self.config.default_group_name

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
            if provider_config.provider == ProviderType.ANTHROPIC:
                self.providers[model_name] = AnthropicProvider(
                    provider_config, model_config, self.cache
                )
            elif provider_config.provider == ProviderType.BEDROCK:
                self.providers[model_name] = BedrockProvider(
                    provider_config, model_config, self.cache
                )
            elif provider_config.provider == ProviderType.CLAUDE_CODE:
                self.providers[model_name] = ClaudeCodeProvider(
                    provider_config, model_config, self.cache
                )

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
        rule_types: Optional[List[str]] = None,
        model_override: Optional[str] = None,
    ) -> CompleteAnalysisResult:
        """Run drift analysis on conversations.

        Args:
            agent_tool: Optional specific agent tool to analyze
            rule_types: Optional list of specific rules to check
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

            # Determine which rules to check
            all_types = (
                {lt: self.config.rule_definitions[lt] for lt in rule_types}
                if rule_types is not None
                else self.config.rule_definitions
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
                        "No conversation-based rules configured. "
                        f"Skipped document/project-level rules (use --scope project): "
                        f"{', '.join(filtered_rules)}"
                    )
                return CompleteAnalysisResult(
                    metadata={
                        "generated_at": datetime.now().isoformat(),
                        "session_id": session_id,
                        "message": "No conversation-based rules configured",
                        "skipped_rules": filtered_rules,
                        "execution_details": [],
                    },
                    summary=AnalysisSummary(
                        total_conversations=0,
                        total_rule_violations=0,
                        conversations_with_drift=0,
                        conversations_without_drift=0,
                        rules_checked=[],
                        rules_passed=[],
                        rules_warned=[],
                        rules_failed=[],
                        rules_errored=[],
                        total_checks=0,
                        checks_passed=0,
                        checks_failed=0,
                        checks_warned=0,
                        checks_errored=0,
                    ),
                    results=[],
                )

            # Check provider availability before starting analysis
            # Determine which models will be needed
            models_needed = set()
            for type_name in types_to_check.keys():
                type_config = self.config.rule_definitions.get(type_name)
                type_model = getattr(type_config, "model", None) if type_config else None
                model_name = (
                    model_override or type_model or self.config.get_model_for_rule(type_name)
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
                        total_rule_violations=0,
                        conversations_with_drift=0,
                        conversations_without_drift=0,
                        rules_checked=[],
                        rules_passed=[],
                        rules_warned=[],
                        rules_failed=[],
                        rules_errored=[],
                        total_checks=0,
                        checks_passed=0,
                        checks_failed=0,
                        checks_warned=0,
                        checks_errored=0,
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
                    "rule_types": list(types_to_check.keys()),
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
        rule_types: Dict[str, Any],
        model_override: Optional[str],
    ) -> tuple[AnalysisResult, List[dict]]:
        """Analyze a single conversation using multi-pass approach.

        Args:
            conversation: Conversation to analyze
            rule_types: Rule types to check
            model_override: Optional model override

        Returns:
            Tuple of (AnalysisResult, execution_details)
        """
        all_rules: List[Rule] = []
        conversation_level_rules: Dict[str, Rule] = {}
        skipped_due_to_client: List[str] = []
        rule_errors: Dict[str, str] = {}
        execution_details: List[dict] = []  # Track all rule executions

        # Perform one pass per learning type
        for type_name, type_config in rule_types.items():
            # Client filtering: determine supported clients from validators or explicit config
            supported_clients = _get_supported_clients_from_rule(
                type_config, self.validator_registry, conversation.agent_tool
            )
            if supported_clients is not None and conversation.agent_tool not in supported_clients:
                skipped_due_to_client.append(type_name)
                continue

            rules, error, phase_results = self._run_analysis_pass(
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
                "status": "errored" if error else ("failed" if rules else "passed"),
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

                # Add resources_consulted if any rules have them
                if rules:
                    resources = rules[0].resources_consulted
                    if resources:
                        exec_detail["resources_consulted"] = resources

            execution_details.append(exec_detail)

            # Scope-based limiting for conversation-level rules
            scope = getattr(type_config, "scope", "turn_level")
            if scope == "conversation_level":
                # Only keep first learning for conversation-level types
                if rules and type_name not in conversation_level_rules:
                    conversation_level_rules[type_name] = rules[0]
            else:
                # Turn-level rules: keep all
                all_rules.extend(rules)

            # Save intermediate results
            self.temp_manager.save_pass_result(
                conversation.session_id,
                type_name,
                rules,
            )

        # Add conversation-level rules (max 1 per type)
        all_rules.extend(conversation_level_rules.values())

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
                rules=all_rules,
                analysis_timestamp=datetime.now(),
                error=None,
                rule_errors=rule_errors,
            ),
            execution_details,
        )

    def _run_analysis_pass(
        self,
        conversation: Conversation,
        rule_type: str,
        type_config: Any,
        model_override: Optional[str],
    ) -> tuple[List[Rule], Optional[str], Optional[List[PhaseAnalysisResult]]]:
        """Run a single analysis pass for one rule.

        Args:
            conversation: Conversation to analyze
            rule_type: Name of the rule
            type_config: Configuration for this rule
            model_override: Optional model override

        Returns:
            Tuple of (rules, error_message, phase_results).
            error_message is None if successful.
            phase_results is None for single-phase analysis,
            List[PhaseAnalysisResult] for multi-phase.
        """
        # Check if multi-phase (>1 phase) or single-phase (1 phase)
        phases = getattr(type_config, "phases", [])
        if len(phases) > 1:
            # Route to multi-phase analysis - returns phase_results
            return self._run_multi_phase_analysis(
                conversation, rule_type, type_config, model_override
            )

        # Determine which model to use (from phase)
        phase_model = phases[0].model if phases else None
        model_name = model_override or phase_model or self.config.get_model_for_rule(rule_type)

        provider = self.providers.get(model_name)
        if not provider:
            raise ValueError(f"Model '{model_name}' not found in configured providers")

        if not provider.is_available():
            raise RuntimeError(
                f"Provider for model '{model_name}' is not available. "
                "Check credentials and configuration."
            )

        # Build prompt for this rule
        prompt = self._build_analysis_prompt(conversation, rule_type, type_config)

        # Prepare cache parameters
        conversation_text = self._format_conversation(conversation)
        content_hash = ResponseCache.compute_content_hash(conversation_text)
        prompt_hash = ResponseCache.compute_content_hash(prompt)
        cache_key = f"{conversation.session_id}_{rule_type}"

        # Generate analysis
        logger.debug(f"Sending prompt to {model_name}:\n{prompt}")
        response = provider.generate(
            prompt,
            cache_key=cache_key,
            content_hash=content_hash,
            prompt_hash=prompt_hash,
            drift_type=rule_type,
        )
        logger.debug(f"Raw response from {model_name}:\n{response}")

        # Parse response to extract rules
        rules = self._parse_analysis_response(
            response,
            conversation,
            rule_type,
        )

        # Single-phase analysis - no phase_results to return
        return rules, None, None

    def _build_analysis_prompt(
        self,
        conversation: Conversation,
        rule_type: str,
        type_config: Any,
    ) -> str:
        """Build the prompt for analyzing a conversation.

        Args:
            conversation: Conversation to analyze
            rule_type: Name of the rule
            type_config: Configuration for this rule

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

**Drift Rule Type:** {rule_type}
**Description:** {description}

{project_context_section}**Detection Instructions:**
{detection_prompt}

**Conversation to Analyze:**
{conversation_text}

**Task:**
Analyze the above conversation and identify any instances of the "{rule_type}" drift pattern.

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

IMPORTANT: Return ONLY the raw JSON array. Do NOT wrap it in markdown code blocks (```json).
Do NOT add any explanatory text before or after the JSON. Your entire response should be parseable
as JSON."""

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

    def _parse_analysis_response(
        self,
        response: str,
        conversation: Conversation,
        rule_type: str,
    ) -> List[Rule]:
        """Parse LLM response to extract rules.

        Args:
            response: Raw LLM response
            conversation: Conversation that was analyzed
            rule_type: Type of learning

        Returns:
            List of Rule objects
        """
        import json
        import re

        # Extract JSON from response (in case there's extra text)
        json_match = re.search(r"\[.*\]", response, re.DOTALL)
        if not json_match:
            # No rules found
            return []

        try:
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse analysis response as JSON: {response[:200]}")
            return []

        rules = []
        for item in data:
            learning = Rule(
                turn_number=item.get("turn_number", 0),
                turn_uuid=None,  # Can be populated if we track UUIDs
                agent_tool=conversation.agent_tool,
                conversation_file=conversation.file_path,
                observed_behavior=item.get("observed_behavior", ""),
                expected_behavior=item.get("expected_behavior", ""),
                rule_type=rule_type,
                group_name=self._get_effective_group_name(rule_type),
                workflow_element=WorkflowElement.UNKNOWN,
                turns_to_resolve=1,
                context=item.get("context", ""),
                resources_consulted=[],
                phases_count=1,
                source_type="conversation",  # Mark as conversation-sourced learning
            )
            rules.append(learning)

        return rules

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
            total_rule_violations=0,
            conversations_with_drift=0,
            conversations_without_drift=0,
            total_checks=0,
            checks_passed=0,
            checks_failed=0,
            checks_warned=0,
            checks_errored=0,
        )

        # Count rules by type, group, and agent
        by_type: Dict[str, int] = {}
        by_group: Dict[str, int] = {}
        by_agent: Dict[str, int] = {}
        all_rule_errors: Dict[str, str] = {}

        for result in results:
            if result.rules:
                summary.conversations_with_drift += 1
            else:
                summary.conversations_without_drift += 1

            for learning in result.rules:
                summary.total_rule_violations += 1

                # By type
                by_type[learning.rule_type] = by_type.get(learning.rule_type, 0) + 1

                # By group
                group_name = learning.group_name or "General"
                by_group[group_name] = by_group.get(group_name, 0) + 1

                # By agent
                by_agent[learning.agent_tool] = by_agent.get(learning.agent_tool, 0) + 1

            # Collect rule errors
            for rule_name, error_msg in result.rule_errors.items():
                all_rule_errors[rule_name] = error_msg

        summary.by_type = by_type
        summary.by_group = by_group
        summary.by_agent = by_agent

        # Track which rules were checked, passed, warned, failed, and errored
        if types_checked:
            summary.rules_checked = list(types_checked.keys())
            summary.rules_errored = list(all_rule_errors.keys())  # Rules with errors
            summary.rule_errors = all_rule_errors

            # Separate warnings from failures based on severity
            rules_warned = []
            rules_failed = []

            for rule_type in by_type.keys():
                # Get severity for this rule
                severity = SeverityLevel.WARNING  # Default
                if rule_type in self.config.rule_definitions:
                    type_config = self.config.rule_definitions[rule_type]
                    if type_config.severity is not None:
                        severity = type_config.severity
                    elif type_config.scope == "project_level":
                        severity = SeverityLevel.FAIL
                    else:
                        severity = SeverityLevel.WARNING

                if severity == SeverityLevel.FAIL:
                    rules_failed.append(rule_type)
                elif severity == SeverityLevel.WARNING:
                    rules_warned.append(rule_type)
                # PASS shouldn't produce rules, but if it does, treat as warning

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
        rule_types: Optional[List[str]] = None,
        model_override: Optional[str] = None,
    ) -> CompleteAnalysisResult:
        """Run drift analysis on project documents.

        Args:
            rule_types: Optional list of specific rules to check
            model_override: Optional model to use (overrides all config settings)

        Returns:
            Complete analysis results with document rules
        """
        if not self.project_path:
            raise ValueError("Project path required for document analysis")

        all_types = (
            {lt: self.config.rule_definitions[lt] for lt in rule_types}
            if rule_types is not None
            else self.config.rule_definitions
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
            # Also include project-level rules with phases (programmatic or prompt)
            elif config.scope in ("project_level", "document_level"):
                phases = getattr(config, "phases", [])
                if phases:  # Include if there are ANY phases (programmatic or prompt)
                    document_types[name] = config

        if not document_types:
            return CompleteAnalysisResult(
                metadata={
                    "generated_at": datetime.now().isoformat(),
                    "execution_details": [],
                },
                summary=AnalysisSummary(
                    total_conversations=0,
                    total_rule_violations=0,
                    conversations_with_drift=0,
                    conversations_without_drift=0,
                    total_checks=0,
                    checks_passed=0,
                    checks_failed=0,
                    checks_warned=0,
                    checks_errored=0,
                ),
                results=[],
            )

        doc_loader = DocumentLoader(self.project_path)

        all_document_learnings: List[DocumentRule] = []
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
                registry = ValidatorRegistry()
                has_programmatic_phases = _has_programmatic_phases(phases, registry)
                has_validation_rules = getattr(type_config, "validation_rules", None) is not None
                has_any_phases = len(phases) > 0

                if bundle_config is None and not has_programmatic_phases and not has_any_phases:
                    logger.debug(
                        f"analyze_documents: {type_name} has no bundle_config and "
                        "no phases, skipping"
                    )
                    continue

                bundles = doc_loader.load_bundles(bundle_config) if bundle_config else []

                if not bundles:
                    if has_validation_rules or has_programmatic_phases or has_any_phases:
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
                        rules, exec_details = self._analyze_document_bundle(
                            empty_bundle, type_name, type_config, model_override, doc_loader
                        )
                        all_document_learnings.extend(rules)
                        all_execution_details.extend(exec_details)
                    continue

                # At this point bundle_config must exist (bundles were loaded from it)
                assert bundle_config is not None

                if bundle_config.bundle_strategy == BundleStrategy.INDIVIDUAL:
                    for bundle in bundles:
                        rules, exec_details = self._analyze_document_bundle(
                            bundle, type_name, type_config, model_override, doc_loader
                        )
                        all_document_learnings.extend(rules)
                        all_execution_details.extend(exec_details)
                else:
                    if bundles:
                        combined_bundle = self._combine_bundles(bundles, type_config)
                        rules, exec_details = self._analyze_document_bundle(
                            combined_bundle, type_name, type_config, model_override, doc_loader
                        )
                        if rules:
                            all_document_learnings.append(rules[0])
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
            # Map DocumentRule fields to Rule fields
            learning = Rule(
                turn_number=0,  # Document rules aren't tied to specific turns
                turn_uuid=None,
                agent_tool="documents",
                conversation_file="N/A",
                observed_behavior=doc_learning.observed_issue,
                expected_behavior=doc_learning.expected_quality,
                rule_type=doc_learning.rule_type,
                group_name=doc_learning.group_name,  # Transfer group name from DocumentRule
                workflow_element=WorkflowElement.UNKNOWN,
                turns_to_resolve=1,
                turns_involved=[],
                context=doc_learning.context,
                resources_consulted=[],
                phases_count=1,
                source_type="document",  # Mark as document-sourced learning
                affected_files=doc_learning.file_paths,  # Transfer file information
                bundle_id=doc_learning.bundle_id,  # Transfer bundle identifier
                phase_name=doc_learning.phase_name,  # Transfer phase name if present
            )
            converted_learnings.append(learning)

        result = AnalysisResult(
            session_id="document_analysis",
            agent_tool="documents",
            conversation_file="N/A",
            project_path=str(self.project_path),
            rules=converted_learnings,
            analysis_timestamp=datetime.now(),
            error=None,
        )

        summary = AnalysisSummary(
            total_conversations=0,
            total_rule_violations=len(all_document_learnings),
            conversations_with_drift=0,
            conversations_without_drift=0,
            total_checks=0,
            checks_passed=0,
            checks_failed=0,
            checks_warned=0,
            checks_errored=0,
        )

        by_type: Dict[str, int] = {}
        by_group: Dict[str, int] = {}

        # Build by_type and by_group from execution_details (captures ALL checks)
        # execution_details has rule_name which corresponds to the rule definition key
        for ed in all_execution_details:
            rule_name = ed.get("rule_name")
            if rule_name and rule_name in self.config.rule_definitions:
                # Count by type (rule_name is the rule type)
                by_type[rule_name] = by_type.get(rule_name, 0) + 1

                # Count by group
                rule_def = self.config.rule_definitions[rule_name]
                group_name = rule_def.group_name or "General"
                by_group[group_name] = by_group.get(group_name, 0) + 1

        # Also include document_learnings for rules that only produce failures
        # (to ensure we don't miss any rule types)
        for doc_learning in all_document_learnings:
            # Only add if not already counted from execution_details
            if doc_learning.rule_type not in by_type:
                by_type[doc_learning.rule_type] = by_type.get(doc_learning.rule_type, 0) + 1
                group_name = doc_learning.group_name or "General"
                by_group[group_name] = by_group.get(group_name, 0) + 1

        summary.by_type = by_type
        summary.by_group = by_group

        summary.rules_checked = list(document_types.keys())

        # Count individual checks from execution_details
        summary.total_checks = len(all_execution_details)
        summary.checks_passed = sum(
            1 for ed in all_execution_details if ed.get("status") == "passed"
        )
        summary.checks_errored = sum(
            1 for ed in all_execution_details if ed.get("status") == "errored"
        )

        # Separate warnings from failures based on severity
        # Build set of rule_types that actually had failures
        failed_rule_types = set()
        for doc_learning in all_document_learnings:
            failed_rule_types.add(doc_learning.rule_type)

        # Also check execution_details for failed status
        for ed in all_execution_details:
            if ed.get("status") == "failed":
                rule_name = ed.get("rule_name")
                if rule_name:
                    failed_rule_types.add(rule_name)

        # Build severity map only for rules that actually failed
        rule_severity_map = {}
        for rule_type in failed_rule_types:
            severity = SeverityLevel.WARNING  # Default
            if rule_type in self.config.rule_definitions:
                type_config = self.config.rule_definitions[rule_type]
                if type_config.severity is not None:
                    severity = type_config.severity
                elif type_config.scope == "project_level":
                    severity = SeverityLevel.FAIL
                else:
                    severity = SeverityLevel.WARNING
            rule_severity_map[rule_type] = severity

        # Categorize rules by severity (only for failed rules)
        rules_warned = [rt for rt, sev in rule_severity_map.items() if sev == SeverityLevel.WARNING]
        rules_failed = [rt for rt, sev in rule_severity_map.items() if sev == SeverityLevel.FAIL]

        summary.rules_warned = rules_warned
        summary.rules_failed = rules_failed
        summary.rules_passed = [
            rule
            for rule in summary.rules_checked
            if rule not in rules_warned and rule not in rules_failed
        ]

        # Calculate checks_failed and checks_warned from execution_details based on severity
        # Each execution_detail has a rule_name field - categorize by severity
        checks_failed_count = 0
        checks_warned_count = 0
        for ed in all_execution_details:
            if ed.get("status") == "failed":
                rule_name = ed.get("rule_name")
                if rule_name and rule_severity_map.get(rule_name) == SeverityLevel.FAIL:
                    checks_failed_count += 1
                elif rule_name and rule_severity_map.get(rule_name) == SeverityLevel.WARNING:
                    checks_warned_count += 1
        summary.checks_failed = checks_failed_count
        summary.checks_warned = checks_warned_count

        logger.info(f"analyze_documents: Returning {len(all_execution_details)} execution details")
        logger.debug(f"analyze_documents: execution_details = {all_execution_details}")

        return CompleteAnalysisResult(
            metadata={
                "generated_at": datetime.now().isoformat(),
                "analysis_type": "documents",
                "project_path": str(self.project_path),
                "document_rules": [learning.model_dump() for learning in all_document_learnings],
                "execution_details": all_execution_details,
            },
            summary=summary,
            results=[result] if all_document_learnings else [],
        )

    def _analyze_document_bundle(
        self,
        bundle: DocumentBundle,
        rule_type: str,
        type_config: Any,
        model_override: Optional[str],
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentRule], List[dict]]:
        """Analyze a single document bundle.

        Args:
            bundle: Document bundle to analyze
            rule_type: Name of learning type
            type_config: Configuration for this rule
            model_override: Optional model override
            loader: Optional document loader for resource access

        Returns:
            Tuple of (rules, execution_details)
        """
        validation_rules = getattr(type_config, "validation_rules", None)
        logger.debug(
            f"_analyze_document_bundle for {rule_type}: validation_rules={validation_rules}"
        )

        if validation_rules is not None:
            logger.debug(
                f"_analyze_document_bundle: Calling _execute_validation_rules for {rule_type}"
            )
            return self._execute_validation_rules(bundle, rule_type, type_config, loader)

        phases = getattr(type_config, "phases", [])

        if phases:
            # Execute phases sequentially: programmatic first, then prompt-based
            # Stop on first failure
            registry = ValidatorRegistry(loader)
            all_rules = []
            all_execution_details = []

            for phase_idx, phase in enumerate(phases):
                phase_type = getattr(phase, "type", "prompt")

                # Execute programmatic phase
                if phase_type != "prompt":
                    try:
                        if not registry.is_programmatic(phase_type):
                            # Unknown type - skip
                            continue
                    except (ValueError, KeyError):
                        # Unknown type - skip
                        continue

                    # Merge legacy phase fields into params for backward compatibility
                    phase_params = dict(phase.params) if phase.params else {}
                    if phase.file_path and "file_path" not in phase_params:
                        phase_params["file_path"] = phase.file_path

                    rule = ValidationRule(  # type: ignore[call-arg]
                        rule_type=phase.type,
                        description=type_config.description,
                        params=phase_params,
                        file_path=phase.file_path,
                        failure_message=phase.failure_message,
                        expected_behavior=phase.expected_behavior,
                    )

                    result = registry.execute_rule(rule, bundle)

                    # Track execution
                    exec_info = {
                        "rule_name": rule_type,
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
                    all_execution_details.append(exec_info)

                    if result is not None:
                        result.rule_type = rule_type
                        # Add phase name if rule has multiple phases
                        if len(phases) > 1:
                            phase_name = getattr(phase, "name", f"phase_{phase_idx + 1}")
                            result.phase_name = phase_name
                        all_rules.append(result)
                        # Stop on failure
                        return all_rules, all_execution_details

                # Execute prompt-based phase
                else:
                    prompt = self._build_document_analysis_prompt(bundle, rule_type, type_config)

                    phase_model = phase.model if hasattr(phase, "model") else None
                    model_name = (
                        model_override or phase_model or self.config.get_model_for_rule(rule_type)
                    )

                    provider = self.providers.get(model_name)
                    if not provider:
                        raise ValueError(f"Model '{model_name}' not found in configured providers")

                    # Prepare cache parameters
                    doc_loader = DocumentLoader(bundle.project_path)
                    bundle_content = doc_loader.format_bundle_for_llm(bundle)
                    content_hash = ResponseCache.compute_content_hash(bundle_content)
                    prompt_hash = ResponseCache.compute_content_hash(prompt)
                    cache_key = f"{bundle.bundle_id}_{rule_type}_phase{phase_idx}"

                    logger.debug(f"Sending prompt (phase {phase_idx+1}) to {model_name}:\n{prompt}")
                    response = provider.generate(
                        prompt,
                        cache_key=cache_key,
                        content_hash=content_hash,
                        prompt_hash=prompt_hash,
                        drift_type=rule_type,
                    )
                    logger.debug(f"Raw response from {model_name}:\n{response}")

                    rules = self._parse_document_analysis_response(response, bundle, rule_type)

                    # Track execution
                    exec_info = {
                        "rule_name": rule_type,
                        "rule_description": type_config.description,
                        "rule_context": type_config.context,
                        "status": "passed" if not rules else "failed",
                        "execution_context": {
                            "bundle_id": bundle.bundle_id,
                            "bundle_type": bundle.bundle_type,
                            "files": [f.relative_path for f in bundle.files],
                        },
                        "validation_results": {
                            "rule_type": "llm_analysis",
                            "params": {},
                        },
                    }
                    all_execution_details.append(exec_info)

                    if rules:
                        # Add phase name if rule has multiple phases
                        if len(phases) > 1:
                            phase_name = getattr(phase, "name", f"phase_{phase_idx + 1}")
                            for doc_rule in rules:
                                doc_rule.phase_name = phase_name
                        all_rules.extend(rules)
                        # Stop on failure
                        return all_rules, all_execution_details

            # All phases passed
            return all_rules, all_execution_details

        # No phases configured - shouldn't happen but handle gracefully
        return [], []

    def _run_multi_phase_document_analysis(
        self,
        bundle: DocumentBundle,
        rule_type: str,
        type_config: Any,
        model_override: Optional[str] = None,
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentRule], List[dict]]:
        """Run multi-phase analysis on a document bundle."""
        phases = getattr(type_config, "phases", [])
        if not phases:
            raise ValueError(
                f"Rule type '{rule_type}' routed to multi-phase analysis "
                "but no phases configured"
            )

        # For documents, we just run single-phase for now with the first phase
        # Multi-phase with resource requests doesn't make sense for static documents
        phase_model = phases[0].model if phases else None
        model_name = model_override or phase_model or self.config.get_model_for_rule(rule_type)

        provider = self.providers.get(model_name)
        if not provider:
            raise ValueError(f"Model '{model_name}' not found in configured providers")

        prompt = self._build_document_analysis_prompt(bundle, rule_type, type_config)

        # Prepare cache parameters for document analysis
        doc_loader = DocumentLoader(bundle.project_path)
        bundle_content = doc_loader.format_bundle_for_llm(bundle)
        content_hash = ResponseCache.compute_content_hash(bundle_content)
        prompt_hash = ResponseCache.compute_content_hash(prompt)
        cache_key = f"{bundle.bundle_id}_{rule_type}"

        logger.debug(f"Sending prompt to {model_name}:\n{prompt}")
        response = provider.generate(
            prompt,
            cache_key=cache_key,
            content_hash=content_hash,
            prompt_hash=prompt_hash,
            drift_type=rule_type,
        )
        logger.debug(f"Raw response from {model_name}:\n{response}")
        rules = self._parse_document_analysis_response(response, bundle, rule_type)

        # Track execution details for multi-phase LLM-based document analysis
        exec_info = {
            "rule_name": rule_type,
            "rule_description": type_config.description,
            "rule_context": type_config.context,
            "status": "passed" if not rules else "failed",
            "execution_context": {
                "bundle_id": bundle.bundle_id,
                "bundle_type": bundle.bundle_type,
                "files": [f.relative_path for f in bundle.files],
            },
            "validation_results": {
                "rule_type": "llm_analysis_multi_phase",
                "params": {},
            },
        }

        return rules, [exec_info]

    def _execute_validation_rules(
        self,
        bundle: DocumentBundle,
        rule_type: str,
        type_config: Any,
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentRule], List[dict]]:
        """Execute rule-based validation on a bundle.

        Routes to parallel or sequential execution based on rule count and config.
        Single rules use sequential execution to avoid async overhead.

        Args:
            bundle: Document bundle to validate
            rule_type: Name of learning type
            type_config: Configuration for this rule
            loader: Optional document loader for resource access

        Returns:
            Tuple of (rules, execution_details).
            rules: List of document rules from failed validations
            execution_details: List of dicts with execution info for ALL rules
        """
        logger.debug(f"_execute_validation_rules called for {rule_type}")
        validation_config = getattr(type_config, "validation_rules", None)
        if not validation_config:
            raise ValueError(
                f"Rule type '{rule_type}' routed to programmatic validation "
                "but no validation_rules configured"
            )

        # Determine if we should use parallel execution
        parallel_enabled = self.config.parallel_execution.enabled
        num_rules = len(validation_config.rules)

        # Use parallel execution if enabled and more than one rule
        if parallel_enabled and num_rules > 1:
            logger.debug(f"Using parallel execution for {num_rules} rules")
            return asyncio.run(
                self._execute_rules_parallel(validation_config.rules, bundle, rule_type, loader)
            )
        else:
            logger.debug(f"Using sequential execution for {num_rules} rules")
            return self._execute_rules_sequential(
                validation_config.rules, bundle, rule_type, loader
            )

    def _execute_rules_sequential(
        self,
        rules: List[ValidationRule],
        bundle: DocumentBundle,
        rule_type: str,
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentRule], List[dict]]:
        """Execute validation rules sequentially.

        Args:
            rules: List of validation rules to execute
            bundle: Document bundle to validate
            rule_type: Name of learning type
            loader: Optional document loader for resource access

        Returns:
            Tuple of (rules, execution_details).
        """
        registry = ValidatorRegistry(loader)
        doc_rules = []
        execution_details = []

        logger.debug(f"_execute_rules_sequential: Processing {len(rules)} rules for {rule_type}")

        for rule in rules:
            try:
                logger.debug(f"_execute_rules_sequential: Executing rule {rule.description}")
                result = registry.execute_rule(rule, bundle)
                logger.debug(f"_execute_rules_sequential: Rule result: {result}")

                # Track execution info for this rule
                exec_info = {
                    "rule_name": rule_type,
                    "rule_description": rule.description,
                    "status": "passed" if result is None else "failed",
                    "execution_context": {
                        "bundle_id": bundle.bundle_id,
                        "bundle_type": bundle.bundle_type,
                        "files": [f.relative_path for f in bundle.files],
                    },
                    "validation_results": {
                        "rule_type": rule.rule_type,
                        "params": rule.params if hasattr(rule, "params") else {},
                    },
                }
                execution_details.append(exec_info)

                if result is not None:
                    # Validation failed - set the learning type name
                    result.rule_type = rule_type
                    doc_rules.append(result)

            except Exception as e:
                # Log error but continue with other rules
                logger.warning(f"Validation rule '{rule.description}' failed: {e}")

                # Track error in execution details
                exec_info = {
                    "rule_name": rule_type,
                    "rule_description": rule.description,
                    "status": "errored",
                    "error_message": str(e),
                }
                execution_details.append(exec_info)
                continue

        return doc_rules, execution_details

    async def _execute_rules_parallel(
        self,
        rules: List[ValidationRule],
        bundle: DocumentBundle,
        rule_type: str,
        loader: Optional[Any] = None,
    ) -> tuple[List[DocumentRule], List[dict]]:
        """Execute validation rules in parallel using asyncio.

        Uses asyncio.gather() with return_exceptions=True so individual
        rule failures don't stop other rules from executing.

        Args:
            rules: List of validation rules to execute
            bundle: Document bundle to validate
            rule_type: Name of learning type
            loader: Optional document loader for resource access

        Returns:
            Tuple of (rules, execution_details).
            rules: List of DocumentRule objects from failed validations
            execution_details: List of dicts with execution info for all rules
        """
        logger.debug(f"_execute_rules_parallel: Processing {len(rules)} rules for {rule_type}")

        # Create tasks for all rules
        tasks = [self._execute_single_rule_async(rule, bundle, rule_type, loader) for rule in rules]

        # Execute all rules concurrently, collecting exceptions
        results: list[Any] = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        doc_rules = []
        execution_details = []

        for result_item in results:
            if isinstance(result_item, Exception):
                # Task raised an exception
                logger.error(f"Rule execution raised exception: {result_item}")
                exec_info = {
                    "rule_name": rule_type,
                    "rule_description": "Unknown rule",
                    "status": "errored",
                    "error_message": str(result_item),
                }
                execution_details.append(exec_info)
            else:
                # Unpack the result tuple
                doc_rule, exec_info = result_item
                execution_details.append(exec_info)
                if doc_rule is not None:
                    doc_rules.append(doc_rule)

        return doc_rules, execution_details

    async def _execute_single_rule_async(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        rule_type: str,
        loader: Optional[Any] = None,
    ) -> tuple[Optional[DocumentRule], dict]:
        """Execute a single validation rule asynchronously.

        Uses asyncio.to_thread() to offload synchronous file I/O to a thread pool.

        Args:
            rule: Validation rule to execute
            bundle: Document bundle to validate
            rule_type: Name of learning type
            loader: Optional document loader for resource access

        Returns:
            Tuple of (document_rule, execution_info).
            document_rule is None if validation passed, otherwise contains failure info.
        """
        try:
            # Create a new registry for this task to avoid sharing state
            registry = ValidatorRegistry(loader)

            # Execute rule in thread pool (file I/O is synchronous)
            logger.debug(f"_execute_single_rule_async: Executing rule {rule.description}")
            result = await asyncio.to_thread(registry.execute_rule, rule, bundle)
            logger.debug(f"_execute_single_rule_async: Rule result: {result}")

            # Build execution info
            exec_info = {
                "rule_name": rule_type,
                "rule_description": rule.description,
                "status": "passed" if result is None else "failed",
                "execution_context": {
                    "bundle_id": bundle.bundle_id,
                    "bundle_type": bundle.bundle_type,
                    "files": [f.relative_path for f in bundle.files],
                },
                "validation_results": {
                    "rule_type": rule.rule_type,
                    "params": rule.params if hasattr(rule, "params") else {},
                },
            }

            # Set the learning type name if validation failed
            if result is not None:
                result.rule_type = rule_type

            return result, exec_info

        except Exception as e:
            # Log error and return error info
            logger.warning(f"Validation rule '{rule.description}' failed: {e}")

            exec_info = {
                "rule_name": rule_type,
                "rule_description": rule.description,
                "status": "errored",
                "error_message": str(e),
            }

            return None, exec_info

    def _build_document_analysis_prompt(
        self,
        bundle: DocumentBundle,
        rule_type: str,
        type_config: Any,
    ) -> str:
        """Build prompt for document analysis.

        Args:
            bundle: Document bundle to analyze
            rule_type: Name of learning type
            type_config: Configuration for this rule

        Returns:
            Formatted prompt string
        """
        description = getattr(type_config, "description", "")
        phases = getattr(type_config, "phases", [])

        # Find first phase with a prompt (skip core phases that have no prompt)
        detection_prompt = ""
        for phase in phases:
            if hasattr(phase, "prompt") and phase.prompt:
                detection_prompt = phase.prompt
                break

        # Format bundle content
        doc_loader = DocumentLoader(bundle.project_path)
        formatted_files = doc_loader.format_bundle_for_llm(bundle)

        # Build prompt with template variable substitution
        prompt = f"""**Analysis Type:** {rule_type}
**Bundle Type:** {bundle.bundle_type}
**Description:** {description}

**Files Being Analyzed:**
{formatted_files}

**Your Task:**
{detection_prompt}

**CRITICAL:**
- Follow the task instructions EXACTLY.
- If the task says "Check ONLY X", check ONLY X.
- If the task lists things as "OUT OF SCOPE" or "NOT YOUR JOB", completely ignore those things.
- Do NOT mention or report anything marked as out of scope, even if you notice issues.

**Important Examples:**
- If task says "NOT YOUR JOB: Resource file links", and you see broken resource links, return []
- If task says "NOT YOUR JOB: Duplicate files", and you see duplicates, return []
- If task says "NOT YOUR JOB: MCP tool references", and you see MCP issues, return []

**Output Format:**
Return a JSON array with ONLY issues that match your specific task scope:

[{{
    "file_paths": ["file.md"],
    "observed_issue": "issue",
    "expected_quality": "expected",
    "context": "explanation"
}}]

If NO issues match your task scope (or if you only find out-of-scope issues), return: []

IMPORTANT: Return ONLY the raw JSON array. Do NOT wrap it in markdown code blocks (```json).
Do NOT add any explanatory text before or after the JSON. Your entire response should be parseable
as JSON."""

        return prompt

    def _parse_document_analysis_response(
        self,
        response: str,
        bundle: DocumentBundle,
        rule_type: str,
    ) -> List[DocumentRule]:
        """Parse document analysis response from LLM.

        Args:
            response: Raw response from LLM
            bundle: Document bundle that was analyzed
            rule_type: Type of learning

        Returns:
            List of parsed document rules
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

        # Filter out common false positives that should be handled by other phases
        false_positive_patterns = [
            # Resource file checks (handled by core:file_exists phases)
            r"resource file.*not.*exist",
            r"resource file.*reference",
            r"resource link",
            r"resources?/.*\.md",
            # Duplicate file checks (handled by core:file_exists phases)
            r"duplicate.*file",
            r"SKILL\.md and skill\.md",
            r"identical content",
            # MCP tool checks (validated by other phases)
            r"mcp__\w+__",
            r"mcp tool",
            # Out of scope items
            r"project-specific context",
            r"documentation completeness",
            # Technical accuracy (not structural quality)
            r"deprecated.*parameter",
            r"model.*version",
            r"outdated.*model",
            r"current model",
            r"undefined.*script",
            r"references.*script",
            r"\.sh\b",  # Script references
            r"model_id.*format",
            r"anthropic\.claude",
            # Skills/tools relationship (skills don't need Skill tool)
            r"skills.*tools list",
            r"skill tool.*invoking",
            r"tools list.*doesn't include.*skill",
            r"access to the skill tool",
            # Attribution/footer complaints
            r"co-authored-by",
            r"noreply@anthropic",
            r"footer attribution",
            r"attribution.*format",
            r"generated with.*claude code",
        ]

        # Convert to DocumentRule objects
        rules = []
        for item in items:
            if not isinstance(item, dict):
                continue

            observed = item.get("observed_issue", "")
            expected = item.get("expected_quality", "")
            context = item.get("context", "")

            # Check all text fields for false positive patterns
            all_text = f"{observed} {expected} {context}".lower()

            # Skip if matches any false positive pattern
            is_false_positive = any(
                re.search(pattern, all_text, re.IGNORECASE) for pattern in false_positive_patterns
            )

            if is_false_positive:
                continue

            learning = DocumentRule(
                bundle_id=bundle.bundle_id,
                bundle_type=bundle.bundle_type,
                file_paths=item.get("file_paths", []),
                observed_issue=item.get("observed_issue", ""),
                expected_quality=item.get("expected_quality", ""),
                rule_type=rule_type,
                group_name=self._get_effective_group_name(rule_type),
                context=item.get("context", ""),
            )
            rules.append(learning)

        # ENFORCE: Return only first learning (ONE per rule)
        # This ensures each rule returns exactly one learning, regardless of what LLM returns
        return rules[:1] if rules else []

    def _combine_bundles(
        self,
        bundles: List[DocumentBundle],
        type_config: Any,
    ) -> DocumentBundle:
        """Combine multiple bundles into a single mega-bundle for project-level analysis.

        Args:
            bundles: List of bundles to combine
            type_config: Rule type configuration

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
        rule_type: str,
        type_config: Any,
        model_override: Optional[str],
    ) -> tuple[List[Rule], Optional[str], List[PhaseAnalysisResult]]:
        """Execute multi-phase analysis with resource requests.

        Returns:
            Tuple of (rules, error_message, phase_results).
            error_message is None if successful.
            phase_results contains all PhaseAnalysisResult objects from execution.
        """
        # Get phases from config
        phases = getattr(type_config, "phases", [])
        if not phases:
            raise ValueError(
                f"Rule type '{rule_type}' routed to multi-phase analysis "
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

        logger.info(f"Starting multi-phase analysis for {rule_type} with {len(phases)} phase(s)")

        # Phase 1: Initial analysis
        phase_idx = 0
        phase_def = phases[phase_idx]
        logger.info(f"Starting phase {phase_idx + 1}: {phase_def.name}")
        prompt = self._build_multi_phase_prompt(
            conversation=conversation,
            rule_type=rule_type,
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
            model_name = model_override or phase_model or self.config.get_model_for_rule(rule_type)

            provider = self.providers.get(model_name)
            if not provider:
                raise ValueError(f"Model '{model_name}' not found in configured providers")

            if not provider.is_available():
                raise RuntimeError(
                    f"Provider for model '{model_name}' is not available. "
                    "Check credentials and configuration."
                )

            # Prepare cache parameters for multi-phase analysis
            conversation_text = self._format_conversation(conversation)
            content_hash = ResponseCache.compute_content_hash(conversation_text)
            prompt_hash = ResponseCache.compute_content_hash(prompt)
            cache_key = f"{conversation.session_id}_{rule_type}_phase{phase_idx + 1}"

            # Call LLM
            logger.debug(f"Sending phase {phase_idx + 1} prompt to {model_name}:\n{prompt}")
            response = provider.generate(
                prompt,
                cache_key=cache_key,
                content_hash=content_hash,
                prompt_hash=prompt_hash,
                drift_type=rule_type,
            )
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
                # All resources missing - create missing resource rules
                return self._create_missing_resource_learnings(
                    conversation=conversation,
                    rule_type=rule_type,
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
                    rule_type=rule_type,
                    type_config=type_config,
                    phase_idx=phase_idx,
                    phase_def=phase_def,
                    resources_loaded=resources_loaded,
                    previous_findings=phase_result.findings,
                )

        # Finalize rules from all phases
        rules, error = self._finalize_multi_phase_learnings(
            conversation=conversation,
            rule_type=rule_type,
            phase_results=phase_results,
            resources_consulted=resources_consulted,
        )

        # Return rules, error, AND phase_results (stop throwing them away!)
        return rules, error, phase_results

    def _build_multi_phase_prompt(
        self,
        conversation: Conversation,
        rule_type: str,
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

**Analysis Type**: {rule_type}
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
                f"for drift pattern: {rule_type}"
            )
            prompt = f"""{prompt_prefix}

**Analysis Type**: {rule_type}
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
        rule_type: str,
        resources_loaded: List[ResourceResponse],
        phase_results: List[PhaseAnalysisResult],
    ) -> tuple[List[Rule], Optional[str], List[PhaseAnalysisResult]]:
        """Create rules when requested resources are missing.

        Returns:
            Tuple of (rules, error_message). Always returns None for error since
            missing resources are valid rules, not errors.
        """
        rules = []

        for resource in resources_loaded:
            if not resource.found:
                # Missing resource IS the drift
                missing_rule_type = f"missing_{resource.request.resource_type}"
                learning = Rule(
                    turn_number=0,  # Not turn-specific
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
                    rule_type=missing_rule_type,
                    group_name=self._get_effective_group_name(missing_rule_type),
                    workflow_element=WorkflowElement.UNKNOWN,
                    turns_to_resolve=1,
                    turns_involved=[],
                    context=resource.request.reason,
                    resources_consulted=[
                        f"{resource.request.resource_type}:{resource.request.resource_id}"
                    ],
                    phases_count=len(phase_results),
                    source_type="resource_missing",  # Mark as resource-missing learning
                )
                rules.append(learning)

        return rules, None, phase_results

    def _finalize_multi_phase_learnings(
        self,
        conversation: Conversation,
        rule_type: str,
        phase_results: List[PhaseAnalysisResult],
        resources_consulted: List[str],
    ) -> tuple[List[Rule], Optional[str]]:
        """Convert final phase results to Rule objects.

        Returns:
            Tuple of (rules, error_message). error_message is set if findings are malformed.
        """
        # Get final findings (last phase)
        final_phase = phase_results[-1]

        rules = []
        malformed_count = 0

        # ENFORCE: Only process first VALID finding (ONE per rule)
        # This ensures each rule returns exactly one learning, regardless of what LLM returns
        # We find the first valid finding to handle cases where LLM returns malformed data first
        for finding in final_phase.findings:
            # Validate that finding has required fields
            observed = finding.get("observed_behavior", "").strip()
            expected = finding.get("expected_behavior", "").strip()

            # Track malformed findings
            if not observed or not expected:
                malformed_count += 1
                continue

            # Found first valid finding - create learning and stop
            learning = Rule(
                turn_number=finding.get("turn_number", 0),
                turn_uuid=None,
                agent_tool=conversation.agent_tool,
                conversation_file=conversation.file_path,
                observed_behavior=observed,
                expected_behavior=expected,
                rule_type=rule_type,
                group_name=self._get_effective_group_name(rule_type),
                workflow_element=WorkflowElement.UNKNOWN,
                turns_to_resolve=1,
                turns_involved=[],
                context=finding.get("context", ""),
                resources_consulted=resources_consulted,
                phases_count=len(phase_results),
                source_type="conversation",  # Mark as conversation-sourced learning
            )
            rules.append(learning)
            break  # ENFORCE: Only one learning per rule

        # Return error if we had malformed findings
        error = None
        if malformed_count > 0:
            error = (
                f"Multi-phase analysis returned {malformed_count} malformed finding(s) "
                f"with missing observed_behavior or expected_behavior fields"
            )

        return rules, error

    def cleanup(self) -> None:
        """Clean up temporary files."""
        self.temp_manager.cleanup()
