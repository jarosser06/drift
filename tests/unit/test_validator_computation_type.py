"""Test computation_type property on validators."""

import pytest

from drift.validation.validators import ValidatorRegistry
from drift.validation.validators.base import BaseValidator
from drift.validation.validators.client import ClaudeSkillSettingsValidator
from drift.validation.validators.core import (
    DependencyDuplicateValidator,
    FileExistsValidator,
    ListMatchValidator,
    ListRegexMatchValidator,
    MarkdownLinkValidator,
    RegexMatchValidator,
)


def test_all_validators_have_computation_type():
    """Test that all validators implement computation_type property."""
    validators = [
        FileExistsValidator(),
        RegexMatchValidator(),
        ListMatchValidator(),
        ListRegexMatchValidator(),
        DependencyDuplicateValidator(),
        MarkdownLinkValidator(),
        ClaudeSkillSettingsValidator(),
    ]

    for validator in validators:
        assert hasattr(validator, "computation_type")
        comp_type = validator.computation_type
        assert comp_type in ["programmatic", "llm"]


def test_all_validators_are_programmatic():
    """Test that all current validators are programmatic."""
    validators = [
        FileExistsValidator(),
        RegexMatchValidator(),
        ListMatchValidator(),
        ListRegexMatchValidator(),
        DependencyDuplicateValidator(),
        MarkdownLinkValidator(),
        ClaudeSkillSettingsValidator(),
    ]

    for validator in validators:
        assert validator.computation_type == "programmatic"


def test_registry_get_computation_type():
    """Test ValidatorRegistry.get_computation_type method."""
    registry = ValidatorRegistry()

    # Test all registered types
    assert registry.get_computation_type("core:file_exists") == "programmatic"
    assert registry.get_computation_type("core:file_exists") == "programmatic"
    assert registry.get_computation_type("core:regex_match") == "programmatic"
    assert registry.get_computation_type("core:list_match") == "programmatic"
    assert registry.get_computation_type("core:list_regex_match") == "programmatic"
    assert registry.get_computation_type("core:dependency_duplicate") == "programmatic"
    assert registry.get_computation_type("core:markdown_link") == "programmatic"
    assert registry.get_computation_type("core:claude_skill_settings") == "programmatic"


def test_registry_is_programmatic():
    """Test ValidatorRegistry.is_programmatic method."""
    registry = ValidatorRegistry()

    # All current validators should be programmatic
    assert registry.is_programmatic("core:file_exists") is True
    assert registry.is_programmatic("core:claude_skill_settings") is True


def test_base_validator_abstract_computation_type():
    """Test that BaseValidator.computation_type is abstract."""
    # Cannot instantiate BaseValidator directly
    with pytest.raises(TypeError):
        BaseValidator()
