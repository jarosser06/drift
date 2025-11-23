"""Claude Code conversation loader."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from drift.agents.base import AgentLoader
from drift.core.types import Conversation
from drift.utils.project_context import ClaudeCodeContextExtractor


class ClaudeCodeLoader(AgentLoader):
    """Loader for Claude Code conversations."""

    def __init__(self, conversation_path: str):
        """Initialize Claude Code loader.

        Args:
            conversation_path: Path to Claude Code projects directory
        """
        super().__init__("claude-code", conversation_path)
        self.context_extractor = ClaudeCodeContextExtractor()

    def get_conversation_files(
        self,
        since: Optional[datetime] = None,
        project_path: Optional[Path] = None,
    ) -> List[Path]:
        """Get list of Claude Code conversation files.

        Claude Code stores conversations as *.jsonl files within project directories.

        Args:
            since: Optional datetime to filter files modified after
            project_path: Optional project path to filter conversations

        Returns:
            List of conversation file paths
        """
        self.validate_conversation_path()

        files = []

        # If project_path is specified, only look in that project
        if project_path:
            # Claude Code mangles paths: /Users/jim/Projects/foo_bar -> -Users-jim-Projects-foo-bar
            # It replaces / with - AND _ with -
            mangled_path = str(project_path).replace("/", "-").replace("_", "-")
            project_dirs = [
                d for d in self.conversation_path.iterdir() if d.is_dir() and d.name == mangled_path
            ]
        else:
            # Look in all project directories
            project_dirs = [d for d in self.conversation_path.iterdir() if d.is_dir()]

        # Find *.jsonl files in each project directory
        for project_dir in project_dirs:
            for file in project_dir.glob("*.jsonl"):
                # Filter by modification time if specified
                if since:
                    mtime = datetime.fromtimestamp(file.stat().st_mtime)
                    if mtime < since:
                        continue

                files.append(file)

        # Sort by modification time (newest first)
        files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        return files

    def _parse_conversation_file(self, file_path: Path) -> Dict[str, Any]:
        """Parse a Claude Code conversation file.

        Claude Code stores conversations as JSONL files where each line is a message.

        Args:
            file_path: Path to the conversation file

        Returns:
            Dictionary with session_id, project_path, and turns
        """
        turn_dicts: List[Dict[str, Any]] = []
        current_user_message = None
        current_user_timestamp = None
        project_path = None
        session_id = None
        current_turn_messages: List[str] = []

        def finalize_turn() -> None:
            """Finalize the current turn and add it to the turns list."""
            if current_user_message and current_turn_messages:
                turn_dicts.append(
                    {
                        "user_message": current_user_message,
                        "ai_message": "\n".join(current_turn_messages),
                        "timestamp": current_user_timestamp,
                        "uuid": None,
                    }
                )

        with open(file_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Extract session ID from sessionId field (Claude Code format)
                if not session_id and "sessionId" in message:
                    session_id = message.get("sessionId")

                # Extract project path from cwd field (Claude Code format)
                if not project_path and "cwd" in message:
                    project_path = message.get("cwd")

                # Also check for test format
                if not project_path and "project_path" in message:
                    project_path = message.get("project_path")

                # Handle both test format and real Claude Code format
                msg_type = message.get("type")

                # Real Claude Code format: message.role inside nested structure
                if msg_type in ("user", "assistant") and "message" in message:
                    role = message["message"].get("role")
                    content_list = message["message"].get("content", [])

                    # Extract text from content array
                    text_content = ""
                    for item in content_list:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text_content += item.get("text", "")

                    if role == "user" and text_content:
                        # Finalize previous turn (if exists) before starting new one
                        finalize_turn()
                        # Start new turn
                        current_user_message = text_content
                        current_user_timestamp = self._parse_timestamp(message.get("timestamp"))
                        current_turn_messages = []
                    elif role == "assistant" and text_content and current_user_message:
                        # Accumulate assistant messages for this turn
                        current_turn_messages.append(text_content)

                # Test/simple format: type and content fields
                elif msg_type == "user":
                    # Finalize previous turn (if exists) before starting new one
                    finalize_turn()
                    current_user_message = message.get("content", "")
                    current_user_timestamp = self._parse_timestamp(message.get("timestamp"))
                    current_turn_messages = []
                elif msg_type == "assistant" and current_user_message is not None:
                    content = message.get("content", "")
                    if content:
                        current_turn_messages.append(content)

        # After reading all lines, finalize any pending turn
        finalize_turn()

        # Use session ID from file content, or fall back to filename
        if not session_id:
            session_id = file_path.stem

        return {
            "session_id": session_id,
            "project_path": project_path,
            "turns": turn_dicts,
        }

    @staticmethod
    def _parse_timestamp(timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime.

        Args:
            timestamp_str: ISO format timestamp string

        Returns:
            Parsed datetime or None if parsing fails
        """
        if not timestamp_str:
            return None

        try:
            # Try ISO format
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

    def _build_conversation(self, file_path: Path, parsed_data: Dict[str, Any]) -> Conversation:
        """Build a Conversation object from parsed data with project context.

        Overrides base class to add project context extraction for Claude Code projects.

        Args:
            file_path: Path to the conversation file
            parsed_data: Parsed conversation data from _parse_conversation_file

        Returns:
            Conversation object with project_context populated
        """
        # Call parent to build base conversation
        conversation = super()._build_conversation(file_path, parsed_data)

        # Extract and add project context
        if conversation.project_path:
            project_context = self.context_extractor.extract_context(conversation.project_path)
            # Create new conversation with updated project_context
            conversation = Conversation(
                session_id=conversation.session_id,
                agent_tool=conversation.agent_tool,
                file_path=conversation.file_path,
                project_path=conversation.project_path,
                project_context=project_context,
                turns=conversation.turns,
                started_at=conversation.started_at,
                ended_at=conversation.ended_at,
                metadata=conversation.metadata,
            )

        return conversation
