"""Main analysis orchestration for drift detection."""

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from drift.agents.base import AgentLoader
from drift.agents.claude_code import ClaudeCodeLoader
from drift.config.loader import ConfigLoader
from drift.config.models import DriftConfig, ProviderType
from drift.core.types import (
    AnalysisResult,
    AnalysisSummary,
    CompleteAnalysisResult,
    Conversation,
    DocumentBundle,
    DocumentLearning,
    FrequencyType,
    Learning,
    WorkflowElement,
)
from drift.documents.loader import DocumentLoader
from drift.providers.base import Provider
from drift.providers.bedrock import BedrockProvider
from drift.utils.temp import TempManager


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
            types_to_check = (
                {lt: self.config.drift_learning_types[lt] for lt in learning_types}
                if learning_types
                else self.config.drift_learning_types
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
                    # Re-raise with helpful message
                    raise FileNotFoundError(str(e))
                except Exception as e:
                    print(f"Warning: Failed to load conversations from {tool_name}: {e}")
                    continue

            # Analyze each conversation
            results: List[AnalysisResult] = []
            for conversation in all_conversations:
                try:
                    result = self._analyze_conversation(
                        conversation,
                        types_to_check,
                        model_override,
                    )
                    results.append(result)
                except Exception as e:
                    # Log error but continue with other conversations
                    print(f"Warning: Failed to analyze conversation {conversation.session_id}: {e}")
                    continue

            # Generate summary
            summary = self._generate_summary(results)

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
    ) -> AnalysisResult:
        """Analyze a single conversation using multi-pass approach.

        Args:
            conversation: Conversation to analyze
            learning_types: Learning types to check
            model_override: Optional model override

        Returns:
            Analysis result for this conversation
        """
        all_learnings: List[Learning] = []
        conversation_level_learnings: Dict[str, Learning] = {}

        # Perform one pass per learning type
        for type_name, type_config in learning_types.items():
            # Client filtering: skip if rule doesn't support this agent_tool
            supported_clients = getattr(type_config, "supported_clients", None)
            if supported_clients is not None and conversation.agent_tool not in supported_clients:
                continue

            learnings = self._run_analysis_pass(
                conversation,
                type_name,
                type_config,
                model_override,
            )

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

        return AnalysisResult(
            session_id=conversation.session_id,
            agent_tool=conversation.agent_tool,
            conversation_file=conversation.file_path,
            project_path=conversation.project_path,
            learnings=all_learnings,
            analysis_timestamp=datetime.now(),
            error=None,
        )

    def _run_analysis_pass(
        self,
        conversation: Conversation,
        learning_type: str,
        type_config: Any,
        model_override: Optional[str],
    ) -> List[Learning]:
        """Run a single analysis pass for one learning type.

        Args:
            conversation: Conversation to analyze
            learning_type: Name of the learning type
            type_config: Configuration for this learning type
            model_override: Optional model override

        Returns:
            List of learnings found
        """
        # Determine which model to use
        type_config_model = getattr(type_config, "model", None)
        model_name = (
            model_override
            or type_config_model
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

        # Build prompt for this learning type
        prompt = self._build_analysis_prompt(conversation, learning_type, type_config)

        # Generate analysis
        response = provider.generate(prompt)

        # Parse response to extract learnings
        learnings = self._parse_analysis_response(
            response,
            conversation,
            learning_type,
        )

        return learnings

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
        detection_prompt = getattr(type_config, "detection_prompt", "")
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
            print(f"Warning: Failed to parse analysis response as JSON: {response[:200]}")
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
            )
            learnings.append(learning)

        return learnings

    @staticmethod
    def _generate_summary(results: List[AnalysisResult]) -> AnalysisSummary:
        """Generate summary statistics from analysis results.

        Args:
            results: List of analysis results

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

        summary.by_type = by_type
        summary.by_agent = by_agent
        summary.by_frequency = by_frequency

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

        # Filter to learning types that have document_bundle config
        all_types = (
            {lt: self.config.drift_learning_types[lt] for lt in learning_types}
            if learning_types
            else self.config.drift_learning_types
        )

        # Only keep types with document_bundle configuration
        document_types = {
            name: config
            for name, config in all_types.items()
            if hasattr(config, "document_bundle") and config.document_bundle is not None
        }

        if not document_types:
            # No document learning types configured
            return CompleteAnalysisResult(
                metadata={"generated_at": datetime.now().isoformat()},
                summary=AnalysisSummary(),
                results=[],
            )

        # Initialize document loader
        doc_loader = DocumentLoader(self.project_path)

        # Analyze each document learning type
        all_document_learnings: List[DocumentLearning] = []

        for type_name, type_config in document_types.items():
            try:
                # Load bundles for this type
                bundles = doc_loader.load_bundles(type_config.document_bundle)

                if not bundles:
                    continue

                # Handle scope-based analysis
                scope = getattr(type_config, "scope", "document_level")

                if scope == "document_level":
                    # Analyze each bundle independently
                    for bundle in bundles:
                        learnings = self._analyze_document_bundle(
                            bundle, type_name, type_config, model_override
                        )
                        all_document_learnings.extend(learnings)

                elif scope == "project_level":
                    # Combine all bundles for cross-document analysis
                    if bundles:
                        combined_bundle = self._combine_bundles(bundles, type_config)
                        learnings = self._analyze_document_bundle(
                            combined_bundle, type_name, type_config, model_override
                        )
                        # Limit to 1 per type for project-level
                        if learnings:
                            all_document_learnings.append(learnings[0])

            except Exception as e:
                print(f"Warning: Failed to analyze documents for {type_name}: {e}")
                continue

        # Convert document learnings to AnalysisResult format for compatibility
        # For now, create a synthetic result
        result = AnalysisResult(
            session_id="document_analysis",
            agent_tool="documents",
            conversation_file="N/A",
            project_path=str(self.project_path),
            learnings=[],  # Document learnings are separate
            analysis_timestamp=datetime.now(),
        )

        # Generate summary (adapt for document learnings)
        summary = AnalysisSummary(
            total_conversations=0,
            total_learnings=len(all_document_learnings),
            conversations_with_drift=0,
            conversations_without_drift=0,
        )

        # Count by type
        by_type: Dict[str, int] = {}
        for learning in all_document_learnings:
            by_type[learning.learning_type] = by_type.get(learning.learning_type, 0) + 1
        summary.by_type = by_type

        return CompleteAnalysisResult(
            metadata={
                "generated_at": datetime.now().isoformat(),
                "analysis_type": "documents",
                "project_path": str(self.project_path),
                "document_learnings": [
                    learning.model_dump() for learning in all_document_learnings
                ],
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
    ) -> List[DocumentLearning]:
        """Analyze a single document bundle.

        Args:
            bundle: Document bundle to analyze
            learning_type: Name of learning type
            type_config: Configuration for this learning type
            model_override: Optional model override

        Returns:
            List of document learnings found
        """
        # Build prompt
        prompt = self._build_document_analysis_prompt(bundle, learning_type, type_config)

        # Determine model to use
        model_name = (
            model_override
            or (type_config.model if hasattr(type_config, "model") else None)
            or self.config.get_model_for_learning_type(learning_type)
        )

        # Get provider
        provider = self.providers.get(model_name)
        if not provider:
            raise ValueError(f"Model '{model_name}' not found in configured providers")

        # Generate analysis
        response = provider.generate(prompt)

        # Parse response
        learnings = self._parse_document_analysis_response(response, bundle, learning_type)

        return learnings

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
        detection_prompt = getattr(type_config, "detection_prompt", "")

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

        return DocumentBundle(
            bundle_id="combined_project_level",
            bundle_type=type_config.document_bundle.bundle_type,
            bundle_strategy="collection",
            files=unique_files,
            project_path=bundles[0].project_path,
        )

    def cleanup(self) -> None:
        """Clean up temporary files."""
        self.temp_manager.cleanup()
