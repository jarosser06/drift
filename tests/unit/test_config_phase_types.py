"""Test that all phases have type declarations."""

from pathlib import Path

from drift.config.loader import ConfigLoader


class TestPhaseTypes:
    """Test that all phases have required type field."""

    def test_all_phases_must_have_type_field(self):
        """Test that every phase in every drift learning type has a type field."""
        loader = ConfigLoader()
        config = loader.load_config(Path(".drift.yaml"))

        missing_types = []

        for rule_name, rule_config in config.drift_learning_types.items():
            phases = getattr(rule_config, "phases", None)
            if not phases:
                continue

            for i, phase in enumerate(phases):
                phase_type = getattr(phase, "type", None)
                if not phase_type:
                    missing_types.append(
                        (rule_name, i, phase.name if hasattr(phase, "name") else "unnamed")
                    )

        assert (
            len(missing_types) == 0
        ), f"Found {len(missing_types)} phases without type field:\n" + "\n".join(
            f"  - {rule} phase {idx} ({name})" for rule, idx, name in missing_types
        )

    def test_phase_type_must_be_valid(self):
        """Test that phase types are from the valid set."""
        VALID_PHASE_TYPES = [
            "prompt",  # LLM-based analysis
            "file_exists",
            "file_not_exists",
            "regex_match",
            "regex_not_match",
            "file_count",
            "file_size",
            "cross_file_reference",
            "list_match",
            "list_regex_match",
        ]

        loader = ConfigLoader()
        config = loader.load_config(Path(".drift.yaml"))

        invalid_types = []

        for rule_name, rule_config in config.drift_learning_types.items():
            phases = getattr(rule_config, "phases", None)
            if not phases:
                continue

            for i, phase in enumerate(phases):
                phase_type = getattr(phase, "type", None)
                if phase_type and phase_type not in VALID_PHASE_TYPES:
                    phase_name = phase.name if hasattr(phase, "name") else "unnamed"
                    invalid_types.append((rule_name, i, phase_name, phase_type))

        assert (
            len(invalid_types) == 0
        ), f"Found {len(invalid_types)} phases with invalid type:\n" + "\n".join(
            f"  - {rule} phase {idx} ({name}): '{ptype}'"
            for rule, idx, name, ptype in invalid_types
        )
