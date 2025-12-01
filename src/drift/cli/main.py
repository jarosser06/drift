"""Main CLI application for drift."""

import typer

from drift.cli.commands import analyze

# Create the main Typer app - use analyze_command directly as the default
app = typer.Typer(
    name="drift",
    help=(
        "AI agent conversation drift analyzer - identifies gaps between "
        "what AI agents did and what users wanted"
    ),
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Handle --version flag."""
    if value:
        print("drift version 0.1.0")
        raise typer.Exit(0)


# Make analyze the default command by registering it at the root level
@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version and exit",
        callback=version_callback,
        is_eager=True,
    ),
    format: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format (markdown or json)",
    ),
    scope: str = typer.Option(
        "project",
        "--scope",
        "-s",
        help="Analysis scope: conversation, project, or all",
    ),
    agent_tool: str = typer.Option(
        None,
        "--agent-tool",
        "-a",
        help="Specific agent tool to analyze (e.g., claude-code)",
    ),
    rules: str = typer.Option(
        None,
        "--rules",
        "-r",
        help="Comma-separated list of rules to check",
    ),
    latest: bool = typer.Option(
        False,
        "--latest",
        help="Analyze only the latest conversation",
    ),
    days: int = typer.Option(
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
    model: str = typer.Option(
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
    project: str = typer.Option(
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

    Examples
    --------
    # Analyze latest conversation in current project
    drift

    # Output as JSON
    drift --format json

    # Analyze only incomplete_work and documentation_gap
    drift --rules incomplete_work,documentation_gap

    # Analyze last 3 days of conversations
    drift --days 3

    # Use sonnet model for all analysis
    drift --model sonnet
    """
    # If a subcommand is invoked, don't run analyze
    if ctx.invoked_subcommand is not None:
        return

    # Run the analyze command directly
    analyze.analyze_command(
        format=format,
        scope=scope,
        agent_tool=agent_tool,
        rules=rules,
        latest=latest,
        days=days,
        all_conversations=all_conversations,
        model=model,
        no_llm=no_llm,
        project=project,
        verbose=verbose,
        detailed=detailed,
    )


if __name__ == "__main__":
    app()
