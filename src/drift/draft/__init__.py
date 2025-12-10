"""Draft module for generating AI prompts from Drift rules.

This module provides functionality to generate AI prompts that can be used to
scaffold new files (skills, commands, agents) based on Drift validation rules.
"""

from drift.draft.checker import FileExistenceChecker
from drift.draft.eligibility import DraftEligibility
from drift.draft.generator import PromptGenerator
from drift.draft.resolver import FilePatternResolver

__all__ = [
    "DraftEligibility",
    "FilePatternResolver",
    "FileExistenceChecker",
    "PromptGenerator",
]
