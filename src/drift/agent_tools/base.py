"""Base agent loader interface for loading conversations."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from drift.core.types import Conversation, ResourceRequest, ResourceResponse, Turn


class AgentLoader(ABC):
    """Abstract base class for agent tool conversation loaders."""

    def __init__(self, agent_name: str, conversation_path: str):
        """Initialize the agent loader.

        Args:
            agent_name: Name of the agent tool
            conversation_path: Path to conversation files
        """
        self.agent_name = agent_name
        self.conversation_path = Path(conversation_path).expanduser()

    def load_conversations(
        self,
        mode: str = "latest",
        days: Optional[int] = None,
        project_path: Optional[Path] = None,
    ) -> List[Conversation]:
        """Load conversations based on selection criteria.

        This is a template method that handles mode logic, file selection,
        and error handling. Subclasses implement the file finding and parsing.

        Args:
            mode: Selection mode ('latest', 'last_n_days', 'all')
            days: Number of days (for 'last_n_days' mode)
            project_path: Optional project path to filter conversations

        Returns:
            List of loaded conversations

        Raises:
            FileNotFoundError: If conversation path doesn't exist
            ValueError: If mode is invalid
        """
        since = None

        if mode == "latest":
            # Will take only the first file after sorting
            pass
        elif mode == "last_n_days":
            if days is None:
                raise ValueError("days parameter required for 'last_n_days' mode")
            since = datetime.now() - timedelta(days=days)
        elif mode == "all":
            # No filtering
            pass
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'latest', 'last_n_days', or 'all'")

        files = self.get_conversation_files(since=since, project_path=project_path)

        if mode == "latest" and files:
            files = [files[0]]

        # Load each conversation file
        conversations = []
        for file in files:
            try:
                conversation = self._load_conversation_file(file)
                conversations.append(conversation)
            except Exception as e:
                # Log error but continue with other files
                print(f"Warning: Failed to load {file}: {e}")
                continue

        return conversations

    @abstractmethod
    def get_conversation_files(
        self,
        since: Optional[datetime] = None,
        project_path: Optional[Path] = None,
    ) -> List[Path]:
        """Get list of conversation files matching criteria.

        Args:
            since: Optional datetime to filter files modified after
            project_path: Optional project path to filter conversations

        Returns:
            List of conversation file paths
        """
        pass

    @abstractmethod
    def _parse_conversation_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a conversation file into raw data.

        Subclasses implement this to parse their specific format into a
        normalized dictionary structure.

        Args:
            file_path: Path to the conversation file

        Returns:
            Dictionary with keys:
                - session_id: str - unique session identifier
                - project_path: Optional[str] - path to the project
                - turns: List[Dict] - list of turn dictionaries, each with:
                    - user_message: str
                    - ai_message: str
                    - timestamp: Optional[datetime]
        """
        pass

    def _load_conversation_file(self, file_path: Path) -> Conversation:
        """Load a conversation file and convert to Conversation object.

        This method orchestrates parsing and conversion to normalized format.

        Args:
            file_path: Path to the conversation file

        Returns:
            Loaded Conversation object
        """
        # Parse the file using subclass-specific logic
        parsed_data = self._parse_conversation_file(file_path)

        # Build normalized Conversation object
        return self._build_conversation(file_path, parsed_data)

    def _build_conversation(self, file_path: Path, parsed_data: Dict[str, Any]) -> Conversation:
        """Build a Conversation object from parsed data.

        Args:
            file_path: Path to the conversation file
            parsed_data: Parsed conversation data from _parse_conversation_file

        Returns:
            Conversation object
        """
        # Convert turn dictionaries to Turn objects
        turns: List[Turn] = []
        for i, turn_data in enumerate(parsed_data.get("turns", []), start=1):
            turn = Turn(
                number=i,
                uuid=turn_data.get("uuid"),
                user_message=turn_data["user_message"],
                ai_message=turn_data["ai_message"],
                timestamp=turn_data.get("timestamp"),
            )
            turns.append(turn)

        # Get timestamps from turns
        started_at = turns[0].timestamp if turns else None
        ended_at = turns[-1].timestamp if turns else None

        return Conversation(
            session_id=parsed_data["session_id"],
            agent_tool=self.agent_name,
            file_path=str(file_path),
            project_path=parsed_data.get("project_path"),
            project_context=None,  # Base class doesn't extract context
            turns=turns,
            started_at=started_at,
            ended_at=ended_at,
            metadata={"turn_count": len(turns)},
        )

    def validate_conversation_path(self) -> None:
        """Validate that the conversation path exists.

        Raises:
            FileNotFoundError: If path doesn't exist with helpful message
        """
        if not self.conversation_path.exists():
            raise FileNotFoundError(
                f"Conversation path for {self.agent_name} not found: {self.conversation_path}\n"
                f"Please ensure {self.agent_name} is installed and has been used, "
                f"or update the conversation_path in your drift configuration."
            )

        if not self.conversation_path.is_dir():
            raise ValueError(
                f"Conversation path for {self.agent_name} is not a "
                f"directory: {self.conversation_path}"
            )

    def get_resource(
        self,
        resource_type: str,
        resource_id: str,
        project_path: Optional[str] = None,
    ) -> ResourceResponse:
        """Get a specific project resource.

        Args:
            resource_type: Type of resource (command, skill, agent, main_config)
            resource_id: Identifier for the resource
            project_path: Path to project root

        Returns:
            ResourceResponse with content or error
        """
        # Default implementation - subclasses override
        return ResourceResponse(
            request=ResourceRequest(
                resource_type=resource_type,
                resource_id=resource_id,
                reason="Requested by analysis",
            ),
            found=False,
            content=None,
            file_path=None,
            error=f"Resource extraction not implemented for {self.agent_name}",
        )
