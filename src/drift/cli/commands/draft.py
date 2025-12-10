"""Draft command for drift CLI.

Generates AI prompts from Drift rules to help draft new files that
satisfy validation requirements.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from drift.cli.logging_config import setup_logging
from drift.config.loader import ConfigLoader
from drift.draft import DraftEligibility, FileExistenceChecker, FilePatternResolver, PromptGenerator

logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_error(message: str) -> None:
    """Print error message to stderr with red color.

    -- message: Error message to print
    """
    print(f"{RED}{message}{RESET}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message to stderr with yellow color.

    -- message: Warning message to print
    """
    print(f"{YELLOW}{message}{RESET}", file=sys.stderr)


def print_success(message: str) -> None:
    """Print success message to stdout with green color.

    -- message: Success message to print
    """
    print(f"{GREEN}{message}{RESET}")


def draft_command(
    rule: str,
    target_file: Optional[str] = None,
    output: Optional[str] = None,
    force: bool = False,
    project: Optional[str] = None,
    verbose: int = 0,
) -> None:
    """Generate AI prompt for drafting a file from a Drift rule.

    This command reads a rule definition and generates an AI prompt that can be
    used to create a file satisfying the rule's validation requirements. The prompt
    is either printed to stdout or saved to a file.

    Draft works on ONE file at a time. If the rule pattern contains wildcards
    (e.g., ".claude/skills/*/SKILL.md"), you must specify which file to draft
    using --target-file.

    Parameters
    ----------
    rule : str
        Name of the rule to draft (e.g., "skill_validation").
    target_file : Optional[str], optional
        Specific file path to draft (required if rule pattern has wildcards).
    output : Optional[str], optional
        Output file path. If None, prints to stdout.
    force : bool, optional
        If True, generate prompt even if target file exists.
    project : Optional[str], optional
        Project path. If None, uses current directory.
    verbose : int, optional
        Verbosity level (0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG).

    Examples
    --------
    # Rule with specific path (no wildcards)
    drift draft --target-rule skill_validation

    # Rule with wildcard pattern - requires --target-file
    drift draft --target-rule skill_validation --target-file .claude/skills/testing/SKILL.md

    # Save to file
    drift draft --target-rule skill_validation --output prompt.md
    """
    # Setup colored logging based on verbosity
    setup_logging(verbose)

    try:
        # Ensure global config exists on first run
        ConfigLoader.ensure_global_config_exists()

        # Determine project path
        project_path = Path(project) if project else Path.cwd()
        if not project_path.exists():
            print_error(f"Error: Project path does not exist: {project_path}")
            sys.exit(1)

        # Load configuration
        try:
            config = ConfigLoader.load_config(project_path, rules_files=None)
        except ValueError as e:
            print_error(f"Configuration error: {e}")
            sys.exit(1)

        # Check if rule exists
        if rule not in config.rule_definitions:
            print_error(f"Error: Rule '{rule}' not found in configuration.")
            available_rules = ", ".join(config.rule_definitions.keys())
            print_error(f"Available rules: {available_rules}")
            sys.exit(1)

        rule_def = config.rule_definitions[rule]

        # Check if rule is eligible for draft
        eligible, error_message = DraftEligibility.check(rule_def)
        if not eligible:
            print_error(f"Error: Rule '{rule}' doesn't support draft.")
            print_error(f"Reason: {error_message}")
            sys.exit(1)

        # Resolve file patterns to target paths
        # Note: document_bundle is guaranteed to exist because eligibility check passed
        assert rule_def.document_bundle is not None
        resolver = FilePatternResolver(project_path)
        resolved_files = []

        for pattern in rule_def.document_bundle.file_patterns:
            resolved = resolver.resolve(pattern)
            resolved_files.extend(resolved)

        # Determine target file
        # If rule pattern has no wildcards: resolver returns single file
        # If rule pattern has wildcards: resolver returns empty list (requires --target-file)
        if not resolved_files:
            # Pattern has wildcards - require --target-file
            if not target_file:
                pattern_str = ", ".join(rule_def.document_bundle.file_patterns)
                print_error(f"Error: Rule '{rule}' uses wildcard pattern: {pattern_str}")
                print_error("This rule can match multiple files.")
                print_error("You must specify which file to draft using --target-file.\n")
                print_error("Example:")
                print_error(
                    f"  drift draft --target-rule {rule} "
                    "--target-file .claude/skills/testing/SKILL.md"
                )
                sys.exit(1)

            # Use target_file provided by user
            target_path = project_path / target_file
            target_files = [target_path]
        else:
            # Pattern resolved to a single file
            target_files = resolved_files

        # Check if target file already exists
        any_exist, existing_files = FileExistenceChecker.check(target_files)
        if any_exist and not force:
            file_path = existing_files[0]
            try:
                rel_path = file_path.relative_to(project_path)
            except ValueError:
                rel_path = file_path
            print_warning(f"Warning: Target file already exists: {rel_path}")
            print_warning("Refusing to generate prompt (file would be overwritten).")
            print_warning("Use --force to generate prompt anyway.")
            sys.exit(1)

        # Generate prompt
        generator = PromptGenerator()
        prompt = generator.generate(rule, rule_def, target_files, project_path)

        # Output prompt
        if output:
            output_path = Path(output)
            try:
                output_path.write_text(prompt, encoding="utf-8")
                print_success(f"Draft prompt written to: {output_path}")
            except Exception as e:
                print_error(f"Error writing to file: {e}")
                sys.exit(1)
        else:
            # Print to stdout
            print(prompt)

        sys.exit(0)

    except KeyboardInterrupt:
        print_error("\nDraft interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during draft")
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
