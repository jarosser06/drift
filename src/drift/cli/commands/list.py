"""List command for drift CLI.

Lists all available Drift rules from configuration.
Provides simple text output (one rule per line) or JSON format.
"""

import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from drift.cli.logging_config import setup_logging
from drift.cli.utils import print_error
from drift.config.loader import ConfigLoader

logger = logging.getLogger(__name__)


def list_command(
    format_type: str = "text",
    project: Optional[str] = None,
    rules_file: Optional[List[str]] = None,
    verbose: int = 0,
) -> None:
    """List all available Drift rules.

    This command reads rule definitions from configuration and outputs
    a list of available rule names. The output format can be plain text
    (one rule per line, default) or JSON.

    -- format_type: Output format ('text' or 'json')
    -- project: Project path (if None, uses current directory)
    -- rules_file: List of custom rules files to load
    -- verbose: Verbosity level (0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG)
    """
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
            config = ConfigLoader.load_config(project_path, rules_files=rules_file)
        except ValueError as e:
            print_error(f"Configuration error: {e}")
            sys.exit(1)

        # Get list of rule names
        rule_names = list(config.rule_definitions.keys())

        # Normalize format - treat markdown as text for list command
        if format_type == "markdown":
            format_type = "text"

        # Output based on format
        if format_type == "text":
            # Simple text output - one rule per line (script-friendly)
            for rule_name in rule_names:
                print(rule_name)
        elif format_type == "json":
            # JSON output with structure
            output = {"rules": rule_names}
            print(json.dumps(output, indent=2))
        else:
            print_error(f"Error: Unsupported format '{format_type}'. Use 'text' or 'json'.")
            sys.exit(1)

        sys.exit(0)

    except KeyboardInterrupt:
        print_error("\nList interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during list")
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
