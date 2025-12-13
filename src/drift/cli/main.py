"""Main CLI application for drift."""

import argparse
from importlib.metadata import version

from drift.cli.commands import analyze, document, draft, list

__version__ = version("ai-drift")


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser.

    Returns the configured ArgumentParser with all CLI options.
    """
    parser = argparse.ArgumentParser(
        prog="drift",
        description=(
            "AI-augmented codebase validator - ensures your project follows "
            "best practices for AI agent collaboration, from conversation quality "
            "to dependency management and documentation"
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

  # Use custom rules file (ignores .drift.yaml/.drift_rules.yaml rules)
  drift --rules-file custom_rules.yaml

  # Use multiple rules files (later files override earlier ones)
  drift --rules-file base_rules.yaml --rules-file extra_rules.yaml

  # Use remote rules file for isolated testing
  drift --rules-file https://example.com/drift-rules.yaml

  # Draft command - generate AI prompts from rules
  drift draft --target-rule skill_validation
  drift draft --target-rule skill_validation --output prompt.md
  drift draft --target-rule skill_validation --target-file .claude/skills/testing/SKILL.md

  # Document command - generate rule documentation
  drift document --rules skill_validation
  drift document --rules skill_validation,agent_validation --output docs.md
  drift document --all --format html --output rules.html

  # List command - list available rules
  drift list
  drift list --format json
        """,
    )

    # Global arguments (available to all commands)
    parser.add_argument(
        "--version",
        action="version",
        version=f"drift version {__version__}",
        help="Show version and exit",
    )

    parser.add_argument(
        "--project",
        "-p",
        default=None,
        help="Project path (defaults to current directory)",
    )

    parser.add_argument(
        "--rules-file",
        action="append",
        default=None,
        help=(
            "Path to rules file (local file or HTTP(S) URL). "
            "Can be specified multiple times. "
            "When provided, ONLY loads specified files "
            "(ignores .drift.yaml and .drift_rules.yaml rules)."
        ),
    )

    parser.add_argument(
        "--format",
        "-f",
        default="markdown",
        help="Output format (markdown or json)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="count",
        default=0,
        help="Increase verbosity (-v for INFO, -vv for DEBUG, -vvv for TRACE)",
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Draft subcommand
    draft_parser = subparsers.add_parser(
        "draft",
        help="Generate AI prompt for drafting files from a rule",
        description="Generate AI prompts from Drift rules to draft new files",
    )
    draft_parser.add_argument(
        "--target-rule",
        dest="draft_rule",
        required=True,
        help="Rule name to draft (e.g., skill_validation)",
    )
    draft_parser.add_argument(
        "--target-file",
        default=None,
        help="Specific file path to draft (required if rule matches multiple files)",
    )
    draft_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: stdout)",
    )
    draft_parser.add_argument(
        "--force",
        action="store_true",
        help="Generate prompt even if target file exists",
    )

    # Document subcommand
    document_parser = subparsers.add_parser(
        "document",
        help="Generate documentation for Drift rules",
        description="Generate documentation from rule definitions",
    )
    document_parser.add_argument(
        "--rules",
        "-r",
        default=None,
        help="Comma-separated list of rule names to document",
    )
    document_parser.add_argument(
        "--all",
        action="store_true",
        dest="all_rules",
        help="Document all loaded rules",
    )
    document_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: stdout)",
    )

    # List subcommand
    subparsers.add_parser(
        "list",
        help="List all available Drift rules",
        description="List all available rules from configuration",
    )

    # Analyze command arguments (default command - no explicit subcommand)
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
        "--no-cache",
        action="store_true",
        help="Disable LLM response caching",
    )

    parser.add_argument(
        "--cache-dir",
        default=None,
        help="Custom cache directory location (defaults to .drift/cache)",
    )

    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel execution of validation rules",
    )

    return parser


def main() -> None:
    """Parse command-line arguments and run drift command.

    Entry point for the drift CLI that delegates to subcommands.
    """
    parser = create_parser()
    args = parser.parse_args()

    # Handle subcommands
    if args.command == "draft":
        # Call draft command - uses global args: project, rules_file, format, verbose
        draft.draft_command(
            rule=args.draft_rule,
            target_file=args.target_file,
            output=args.output,
            force=args.force,
            project=args.project,
            rules_file=args.rules_file,
            verbose=args.verbose,
        )
    elif args.command == "document":
        # Call document command - uses global args: project, rules_file, format, verbose
        document.document_command(
            rules=args.rules,
            all_rules=args.all_rules,
            output=args.output,
            format_type=args.format,
            project=args.project,
            rules_file=args.rules_file,
            verbose=args.verbose,
        )
    elif args.command == "list":
        # Call list command - uses global args: project, rules_file, format, verbose
        list.list_command(
            format_type=args.format,
            project=args.project,
            rules_file=args.rules_file,
            verbose=args.verbose,
        )
    else:
        # Default to analyze command for backward compatibility
        # Uses global args: project, rules_file, format, verbose
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
            no_cache=args.no_cache,
            cache_dir=args.cache_dir,
            no_parallel=args.no_parallel,
            project=args.project,
            rules_file=args.rules_file,
            verbose=args.verbose,
        )


if __name__ == "__main__":
    main()
