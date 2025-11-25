"""Parameter type resolution for validation rules."""

import re
from typing import Any, Dict, List

from drift.config.models import ParamType
from drift.core.types import DocumentBundle


class ParamResolver:
    """Resolves typed parameters for validation rules."""

    def __init__(self, bundle: DocumentBundle, loader: Any = None):
        """Initialize param resolver.

        Args:
            bundle: Document bundle being validated
            loader: Optional document loader for resource access
        """
        self.bundle = bundle
        self.loader = loader
        self.project_path = bundle.project_path

    def resolve(self, param_spec: Dict[str, Any]) -> Any:
        """Resolve a parameter specification to its actual value.

        Args:
            param_spec: Parameter specification with 'type' and 'value' keys

        Returns:
            Resolved parameter value

        Raises:
            ValueError: If param type is unsupported or resolution fails
        """
        if not isinstance(param_spec, dict) or "type" not in param_spec:
            # Legacy: if not a typed param, return as-is
            return param_spec

        param_type = param_spec["type"]
        param_value = param_spec.get("value")

        if param_type == ParamType.STRING:
            if not isinstance(param_value, str):
                raise ValueError("STRING param requires string value")
            return self._resolve_string(param_value)
        elif param_type == ParamType.STRING_LIST:
            return self._resolve_string_list(param_value)
        elif param_type == ParamType.RESOURCE_LIST:
            if not isinstance(param_value, str):
                raise ValueError("RESOURCE_LIST param requires string resource type")
            return self._resolve_resource_list(param_value)
        elif param_type == ParamType.RESOURCE_CONTENT:
            if not isinstance(param_value, str):
                raise ValueError("RESOURCE_CONTENT param requires string resource spec")
            return self._resolve_resource_content(param_value)
        elif param_type == ParamType.FILE_CONTENT:
            if not isinstance(param_value, str):
                raise ValueError("FILE_CONTENT param requires string file path")
            return self._resolve_file_content(param_value)
        elif param_type == ParamType.REGEX_PATTERN:
            if not isinstance(param_value, str):
                raise ValueError("REGEX_PATTERN param requires string pattern")
            return self._resolve_regex_pattern(param_value)
        else:
            raise ValueError(f"Unsupported param type: {param_type}")

    def _resolve_string(self, value: Any) -> str:
        """Resolve STRING param type.

        Args:
            value: String value

        Returns:
            String value
        """
        if not isinstance(value, str):
            raise ValueError(f"STRING param requires string value, got {type(value)}")
        return value

    def _resolve_string_list(self, value: Any) -> List[str]:
        """Resolve STRING_LIST param type.

        Args:
            value: List of strings or comma-separated string

        Returns:
            List of strings
        """
        if isinstance(value, list):
            return [str(v) for v in value]
        elif isinstance(value, str):
            # Support comma-separated strings
            return [v.strip() for v in value.split(",")]
        else:
            raise ValueError(f"STRING_LIST param requires list or string, got {type(value)}")

    def _resolve_resource_list(self, resource_type: str) -> List[str]:
        """Resolve RESOURCE_LIST param type.

        Args:
            resource_type: Type of resource (skill, command, agent, etc.)

        Returns:
            List of resource names from project

        Raises:
            ValueError: If loader not available
        """
        if not self.loader:
            raise ValueError("RESOURCE_LIST param requires loader to be provided")

        result = self.loader.list_resources(resource_type)
        return list(result) if result else []

    def _resolve_resource_content(self, resource_spec: str) -> str:
        """Resolve RESOURCE_CONTENT param type.

        Args:
            resource_spec: Resource specification like "skill:my-skill" or "command:my-command"

        Returns:
            Content of the resource file

        Raises:
            ValueError: If resource not found or spec invalid
        """
        if ":" not in resource_spec:
            raise ValueError(f"RESOURCE_CONTENT requires 'type:name' format, got: {resource_spec}")

        resource_type, resource_name = resource_spec.split(":", 1)

        # Map resource types to file patterns
        patterns = {
            "skill": [
                f".claude/skills/{resource_name}/SKILL.md",
                f".claude/skills/{resource_name}/skill.md",
            ],
            "command": [f".claude/commands/{resource_name}.md"],
            "agent": [
                f".claude/agents/{resource_name}/AGENT.md",
                f".claude/agents/{resource_name}/agent.md",
            ],
        }

        resource_patterns = patterns.get(resource_type, [])
        if not resource_patterns:
            raise ValueError(f"Unknown resource type: {resource_type}")

        # Try each pattern
        for pattern in resource_patterns:
            file_path = self.project_path / pattern
            if file_path.exists() and file_path.is_file():
                try:
                    return file_path.read_text(encoding="utf-8")
                except Exception as e:
                    raise ValueError(f"Error reading resource {resource_spec}: {e}")

        raise ValueError(f"Resource not found: {resource_spec}")

    def _resolve_file_content(self, file_path: str) -> str:
        """Resolve FILE_CONTENT param type.

        Args:
            file_path: Relative path to file from project root

        Returns:
            Content of the file

        Raises:
            ValueError: If file not found or unreadable
        """
        full_path = self.project_path / file_path
        if not full_path.exists() or not full_path.is_file():
            raise ValueError(f"File not found: {file_path}")

        try:
            return full_path.read_text(encoding="utf-8")
        except Exception as e:
            raise ValueError(f"Error reading file {file_path}: {e}")

    def _resolve_regex_pattern(self, pattern: str) -> re.Pattern:
        """Resolve REGEX_PATTERN param type.

        Args:
            pattern: Regular expression pattern string

        Returns:
            Compiled regex pattern

        Raises:
            ValueError: If pattern is invalid
        """
        if not isinstance(pattern, str):
            raise ValueError(f"REGEX_PATTERN param requires string, got {type(pattern)}")

        try:
            return re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
