"""Colored logging configuration for drift CLI."""

import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels."""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[31m\033[1m",  # Bold Red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Add colors to log record formatting."""
        # Only add colors if stderr is a terminal
        if hasattr(sys.stderr, "isatty") and sys.stderr.isatty():
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


def setup_logging(verbosity: int) -> None:
    """Configure colored logging based on verbosity level.

    Args:
        verbosity: 0=WARNING, 1=INFO, 2=DEBUG, 3+=DEBUG
    """
    log_level = logging.WARNING  # Default
    if verbosity == 1:
        log_level = logging.INFO
    elif verbosity >= 2:
        log_level = logging.DEBUG

    # Create handler with colored formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColoredFormatter("%(levelname)s: %(message)s"))

    # Configure root logger
    logging.basicConfig(level=log_level, handlers=[handler], force=True)

    logger = logging.getLogger(__name__)
    logger.debug(f"Verbosity level: {verbosity}")
    logger.debug(f"Log level: {logging.getLevelName(log_level)}")
