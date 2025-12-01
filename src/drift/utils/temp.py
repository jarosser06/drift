"""Temporary directory management for drift analysis."""

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from drift.core.types import Rule


class TempManager:
    """Manages temporary storage for analysis intermediate results."""

    def __init__(self, temp_dir: str):
        """Initialize temp manager.

        Args:
            temp_dir: Path to temporary directory
        """
        self.temp_dir = Path(temp_dir).expanduser()
        self.analysis_dir: Optional[Path] = None

    def create_analysis_dir(self, session_id: str) -> Path:
        """Create a temporary directory for an analysis session.

        Args:
            session_id: Unique identifier for this analysis session

        Returns:
            Path to the created analysis directory
        """
        self.analysis_dir = self.temp_dir / f"analysis_{session_id}"
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        return self.analysis_dir

    def save_pass_result(
        self,
        conversation_id: str,
        rule_type: str,
        rules: List[Rule],
    ) -> Path:
        """Save results from a single analysis pass.

        Args:
            conversation_id: ID of the conversation analyzed
            rule_type: Type of drift learning
            rules: List of rules found

        Returns:
            Path to saved result file
        """
        if not self.analysis_dir:
            raise ValueError("Analysis directory not created. Call create_analysis_dir() first.")

        # Create subdirectory for this conversation
        conv_dir = self.analysis_dir / conversation_id
        conv_dir.mkdir(exist_ok=True)

        # Save rules to JSON file
        result_file = conv_dir / f"{rule_type}.json"
        with open(result_file, "w") as f:
            json.dump(
                [learning.model_dump(mode="python") for learning in rules],
                f,
                indent=2,
                default=str,
            )

        return result_file

    def load_pass_result(
        self,
        conversation_id: str,
        rule_type: str,
    ) -> List[Rule]:
        """Load results from a previous analysis pass.

        Args:
            conversation_id: ID of the conversation
            rule_type: Type of drift learning

        Returns:
            List of rules from the pass
        """
        if not self.analysis_dir:
            raise ValueError("Analysis directory not created.")

        result_file = self.analysis_dir / conversation_id / f"{rule_type}.json"

        if not result_file.exists():
            return []

        with open(result_file, "r") as f:
            data = json.load(f)
            return [Rule.model_validate(item) for item in data]

    def get_all_learnings(self, conversation_id: str) -> List[Rule]:
        """Get all rules for a conversation across all passes.

        Args:
            conversation_id: ID of the conversation

        Returns:
            Combined list of all rules
        """
        if not self.analysis_dir:
            return []

        conv_dir = self.analysis_dir / conversation_id

        if not conv_dir.exists():
            return []

        all_rules = []

        for result_file in conv_dir.glob("*.json"):
            with open(result_file, "r") as f:
                data = json.load(f)
                all_rules.extend([Rule.model_validate(item) for item in data])

        return all_rules

    def save_metadata(self, metadata: Dict[str, Any]) -> None:
        """Save analysis metadata.

        Args:
            metadata: Metadata dictionary to save
        """
        if not self.analysis_dir:
            raise ValueError("Analysis directory not created.")

        metadata_file = self.analysis_dir / "metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2, default=str)

    def cleanup(self, force: bool = False) -> None:
        """Clean up temporary directory.

        Args:
            force: If True, delete even if analysis_dir is None
        """
        if self.analysis_dir and self.analysis_dir.exists():
            shutil.rmtree(self.analysis_dir)
            self.analysis_dir = None
        elif force and self.temp_dir.exists():
            # Clean entire temp directory
            shutil.rmtree(self.temp_dir)

    def preserve_for_debugging(self) -> Optional[Path]:
        """Preserve temp directory for debugging instead of cleaning up.

        Returns:
            Path to preserved directory or None if no analysis dir
        """
        if self.analysis_dir:
            return self.analysis_dir
        return None
