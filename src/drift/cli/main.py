"""Main CLI application for drift."""

import argparse

from drift.cli.commands import analyze

__version__ = "0.1.0"


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns the configured ArgumentParser with all CLI options.
    """
    parser = argparse.ArgumentParser(
        prog="drift",
        description=(
            "AI agent conversation drift analyzer - identifies gaps between "
            "what AI agents did and what users wanted"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
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
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"drift version {__version__}",
        help="Show version and exit",
    )

    parser.add_argument(
        "--format",
        "-f",
        default="markdown",
        help="Output format (markdown or json)",
    )

    parser.add_argument(
        "--scope",
        "-s",
        default="project",
        help="Analysis scope: conversation, project, or all",
    )

    parser.add_argument(
        "--agent-tool",
        "-a",
        default=None,
        help="Specific agent tool to analyze (e.g., claude-code)",
    )

    parser.add_argument(
        "--rules",
        "-r",
        default=None,
        help="Comma-separated list of rules to check",
    )

    parser.add_argument(
        "--latest",
        action="store_true",
        help="Analyze only the latest conversation",
    )

    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=None,
        help="Analyze conversations from last N days",
    )

    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_conversations",
        help="Analyze all conversations",
    )

    parser.add_argument(
        "--model",
        "-m",
        default=None,
        help="Override model for all analysis (e.g., sonnet, haiku)",
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip rules that require LLM calls (only run programmatic validation)",
    )

    parser.add_argument(
        "--project",
        "-p",
        default=None,
        help="Project path (defaults to current directory)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG, -vvv for TRACE)",
    )

    return parser


def main() -> None:
    """Parse command-line arguments and run drift analysis.

    Entry point for the drift CLI that delegates to the analyze command.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Call analyze command with parsed arguments
    analyze.analyze_command(
        format=args.format,
        scope=args.scope,
        agent_tool=args.agent_tool,
        rules=args.rules,
        latest=args.latest,
        days=args.days,
        all_conversations=args.all_conversations,
        model=args.model,
        no_llm=args.no_llm,
        project=args.project,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
