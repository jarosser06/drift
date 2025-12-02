"""Test utilities for CLI testing without Typer."""

import io
import sys
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, List, Optional


class CliResult:
    """Result of a CLI invocation.

    Mimics the structure of typer.testing.Result for compatibility with existing tests.
    """

    def __init__(
        self, exit_code: int, stdout: str, stderr: str, exception: Optional[Exception] = None
    ):
        """Initialize CLI result.

        -- exit_code: Exit code from the CLI
        -- stdout: Captured standard output
        -- stderr: Captured standard error
        -- exception: Exception raised during execution, if any
        """
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.exception = exception


class CliRunner:
    """CLI test runner for argparse-based CLIs.

    Provides a similar interface to typer.testing.CliRunner for testing.
    """

    def invoke(self, main_func: Any, args: List[str]) -> CliResult:
        """Invoke the CLI with the given arguments.

        -- main_func: Main function to invoke
        -- args: List of command-line arguments

        Returns CliResult with exit code, stdout, and stderr.
        """
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        exit_code = 0
        exception = None

        # Save original sys.argv
        original_argv = sys.argv.copy()

        try:
            # Set sys.argv to simulate command line
            sys.argv = ["drift"] + args

            # Capture stdout and stderr
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                try:
                    main_func()
                except SystemExit as e:
                    exit_code = e.code if e.code is not None else 0
                except Exception as e:
                    exception = e
                    exit_code = 1

        finally:
            # Restore original sys.argv
            sys.argv = original_argv

        return CliResult(
            exit_code=exit_code,
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
            exception=exception,
        )
