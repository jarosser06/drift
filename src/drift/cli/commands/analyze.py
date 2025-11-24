"""Analyze command for drift CLI."""

import sys
from pathlib import Path
from typing import Optional

import typer

from drift.cli.output.formatter import OutputFormatter
from drift.cli.output.json import JsonFormatter
from drift.cli.output.markdown import MarkdownFormatter
from drift.config.loader import ConfigLoader
from drift.config.models import ConversationMode
from drift.core.analyzer import DriftAnalyzer
from drift.core.types import CompleteAnalysisResult


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

    # Merge summaries
    merged_summary = conv_result.summary.copy()
    merged_summary.total_learnings += doc_result.summary.total_learnings

    # Merge by_type counts
    for type_name, count in doc_result.summary.by_type.items():
        merged_summary.by_type[type_name] = merged_summary.by_type.get(type_name, 0) + count

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
        "conversations",
        "--scope",
        "-s",
        help="Analysis scope: conversations, documents, or all",
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
    project: Optional[str] = typer.Option(
        None,
        "--project",
        "-p",
        help="Project path (defaults to current directory)",
    ),
) -> None:
    """Analyze AI agent conversations to identify drift patterns.

    Runs multi-pass analysis on conversations to detect gaps between what AI agents
    did and what users actually wanted. Outputs actionable insights for improving
    documentation, workflows, and context.

    Examples
    --------
    # Analyze latest conversation in current project
    drift analyze

        # Output as JSON
        drift analyze --format json

        # Analyze only incomplete_work and documentation_gap
        drift analyze --types incomplete_work,documentation_gap

        # Analyze last 3 days of conversations
        drift analyze --days 3

        # Use sonnet model for all analysis
        drift analyze --model sonnet
    """
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
        if scope not in ["conversations", "documents", "all"]:
            typer.secho(
                f"Error: Invalid scope: {scope}. Use 'conversations', 'documents', or 'all'",
                fg=typer.colors.RED,
                err=True,
            )
            raise typer.Exit(1)

        # Create analyzer
        analyzer = DriftAnalyzer(config=config, project_path=project_path)

        # Run analysis based on scope
        try:
            if scope == "conversations":
                result = analyzer.analyze(
                    agent_tool=agent_tool,
                    learning_types=learning_types_list,
                    model_override=model,
                )
            elif scope == "documents":
                result = analyzer.analyze_documents(
                    learning_types=learning_types_list,
                    model_override=model,
                )
            elif scope == "all":
                # Run both analyses
                conv_result = analyzer.analyze(
                    agent_tool=agent_tool,
                    learning_types=learning_types_list,
                    model_override=model,
                )
                doc_result = analyzer.analyze_documents(
                    learning_types=learning_types_list,
                    model_override=model,
                )
                # Merge results
                result = _merge_results(conv_result, doc_result)
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

        # Format and output results
        formatter: OutputFormatter
        if format == "markdown":
            formatter = MarkdownFormatter(config=config)
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
