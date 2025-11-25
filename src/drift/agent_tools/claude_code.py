"""Claude Code conversation loader."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from drift.agent_tools.base import AgentLoader
from drift.core.types import Conversation, ResourceRequest, ResourceResponse


class ClaudeCodeContextExtractor:
    """Extracts project context from Claude Code project setups."""

    def extract_context(self, project_path: str) -> Optional[str]:
        """Extract project context from a Claude Code project.

        Scans for:
        - .claude/commands/ for slash commands
        - .claude/skills/ for skills
        - .mcp.json for MCP servers
        - .claude/agents/ for custom agents

        Args:
            project_path: Path to the project root

        Returns:
            Formatted string summary of available features, or None if no project path
        """
        if not project_path:
            return None

        project_root = Path(project_path)
        if not project_root.exists():
            return None

        components: Dict[str, List[str]] = {
            "commands": self._extract_commands(project_root),
            "skills": self._extract_skills(project_root),
            "mcp_servers": self._extract_mcp_servers(project_root),
            "agents": self._extract_agents(project_root),
        }

        # Only include non-empty components
        parts = []
        if components["commands"]:
            parts.append(f"Commands: {', '.join(components['commands'])}")
        if components["skills"]:
            parts.append(f"Skills: {', '.join(components['skills'])}")
        if components["mcp_servers"]:
            parts.append(f"MCP Servers: {', '.join(components['mcp_servers'])}")
        if components["agents"]:
            parts.append(f"Agents: {', '.join(components['agents'])}")

        return "; ".join(parts) if parts else None

    def _extract_commands(self, project_root: Path) -> List[str]:
        """Extract slash command names from .claude/commands/."""
        commands_dir = project_root / ".claude" / "commands"
        if not commands_dir.exists():
            return []

        commands = []
        for cmd_file in commands_dir.glob("*.md"):
            # Command name is filename without extension, prefixed with /
            commands.append(f"/{cmd_file.stem}")

        return sorted(commands)

    def _extract_skills(self, project_root: Path) -> List[str]:
        """Extract skill names from .claude/skills/."""
        skills_dir = project_root / ".claude" / "skills"
        if not skills_dir.exists():
            return []

        skills = []
        for skill_file in skills_dir.glob("*.md"):
            # Skill name is filename without extension
            skills.append(skill_file.stem)

        return sorted(skills)

    def _extract_mcp_servers(self, project_root: Path) -> List[str]:
        """Extract MCP server names from .mcp.json."""
        mcp_file = project_root / ".mcp.json"
        if not mcp_file.exists():
            return []

        try:
            with open(mcp_file, "r") as f:
                mcp_config = json.load(f)

            # MCP config has "mcpServers" key with server names
            if "mcpServers" in mcp_config:
                return sorted(mcp_config["mcpServers"].keys())
        except (json.JSONDecodeError, KeyError, IOError):
            # If parsing fails, return empty list
            pass

        return []

    def _extract_agents(self, project_root: Path) -> List[str]:
        """Extract custom agent names from .claude/agents/."""
        agents_dir = project_root / ".claude" / "agents"
        if not agents_dir.exists():
            return []

        agents = []
        for agent_file in agents_dir.glob("*.md"):
            # Agent name is filename without extension
            agents.append(agent_file.stem)

        return sorted(agents)


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

    def get_resource(
        self,
        resource_type: str,
        resource_id: str,
        project_path: Optional[str] = None,
    ) -> ResourceResponse:
        """Get Claude Code project resource."""
        if not project_path:
            return ResourceResponse(
                request=ResourceRequest(
                    resource_type=resource_type,
                    resource_id=resource_id,
                    reason="No project path",
                ),
                found=False,
                content=None,
                file_path=None,
                error="No project path provided",
            )

        project_root = Path(project_path)
        request = ResourceRequest(
            resource_type=resource_type,
            resource_id=resource_id,
            reason="Multi-phase analysis",
        )

        try:
            if resource_type == "command":
                return self._get_command(project_root, resource_id, request)
            elif resource_type == "skill":
                return self._get_skill(project_root, resource_id, request)
            elif resource_type == "agent":
                return self._get_agent(project_root, resource_id, request)
            elif resource_type == "main_config":
                return self._get_main_config(project_root, request)
            else:
                return ResourceResponse(
                    request=request,
                    found=False,
                    content=None,
                    file_path=None,
                    error=f"Unknown resource type: {resource_type}",
                )
        except Exception as e:
            return ResourceResponse(
                request=request,
                found=False,
                content=None,
                file_path=None,
                error=str(e),
            )

    def _get_command(
        self,
        project_root: Path,
        resource_id: str,
        request: ResourceRequest,
    ) -> ResourceResponse:
        """Get a slash command file."""
        # Try with and without leading slash
        clean_id = resource_id.lstrip("/")
        cmd_path = project_root / ".claude" / "commands" / f"{clean_id}.md"

        if not cmd_path.exists():
            return ResourceResponse(
                request=request,
                found=False,
                content=None,
                file_path=None,
                error=f"Command /{clean_id} not found at {cmd_path}",
            )

        content = cmd_path.read_text(encoding="utf-8")
        return ResourceResponse(
            request=request,
            found=True,
            error=None,
            content=content,
            file_path=str(cmd_path),
        )

    def _get_skill(
        self,
        project_root: Path,
        resource_id: str,
        request: ResourceRequest,
    ) -> ResourceResponse:
        """Get a skill file."""
        # Try both patterns: .claude/skills/foo.md and .claude/skills/foo/SKILL.md
        skill_file = project_root / ".claude" / "skills" / f"{resource_id}.md"
        skill_dir = project_root / ".claude" / "skills" / resource_id / "SKILL.md"

        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8")
            return ResourceResponse(
                request=request,
                found=True,
                error=None,
                content=content,
                file_path=str(skill_file),
            )
        elif skill_dir.exists():
            content = skill_dir.read_text(encoding="utf-8")
            return ResourceResponse(
                request=request,
                found=True,
                error=None,
                content=content,
                file_path=str(skill_dir),
            )
        else:
            return ResourceResponse(
                request=request,
                found=False,
                content=None,
                file_path=None,
                error=f"Skill {resource_id} not found at {skill_file} or {skill_dir}",
            )

    def _get_agent(
        self,
        project_root: Path,
        resource_id: str,
        request: ResourceRequest,
    ) -> ResourceResponse:
        """Get a custom agent file."""
        agent_path = project_root / ".claude" / "agents" / f"{resource_id}.md"

        if not agent_path.exists():
            return ResourceResponse(
                request=request,
                found=False,
                content=None,
                file_path=None,
                error=f"Agent {resource_id} not found at {agent_path}",
            )

        content = agent_path.read_text(encoding="utf-8")
        return ResourceResponse(
            request=request,
            found=True,
            error=None,
            content=content,
            file_path=str(agent_path),
        )

    def _get_main_config(
        self,
        project_root: Path,
        request: ResourceRequest,
    ) -> ResourceResponse:
        """Get main configuration file (CLAUDE.md or .mcp.json)."""
        # Try CLAUDE.md first, then .mcp.json
        claude_md = project_root / "CLAUDE.md"
        mcp_json = project_root / ".mcp.json"

        if claude_md.exists():
            content = claude_md.read_text(encoding="utf-8")
            return ResourceResponse(
                request=request,
                found=True,
                error=None,
                content=content,
                file_path=str(claude_md),
            )
        elif mcp_json.exists():
            content = mcp_json.read_text(encoding="utf-8")
            return ResourceResponse(
                request=request,
                found=True,
                error=None,
                content=content,
                file_path=str(mcp_json),
            )
        else:
            return ResourceResponse(
                request=request,
                found=False,
                content=None,
                file_path=None,
                error="No main config file (CLAUDE.md or .mcp.json) found",
            )
