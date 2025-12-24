"""Comprehensive tests for parameter merging logic in DriftAnalyzer.

Tests all combinations of validator_param_overrides and rule_param_overrides
with different merge strategies (replace, merge) and data types (lists, dicts, primitives).
"""

from typing import Any, Dict

import pytest

from drift.config.models import DriftConfig
from drift.core.analyzer import DriftAnalyzer


@pytest.fixture
def base_config() -> Dict[str, Any]:
    """Return base configuration for testing."""
    return {
        "providers": {},
        "models": {},
        "default_model": "haiku",
        "rule_definitions": {},
    }


class TestValidatorParamOverrides:
    """Test validator_param_overrides with replace and merge strategies."""

    def test_validator_replace_strategy_primitive(self, base_config, tmp_path):
        """Test replace strategy with primitive values."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "replace": {
                        "min_count": 5,
                        "max_size": 1000,
                    }
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"min_count": 1, "max_size": 500, "other_param": "value"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        assert merged["min_count"] == 5  # Replaced
        assert merged["max_size"] == 1000  # Replaced
        assert merged["other_param"] == "value"  # Unchanged

    def test_validator_replace_strategy_adds_new_param(self, base_config, tmp_path):
        """Test replace strategy adds new parameters."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {"replace": {"new_param": "new_value"}}
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"existing": "value"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        assert merged["existing"] == "value"
        assert merged["new_param"] == "new_value"

    def test_validator_merge_strategy_list(self, base_config, tmp_path):
        """Test merge strategy extends lists."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "merge": {
                        "ignore_patterns": ["*.log", "*.tmp"],
                    }
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"ignore_patterns": ["*.pyc", "*.pyo"]}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Lists should be extended (original + override)
        assert merged["ignore_patterns"] == ["*.pyc", "*.pyo", "*.log", "*.tmp"]

    def test_validator_merge_strategy_dict(self, base_config, tmp_path):
        """Test merge strategy combines dicts."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "merge": {
                        "options": {"verbose": True, "strict": True},
                    }
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"options": {"verbose": False, "debug": True}}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Dicts should be merged (override takes precedence for conflicts)
        assert merged["options"] == {"verbose": True, "debug": True, "strict": True}

    def test_validator_merge_adds_new_list(self, base_config, tmp_path):
        """Test merge strategy creates new list if none exists."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "merge": {
                        "patterns": ["*.txt", "*.md"],
                    }
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Should add the list even if it didn't exist
        assert merged["patterns"] == ["*.txt", "*.md"]

    def test_validator_both_replace_and_merge(self, base_config, tmp_path):
        """Test using both replace and merge strategies together."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "replace": {"max_size": 2000},
                    "merge": {"ignore_patterns": ["*.log"]},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"max_size": 1000, "ignore_patterns": ["*.pyc"]}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Replace is applied first
        assert merged["max_size"] == 2000
        # Then merge extends the list
        assert merged["ignore_patterns"] == ["*.pyc", "*.log"]


class TestRuleParamOverrides:
    """Test rule_param_overrides with different identifier formats."""

    def test_rule_override_simple_name(self, base_config, tmp_path):
        """Test rule override with simple rule name."""
        config_dict = {
            **base_config,
            "rule_param_overrides": {
                "test_rule": {
                    "replace": {"param1": "override_value"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "original"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        assert merged["param1"] == "override_value"

    def test_rule_override_group_and_rule(self, base_config, tmp_path):
        """Test rule override with group::rule format."""
        config_dict = {
            **base_config,
            "rule_param_overrides": {
                "test_group::test_rule": {
                    "replace": {"param1": "group_override"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "original"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        assert merged["param1"] == "group_override"

    def test_rule_override_full_identifier(self, base_config, tmp_path):
        """Test rule override with group::rule::phase format."""
        config_dict = {
            **base_config,
            "rule_param_overrides": {
                "test_group::test_rule::validation_phase": {
                    "replace": {"param1": "full_override"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "original"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
            phase_name="validation_phase",
        )

        assert merged["param1"] == "full_override"

    def test_rule_override_precedence_most_specific_wins(self, base_config, tmp_path):
        """Test that more specific identifiers take precedence."""
        config_dict = {
            **base_config,
            "rule_param_overrides": {
                "test_rule": {
                    "replace": {"param1": "rule_level"},
                },
                "test_group::test_rule": {
                    "replace": {"param1": "group_level"},
                },
                "test_group::test_rule::phase1": {
                    "replace": {"param1": "phase_level"},
                },
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "original"}

        # With phase name - most specific wins
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
            phase_name="phase1",
        )
        assert merged["param1"] == "phase_level"

    def test_rule_override_merge_strategy(self, base_config, tmp_path):
        """Test rule override with merge strategy."""
        config_dict = {
            **base_config,
            "rule_param_overrides": {
                "test_rule": {
                    "merge": {"ignore_patterns": ["override.log"]},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"ignore_patterns": ["base.pyc"]}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        assert merged["ignore_patterns"] == ["base.pyc", "override.log"]


class TestCombinedOverrides:
    """Test combinations of validator and rule overrides with precedence."""

    def test_precedence_rule_overrides_validator(self, base_config, tmp_path):
        """Test that rule overrides take precedence over validator overrides."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "replace": {"param1": "validator_value"},
                }
            },
            "rule_param_overrides": {
                "test_rule": {
                    "replace": {"param1": "rule_value"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "base_value"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Rule override should win over validator override
        assert merged["param1"] == "rule_value"

    def test_combined_replace_and_merge_different_params(self, base_config, tmp_path):
        """Test validator and rule overrides affecting different parameters."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "replace": {"max_size": 5000},
                    "merge": {"ignore_patterns": ["*.validator"]},
                }
            },
            "rule_param_overrides": {
                "test_rule": {
                    "replace": {"min_count": 10},
                    "merge": {"ignore_patterns": ["*.rule"]},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {
            "max_size": 1000,
            "min_count": 1,
            "ignore_patterns": ["*.base"],
        }
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Validator replace applied
        assert merged["max_size"] == 5000
        # Rule replace applied
        assert merged["min_count"] == 10
        # Both merges applied (validator first, then rule)
        assert merged["ignore_patterns"] == ["*.base", "*.validator", "*.rule"]

    def test_precedence_order_base_validator_rule(self, base_config, tmp_path):
        """Test full precedence order: base → validator → rule."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "merge": {"tags": ["validator"]},
                }
            },
            "rule_param_overrides": {
                "test_group::test_rule": {
                    "merge": {"tags": ["rule"]},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"tags": ["base"]}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Should apply in order: base, then validator, then rule
        assert merged["tags"] == ["base", "validator", "rule"]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_base_params(self, base_config, tmp_path):
        """Test merging with empty base params."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "replace": {"param1": "value1"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        merged = analyzer._merge_params(
            base_params={},
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        assert merged["param1"] == "value1"

    def test_no_overrides_configured(self, base_config, tmp_path):
        """Test that base params are returned unchanged when no overrides exist."""
        config = DriftConfig(**base_config)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "value1", "param2": "value2"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        assert merged == base_params

    def test_validator_type_not_in_overrides(self, base_config, tmp_path):
        """Test with validator type that has no overrides."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:other_validator": {
                    "replace": {"param1": "value1"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "original"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",  # Different validator
            rule_name="test_rule",
            group_name="test_group",
        )

        # Should return base params unchanged
        assert merged["param1"] == "original"

    def test_merge_list_with_non_list(self, base_config, tmp_path):
        """Test merge strategy when base is list but override is not."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "merge": {"param1": "not_a_list"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": ["item1", "item2"]}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # When types don't match for merge, should replace
        assert merged["param1"] == "not_a_list"

    def test_merge_dict_with_non_dict(self, base_config, tmp_path):
        """Test merge strategy when base is dict but override is not."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "merge": {"param1": "not_a_dict"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": {"key": "value"}}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # When types don't match for merge, should replace
        assert merged["param1"] == "not_a_dict"

    def test_none_phase_name(self, base_config, tmp_path):
        """Test with None phase name (validation rules without phases)."""
        config_dict = {
            **base_config,
            "rule_param_overrides": {
                "test_group::test_rule::phase1": {
                    "replace": {"param1": "should_not_apply"},
                },
                "test_group::test_rule": {
                    "replace": {"param1": "should_apply"},
                },
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "original"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
            phase_name=None,  # No phase context
        )

        # Should match group::rule but not group::rule::phase
        assert merged["param1"] == "should_apply"

    def test_default_group_name_used(self, base_config, tmp_path):
        """Test that default_group_name is used when group_name is None."""
        config_dict = {
            **base_config,
            "default_group_name": "DefaultGroup",
            "rule_param_overrides": {
                "DefaultGroup::test_rule": {
                    "replace": {"param1": "with_default_group"},
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {"param1": "original"}
        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name=None,  # Will use default
        )

        # Should use default_group_name from config
        assert merged["param1"] == "with_default_group"


class TestComplexScenarios:
    """Test complex real-world scenarios."""

    def test_ignore_patterns_realistic_scenario(self, base_config, tmp_path):
        """Test realistic ignore_patterns override scenario."""
        config_dict = {
            **base_config,
            "default_group_name": "Skills",
            # Global validator override: ignore common files for all file validators
            "validator_param_overrides": {
                "core:file_exists": {
                    "merge": {
                        "ignore_patterns": [
                            "**/.git/**",
                            "**/.venv/**",
                            "**/__pycache__/**",
                        ]
                    },
                }
            },
            # Rule-specific override: add project-specific ignores
            "rule_param_overrides": {
                "Skills::skill_validation": {
                    "merge": {
                        "ignore_patterns": [
                            "**/test_*.md",
                            "**/draft_*.md",
                        ]
                    },
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        # Base params from rule definition
        base_params = {"ignore_patterns": ["*.pyc"]}

        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="skill_validation",
            group_name="Skills",
        )

        # Should have all patterns in order: base → validator → rule
        expected_patterns = [
            "*.pyc",  # Base
            "**/.git/**",  # Validator
            "**/.venv/**",
            "**/__pycache__/**",
            "**/test_*.md",  # Rule
            "**/draft_*.md",
        ]
        assert merged["ignore_patterns"] == expected_patterns

    def test_multiple_params_multiple_strategies(self, base_config, tmp_path):
        """Test complex scenario with multiple params and strategies."""
        config_dict = {
            **base_config,
            "validator_param_overrides": {
                "core:file_exists": {
                    "replace": {
                        "max_size": 10000,
                        "strict_mode": True,
                    },
                    "merge": {
                        "ignore_patterns": ["*.cache"],
                        "options": {"timeout": 30},
                    },
                }
            },
            "rule_param_overrides": {
                "test_group::test_rule": {
                    "replace": {
                        "min_count": 5,
                    },
                    "merge": {
                        "ignore_patterns": ["*.temp"],
                        "options": {"retries": 3},
                    },
                }
            },
        }
        config = DriftConfig(**config_dict)
        analyzer = DriftAnalyzer(config, tmp_path)

        base_params = {
            "max_size": 5000,
            "min_count": 1,
            "strict_mode": False,
            "ignore_patterns": ["*.log"],
            "options": {"verbose": True, "timeout": 60},
        }

        merged = analyzer._merge_params(
            base_params=base_params,
            validator_type="core:file_exists",
            rule_name="test_rule",
            group_name="test_group",
        )

        # Verify all replacements
        assert merged["max_size"] == 10000  # Validator replace
        assert merged["min_count"] == 5  # Rule replace
        assert merged["strict_mode"] is True  # Validator replace

        # Verify list merges (base → validator → rule)
        assert merged["ignore_patterns"] == ["*.log", "*.cache", "*.temp"]

        # Verify dict merges (base → validator → rule)
        assert merged["options"] == {
            "verbose": True,  # From base
            "timeout": 30,  # From validator (overrides base)
            "retries": 3,  # From rule
        }
