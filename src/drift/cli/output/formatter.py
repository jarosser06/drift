"""Base output formatter interface."""

from abc import ABC, abstractmethod

from drift.core.types import CompleteAnalysisResult


class OutputFormatter(ABC):
    """Abstract base class for output formatters."""

    @abstractmethod
    def format(self, result: CompleteAnalysisResult) -> str:
        """Format the analysis result.

        Args:
            result: Complete analysis result to format

        Returns:
            Formatted output string
        """
        pass

    @abstractmethod
    def get_format_name(self) -> str:
        """Get the name of this format.

        Returns:
            Format name (e.g., 'markdown', 'json')
        """
        pass
