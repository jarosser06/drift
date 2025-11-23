"""Utilities for extracting project context from various agent tool setups."""

import json
from pathlib import Path
from typing import Dict, List, Optional


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
