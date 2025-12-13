"""Shared utility functions for CLI commands."""

import sys

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
