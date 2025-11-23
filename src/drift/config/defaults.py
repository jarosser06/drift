"""Default configuration for drift."""

from drift.config.models import (
    AgentToolConfig,
    ConversationMode,
    ConversationSelection,
    DriftConfig,
    DriftLearningType,
    ModelConfig,
    ProviderConfig,
    ProviderType,
)

# Default provider configurations
DEFAULT_PROVIDERS = {
    "bedrock": ProviderConfig(
        provider=ProviderType.BEDROCK,
        params={
            "region": "us-east-1",
            # Auth via default AWS credentials chain (no explicit config needed)
        },
    ),
}

# Default model configurations
DEFAULT_MODELS = {
    "haiku": ModelConfig(
        provider="bedrock",
        model_id="us.anthropic.claude-3-haiku-20240307-v1:0",
        params={
            "max_tokens": 4096,
            "temperature": 0.0,
        },
    ),
    "sonnet": ModelConfig(
        provider="bedrock",
        model_id="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        params={
            "max_tokens": 4096,
            "temperature": 0.0,
        },
    ),
}

# Default drift learning type definitions
DEFAULT_DRIFT_LEARNING_TYPES = {
    "incomplete_work": DriftLearningType(
        description="AI stopped before completing the full scope of work",
        detection_prompt="""Look for instances where the AI claimed to be done but the user \
had to ask for completion, finishing touches, or missing parts. Focus on:
- AI marking tasks as complete when significant work remains
- User asking "what about..." or "you didn't finish..." after AI claims completion
- Missing deliverables that were part of the original request""",
        analysis_method="ai_analyzed",
        scope="turn_level",
        context=(
            "AI stopping before completing full scope wastes user time and "
            "breaks workflow momentum. Clear completion expectations improve efficiency."
        ),
        requires_project_context=False,
        supported_clients=None,
        explicit_signals=[
            "Finish",
            "Complete",
            "You didn't finish",
            "What about",
            "You missed",
            "Still need",
        ],
        implicit_signals=[
            "User lists missing items after AI says done",
            "User asks for specific parts AI didn't do",
            "AI says 'done' but user continues with 'also need'",
        ],
        examples=[
            "User: implement auth | AI: [adds login only] | User: what about "
            "logout and session handling?"
        ],
        model=None,
    ),
    "agent_delegation_miss": DriftLearningType(
        description="AI performed tasks that available agents could handle better",
        detection_prompt="""Identify when AI performs tasks that available agents could \
handle better, leading to slower workflows and inconsistent results.

When analyzing, consider which agents are available in the project (if project context is provided).

Look for:
- AI manually performing tasks that specialized agents could automate
- User suggesting "use the X agent" or "let the agent handle this"
- AI spending multiple turns on tasks an agent could complete in one
- Repetitive manual work that agents are designed for""",
        analysis_method="ai_analyzed",
        scope="turn_level",
        context=(
            "Identifies when AI performs tasks that available agents could handle better, "
            "leading to slower workflows and inconsistent results. "
            "Proper delegation improves speed and reliability."
        ),
        requires_project_context=True,
        supported_clients=["claude-code"],
        explicit_signals=[
            "Use the agent",
            "Let the agent handle",
            "Why didn't you use the agent",
            "Delegate to",
        ],
        implicit_signals=[
            "AI manually performs automated tasks",
            "User redirects to agent-based workflow",
            "Multiple turns for single-agent task",
        ],
        examples=[
            "User: run tests | AI: [manually searches for test files, reads them] | "
            "User: just use the testing agent"
        ],
        model=None,
    ),
    "skill_ignored": DriftLearningType(
        description="AI reinvented solutions when documented skills existed",
        detection_prompt="""Find cases where AI implemented functionality from scratch \
when project skills already documented the approach.

When analyzing, consider which skills are available in the project (if project context is provided).

Look for:
- AI writing code that duplicates skill patterns
- User pointing to "we have a skill for this"
- AI not following documented skill workflows
- User referencing skill documentation AI should have used""",
        analysis_method="ai_analyzed",
        scope="turn_level",
        context=(
            "Reinventing documented solutions creates inconsistency and wastes "
            "development time. Using existing skills ensures proven patterns."
        ),
        requires_project_context=True,
        supported_clients=["claude-code"],
        explicit_signals=[
            "We have a skill for",
            "Check the skill",
            "Follow the skill pattern",
            "Use the documented approach",
        ],
        implicit_signals=[
            "AI implements from scratch when skill exists",
            "User references skill documentation",
            "Deviation from documented workflow",
        ],
        examples=[
            "User: add API endpoint | AI: [writes custom code] | "
            "User: we have a REST API skill that shows the pattern"
        ],
        model=None,
    ),
    "workflow_bypass": DriftLearningType(
        description="User manually prompted instead of using documented workflows",
        detection_prompt="""Detect when user bypassed documented workflows, commands, or \
processes by manually prompting the AI. This indicates workflows may need improvement or the \
user isn't aware of them.

Look for:
- User manually describing multi-step processes that commands automate
- Conversation following manual path when slash command exists
- User unaware of available automation
- Missing validation steps that workflows would provide

Note: Maximum 1 learning per conversation for this type.""",
        analysis_method="ai_analyzed",
        scope="conversation_level",
        context=(
            "Manual prompting instead of documented workflows misses validation steps "
            "and efficiency gains. Following established processes ensures quality and speed."
        ),
        requires_project_context=False,
        supported_clients=None,
        explicit_signals=[
            "I didn't know there was a command",
            "Oh, there's a workflow for that",
            "Should have used the command",
        ],
        implicit_signals=[
            "User manually describes automated workflow",
            "Missing validation from standard workflow",
            "Conversation recreates command functionality",
        ],
        examples=[
            "User: first run tests, then lint, then build, then commit | "
            "[when /full-check command exists]"
        ],
        model=None,
    ),
    "prescriptive_deviation": DriftLearningType(
        description="AI interpreted or improvised when literal adherence was required",
        detection_prompt="""Identify when AI added creativity or interpretation to tasks requiring \
exact adherence to documented patterns, specifications, or requirements.

Look for:
- User corrections: "exactly as shown", "don't change anything", "follow it literally"
- AI paraphrasing when quoting was required
- AI improving/optimizing when copying was needed
- Context requiring compliance (regulations, specs, established patterns)""",
        analysis_method="ai_analyzed",
        scope="turn_level",
        context=(
            "AI creativity is valuable, but some contexts require exact adherence "
            "to documented patterns for consistency and compliance."
        ),
        requires_project_context=False,
        supported_clients=None,
        explicit_signals=[
            "Exactly as shown",
            "Literally",
            "Don't change anything",
            "Copy it exactly",
            "Follow it precisely",
        ],
        implicit_signals=[
            "User corrects AI's interpretation",
            "AI paraphrased when quoting needed",
            "AI optimized when copying required",
        ],
        examples=[
            "User: add the error message from the spec | AI: [writes similar message] | "
            "User: no, use the exact wording from the spec"
        ],
        model=None,
    ),
    "no_agents_configured": DriftLearningType(
        description="Project has no agents configured, missing automation opportunities",
        detection_prompt="""Determine if the project has zero agents configured. This is a \
project-level issue indicating missed opportunities for task delegation and workflow automation.

Based on the project context (if provided), check if any agents are configured.

If no agents are found, this represents an opportunity to add specialized agents for common tasks \
to improve workflow speed and consistency.

Note: Maximum 1 learning per conversation for this type.""",
        analysis_method="ai_analyzed",
        scope="conversation_level",
        context=(
            "Projects without agents miss opportunities for specialized task delegation "
            "and workflow optimization. Adding agents for common tasks improves speed and "
            "consistency."
        ),
        requires_project_context=True,
        supported_clients=["claude-code"],
        explicit_signals=[],
        implicit_signals=[
            "No agents configured in project",
            "Project context shows empty agents list",
        ],
        examples=["Project with .claude/ directory but no .claude/agents/ folder"],
        model=None,
    ),
}

# Default agent tool configurations
DEFAULT_AGENT_TOOLS = {
    "claude-code": AgentToolConfig(
        conversation_path="~/.claude/projects/",
        enabled=True,
    ),
}

# Default conversation selection
DEFAULT_CONVERSATION_SELECTION = ConversationSelection(
    mode=ConversationMode.LATEST,
    days=7,
)


def get_default_config() -> DriftConfig:
    """Get the default drift configuration.

    Returns:
        Default DriftConfig instance
    """
    return DriftConfig(
        providers=DEFAULT_PROVIDERS,
        models=DEFAULT_MODELS,
        default_model="haiku",
        drift_learning_types=DEFAULT_DRIFT_LEARNING_TYPES,
        agent_tools=DEFAULT_AGENT_TOOLS,
        conversations=DEFAULT_CONVERSATION_SELECTION,
        temp_dir="/tmp/drift",
    )
