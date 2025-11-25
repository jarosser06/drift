"""Analyze command for drift CLI."""

import logging
import sys
from pathlib import Path
from typing import Optional

import typer

from drift.cli.logging_config import setup_logging
from drift.cli.output.formatter import OutputFormatter
from drift.cli.output.json import JsonFormatter
from drift.cli.output.markdown import MarkdownFormatter
from drift.config.loader import ConfigLoader
from drift.config.models import ConversationMode
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import CompleteAnalysisResult

logger = logging.getLogger(__name__)


def _merge_results(
    conv_result: CompleteAnalysisResult, doc_result: CompleteAnalysisResult
) -> CompleteAnalysisResult:
    """Merge conversation and document analysis results.

    Args:
        conv_result: Conversation analysis results
        doc_result: Document analysis results

    Returns:
        Merged results
    """
    # Merge metadata
    merged_metadata = {
        **conv_result.metadata,
        "analysis_scopes": ["conversations", "documents"],
        "document_learnings": doc_result.metadata.get("document_learnings", []),
    }

    # Merge execution_details from both results
    conv_exec_details = conv_result.metadata.get("execution_details", [])
    doc_exec_details = doc_result.metadata.get("execution_details", [])
    merged_metadata["execution_details"] = conv_exec_details + doc_exec_details

    logger.debug(
        f"Merging results: conversation has {len(conv_exec_details)} execution details, "
        f"document has {len(doc_exec_details)} execution details"
    )
    logger.debug(f"Merged result has {len(merged_metadata['execution_details'])} execution details")

    # Merge skipped_rules from both results
    conv_skipped = conv_result.metadata.get("skipped_rules", [])
    doc_skipped = doc_result.metadata.get("skipped_rules", [])
    if conv_skipped or doc_skipped:
        merged_metadata["skipped_rules"] = list(set(conv_skipped) | set(doc_skipped))

    # Merge summaries
    merged_summary = conv_result.summary.model_copy()
    merged_summary.total_learnings += doc_result.summary.total_learnings

    # Merge by_type counts
    for type_name, count in doc_result.summary.by_type.items():
        merged_summary.by_type[type_name] = merged_summary.by_type.get(type_name, 0) + count

    # Merge rule statistics
    if conv_result.summary.rules_checked and doc_result.summary.rules_checked:
        merged_summary.rules_checked = list(
            set(conv_result.summary.rules_checked) | set(doc_result.summary.rules_checked)
        )
    elif doc_result.summary.rules_checked:
        merged_summary.rules_checked = doc_result.summary.rules_checked

    if conv_result.summary.rules_passed and doc_result.summary.rules_passed:
        merged_summary.rules_passed = list(
            set(conv_result.summary.rules_passed) | set(doc_result.summary.rules_passed)
        )
    elif doc_result.summary.rules_passed:
        merged_summary.rules_passed = doc_result.summary.rules_passed

    if conv_result.summary.rules_warned and doc_result.summary.rules_warned:
        merged_summary.rules_warned = list(
            set(conv_result.summary.rules_warned) | set(doc_result.summary.rules_warned)
        )
    elif doc_result.summary.rules_warned:
        merged_summary.rules_warned = doc_result.summary.rules_warned

    if conv_result.summary.rules_failed and doc_result.summary.rules_failed:
        merged_summary.rules_failed = list(
            set(conv_result.summary.rules_failed) | set(doc_result.summary.rules_failed)
        )
    elif doc_result.summary.rules_failed:
        merged_summary.rules_failed = doc_result.summary.rules_failed

    if conv_result.summary.rules_errored and doc_result.summary.rules_errored:
        merged_summary.rules_errored = list(
            set(conv_result.summary.rules_errored) | set(doc_result.summary.rules_errored)
        )
    elif doc_result.summary.rules_errored:
        merged_summary.rules_errored = doc_result.summary.rules_errored

    # Merge results lists
    merged_results = conv_result.results + doc_result.results

    return CompleteAnalysisResult(
        metadata=merged_metadata,
        summary=merged_summary,
        results=merged_results,
    )


def analyze_command(
    format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format (markdown or json)",
    ),
    scope: str = typer.Option(
        "all",
        "--scope",
        "-s",
        help="Analysis scope: conversation, project, or all",
    ),
    agent_tool: Optional[str] = typer.Option(
        None,
        "--agent-tool",
        "-a",
        help="Specific agent tool to analyze (e.g., claude-code)",
    ),
    types: Optional[str] = typer.Option(
        None,
        "--types",
        "-t",
        help="Comma-separated list of learning types to check",
    ),
    latest: bool = typer.Option(
        False,
        "--latest",
        help="Analyze only the latest conversation",
    ),
    days: Optional[int] = typer.Option(
        None,
        "--days",
        "-d",
        help="Analyze conversations from last N days",
    ),
    all_conversations: bool = typer.Option(
        False,
        "--all",
        help="Analyze all conversations",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Override model for all analysis (e.g., sonnet, haiku)",
    ),
    no_llm: bool = typer.Option(
        False,
        "--no-llm",
        help="Skip rules that require LLM calls (only run programmatic validation)",
    ),
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project path (defaults to current directory)",
    ),
    verbose: int = typer.Option(
        0,
        "--verbose",
        "-v",
        count=True,
        help="Increase verbosity (-v for INFO, -vv for DEBUG, -vvv for TRACE)",
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        help="Show detailed test execution information (markdown format only)",
    ),
) -> None:
    """Analyze AI agent conversations to identify drift patterns.

    Runs multi-pass analysis on conversations to detect gaps between what AI agents
    did and what users actually wanted. Outputs actionable insights for improving
    documentation, workflows, and context.

    This function is called by the main CLI (drift command) and can also be used
    programmatically.

    Examples
    --------
    # Analyze latest conversation in current project
    drift

    # Output as JSON
    drift --format json

    # Analyze only incomplete_work and documentation_gap
    drift --types incomplete_work,documentation_gap

    # Analyze last 3 days of conversations
    drift --days 3

    # Use sonnet model for all analysis
    drift --model sonnet
    """
    # Setup colored logging based on verbosity
    setup_logging(verbose)

    try:
        # Ensure global config exists on first run
        ConfigLoader.ensure_global_config_exists()

        # Determine project path
        project_path = Path(project) if project else Path.cwd()
        if not project_path.exists():
            typer.secho(
                f"Error: Project path does not exist: {project_path}", fg=typer.colors.RED, err=True
            )
            raise typer.Exit(1)

        # Load configuration
        try:
            config = ConfigLoader.load_config(project_path)
        except ValueError as e:
            typer.secho(f"Configuration error: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        # Override conversation mode if specified
        conversation_mode_count = sum([latest, bool(days), all_conversations])
        if conversation_mode_count > 1:
            typer.secho(
                "Error: Only one of --latest, --days, or --all can be specified",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)

        if latest:
            config.conversations.mode = ConversationMode.LATEST
        elif days is not None:
            config.conversations.mode = ConversationMode.LAST_N_DAYS
            config.conversations.days = days
        elif all_conversations:
            config.conversations.mode = ConversationMode.ALL

        # Parse learning types if specified
        learning_types_list = None
        if types:
            learning_types_list = [t.strip() for t in types.split(",")]
            # Validate learning types exist in config
            invalid_types = [t for t in learning_types_list if t not in config.drift_learning_types]
            if invalid_types:
                typer.secho(
                    f"Error: Unknown learning types: {', '.join(invalid_types)}",
                    fg=typer.colors.RED,
                    err=True,
                )
                typer.secho(
                    f"Available types: {', '.join(config.drift_learning_types.keys())}",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                raise typer.Exit(1)

        # Validate agent tool if specified
        if agent_tool and agent_tool not in config.agent_tools:
            typer.secho(
                f"Error: Unknown agent tool: {agent_tool}",
                fg=typer.colors.RED,
                err=True,
            )
            typer.secho(
                f"Available tools: {', '.join(config.agent_tools.keys())}",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(1)

        # Validate model override if specified
        if model and model not in config.models:
            typer.secho(
                f"Error: Unknown model: {model}",
                fg=typer.colors.RED,
                err=True,
            )
            typer.secho(
                f"Available models: {', '.join(config.models.keys())}",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(1)

        # Validate output format
        if format not in ["markdown", "json"]:
            typer.secho(
                f"Error: Invalid format: {format}. Use 'markdown' or 'json'",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)

        # Validate scope
        if scope not in ["conversation", "project", "all"]:
            typer.secho(
                f"Error: Invalid scope: {scope}. Use 'conversation', 'project', or 'all'",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)

        # Filter LLM-based rules if --no-llm flag is set
        llm_skipped_rules = []
        if no_llm:
            # Determine which rules to check
            rules_to_check = (
                learning_types_list
                if learning_types_list
                else list(config.drift_learning_types.keys())
            )

            # Determine which scopes we're analyzing based on --scope flag
            if scope == "conversation":
                target_scopes = ["turn_level", "conversation_level"]
            elif scope == "project":
                target_scopes = ["document_level", "project_level"]
            else:  # scope == "all"
                target_scopes = [
                    "turn_level",
                    "conversation_level",
                    "document_level",
                    "project_level",
                ]

            # Filter to only programmatic rules within the target scopes
            filtered_types = []
            for name in rules_to_check:
                type_config = config.drift_learning_types[name]
                rule_scope = getattr(type_config, "scope", "turn_level")

                # Skip rules that don't match our target scopes
                if rule_scope not in target_scopes:
                    continue

                # Check if this is an LLM-based rule by inspecting phases
                # A rule uses LLM if ANY phase has type="prompt"
                phases = getattr(type_config, "phases", []) or []
                validation_rules = getattr(type_config, "validation_rules", None)

                # Rule uses LLM if any phase has type="prompt"
                uses_llm = any(getattr(p, "type", "prompt") == "prompt" for p in phases)

                # Rule is programmatic if it has validation_rules OR no phases use LLM
                is_programmatic = validation_rules is not None or not uses_llm

                if is_programmatic:
                    filtered_types.append(name)
                else:
                    llm_skipped_rules.append(name)

            # Warn if rules were skipped
            if llm_skipped_rules:
                programmatic_count = len(filtered_types) if filtered_types else 0
                typer.secho(
                    f"Warning: Skipping {len(llm_skipped_rules)} LLM-based rule(s) "
                    f"due to --no-llm flag (running {programmatic_count} programmatic rule(s)):",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                typer.secho(
                    f"  Skipped: {', '.join(llm_skipped_rules)}",
                    fg=typer.colors.YELLOW,
                    err=True,
                )
                if filtered_types:
                    typer.secho(
                        f"  Running: {', '.join(filtered_types)}",
                        fg=typer.colors.GREEN,
                        err=True,
                    )
                typer.secho("", err=True)

            learning_types_list = filtered_types if filtered_types else []

        # Create analyzer
        analyzer = DriftAnalyzer(config=config, project_path=project_path)

        # Run analysis based on scope
        try:
            if scope == "conversation":
                result = analyzer.analyze(
                    agent_tool=agent_tool,
                    learning_types=learning_types_list,
                    model_override=model,
                )
            elif scope == "project":
                result = analyzer.analyze_documents(
                    learning_types=learning_types_list,
                    model_override=model,
                )
            elif scope == "all":
                # When --no-llm is used with scope=all, need to split filtered rules by scope
                conv_types_list = learning_types_list
                doc_types_list = learning_types_list

                if no_llm and learning_types_list is not None:
                    # Split the filtered programmatic rules by scope
                    conv_types_list = [
                        name
                        for name in learning_types_list
                        if getattr(config.drift_learning_types[name], "scope", "turn_level")
                        in ("turn_level", "conversation_level")
                    ]
                    doc_types_list = [
                        name
                        for name in learning_types_list
                        if getattr(config.drift_learning_types[name], "scope", "turn_level")
                        in ("document_level", "project_level")
                    ]

                # Run both analyses
                conv_result = analyzer.analyze(
                    agent_tool=agent_tool,
                    learning_types=conv_types_list,
                    model_override=model,
                )
                doc_result = analyzer.analyze_documents(
                    learning_types=doc_types_list,
                    model_override=model,
                )
                # Merge results
                result = _merge_results(conv_result, doc_result)

            # Add LLM-skipped rules to metadata if --no-llm was used
            if no_llm and llm_skipped_rules:
                existing_skipped = result.metadata.get("skipped_rules", [])
                result.metadata["skipped_rules"] = existing_skipped + llm_skipped_rules

        except FileNotFoundError as e:
            typer.secho(f"Error: {e}", fg=typer.colors.RED, err=True)
            typer.secho(
                "\nTip: Ensure the agent tool's conversation path is configured correctly.",
                fg=typer.colors.YELLOW,
                err=True,
            )
            raise typer.Exit(1)
        except Exception as e:
            typer.secho(f"Analysis failed: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(1)

        # Check if this is because there are NO rules at all configured
        if not config.drift_learning_types:
            typer.secho(
                "Error: No drift learning types configured.",
                fg=typer.colors.RED,
                err=True,
            )
            typer.secho(
                "\nTip: Create a .drift.yaml file in your project or global config directory.",
                fg=typer.colors.YELLOW,
                err=True,
            )
            typer.secho(
                "See: https://github.com/your-repo/drift for configuration examples",
                fg=typer.colors.BLUE,
                err=True,
            )
            raise typer.Exit(1)

        # Output rule errors to stderr first
        if result.summary.rules_errored:
            typer.secho("\nRule Errors:", fg=typer.colors.RED, bold=True, err=True)
            for rule in sorted(result.summary.rules_errored):
                error_msg = result.summary.rule_errors.get(rule, "Unknown error")
                typer.secho(f"  {rule}: {error_msg}", fg=typer.colors.RED, err=True)
            typer.secho("", err=True)  # Blank line

        # Output skipped rules warning to stderr
        skipped_rules = result.metadata.get("skipped_rules", [])
        if skipped_rules:
            typer.secho(
                f"\nSkipped {len(skipped_rules)} rule(s):",
                fg=typer.colors.YELLOW,
                bold=True,
                err=True,
            )
            for rule in sorted(skipped_rules):
                typer.secho(f"  {rule}", fg=typer.colors.YELLOW, err=True)
            typer.secho("", err=True)  # Blank line

        # Format and output results
        formatter: OutputFormatter
        if format == "markdown":
            formatter = MarkdownFormatter(config=config, detailed=detailed)
        else:
            formatter = JsonFormatter()

        output = formatter.format(result)
        print(output)

        # Exit with appropriate code
        # Exit code 0: No learnings found (clean)
        # Exit code 1: Error occurred (handled above)
        # Exit code 2: Learnings found (drift detected)
        if result.summary.total_learnings > 0:
            sys.exit(2)
        else:
            sys.exit(0)

    except typer.Exit:
        # Re-raise typer exits (already handled)
        raise
    except KeyboardInterrupt:
        typer.secho("\nAnalysis interrupted by user", fg=typer.colors.YELLOW, err=True)
        raise typer.Exit(130)
    except Exception as e:
        typer.secho(f"Unexpected error: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(1)
