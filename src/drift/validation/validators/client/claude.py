"""Claude Code-specific validators.

This module contains validators specific to Claude Code functionality.
Client-specific validators use rule types with pattern: <client>_<rule_name>
"""

import json
import re
from typing import List, Literal, Optional

from drift.config.models import ClientType, ValidationRule
from drift.core.types import DocumentBundle, DocumentRule
from drift.validation.validators.base import BaseValidator


class ClaudeSkillSettingsValidator(BaseValidator):
    """Validator for Claude Code skill settings configuration.

    Validates that .claude/settings.json contains Skill() permission entries
    for all project skills found in .claude/skills/ directory.

    Rule type: claude_skill_settings
    """

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def supported_clients(self) -> List[ClientType]:
        """Return the list of client types this validator supports."""
        return [ClientType.CLAUDE]

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate that all skills have corresponding permission entries.

        -- rule: ValidationRule with optional params
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if skills are missing permissions, None otherwise.
        """
        project_path = bundle.project_path
        skills_dir = project_path / ".claude" / "skills"
        settings_file = project_path / ".claude" / "settings.json"

        # Check if skills directory exists
        if not skills_dir.exists() or not skills_dir.is_dir():
            # No skills directory - validation passes (nothing to validate)
            return None

        # Check if settings.json exists
        if not settings_file.exists() or not settings_file.is_file():
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context="settings.json not found at .claude/settings.json",
            )

        # Read settings.json
        try:
            with settings_file.open("r") as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Invalid JSON in settings.json: {e}",
            )
        except Exception as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Failed to read settings.json: {e}",
            )

        # Extract skill names from .claude/skills/ directory
        skill_dirs = [
            d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

        if not skill_dirs:
            # No skills found - validation passes
            return None

        # Extract Skill() permissions from settings.json
        permissions = settings.get("permissions", {})
        allow_list = permissions.get("allow", [])

        # Extract skill names from Skill() entries using regex
        skill_permission_pattern = re.compile(r"Skill\(([^)]+)\)")
        permitted_skills = []
        for entry in allow_list:
            match = skill_permission_pattern.match(entry)
            if match:
                permitted_skills.append(match.group(1))

        # Check for missing permissions
        missing_skills = [skill for skill in skill_dirs if skill not in permitted_skills]

        if missing_skills:
            missing_list = ", ".join(missing_skills)
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Skills missing from permissions.allow: {missing_list}. "
                f"Add entries like 'Skill({missing_skills[0]})' to .claude/settings.json",
            )

        # All skills have permissions - validation passes
        return None

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        context: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- context: Additional context about the failure

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[".claude/settings.json"],
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class ClaudeSettingsDuplicatesValidator(BaseValidator):
    """Validator for duplicate permissions in Claude Code settings.json.

    Validates that .claude/settings.json permissions.allow list does not
    contain duplicate entries.

    Rule type: claude_settings_duplicates
    """

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def supported_clients(self) -> List[ClientType]:
        """Return the list of client types this validator supports."""
        return [ClientType.CLAUDE]

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate that permissions.allow has no duplicates.

        -- rule: ValidationRule with optional params
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if duplicates found, None otherwise.
        """
        project_path = bundle.project_path
        settings_file = project_path / ".claude" / "settings.json"

        # Check if settings.json exists
        if not settings_file.exists() or not settings_file.is_file():
            # No settings file - validation passes (nothing to validate)
            return None

        # Read settings.json
        try:
            with settings_file.open("r") as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Invalid JSON in settings.json: {e}",
            )
        except Exception as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Failed to read settings.json: {e}",
            )

        # Get permissions.allow list
        permissions = settings.get("permissions", {})
        allow_list = permissions.get("allow", [])

        if not allow_list:
            # No permissions - validation passes
            return None

        # Check for duplicates
        seen = set()
        duplicates = []
        for entry in allow_list:
            if entry in seen:
                duplicates.append(entry)
            else:
                seen.add(entry)

        if duplicates:
            duplicates_list = ", ".join(f"'{d}'" for d in duplicates)
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Duplicate permission entries found: {duplicates_list}. "
                "Remove duplicates from permissions.allow in .claude/settings.json",
            )

        # No duplicates - validation passes
        return None

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        context: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- context: Additional context about the failure

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[".claude/settings.json"],
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )


class ClaudeMcpPermissionsValidator(BaseValidator):
    """Validator for MCP server permissions in Claude Code settings.

    Validates that all MCP servers defined in .mcp.json are included
    in the .claude/settings.json permissions.allow list.

    Rule type: claude_mcp_permissions
    """

    @property
    def computation_type(self) -> Literal["programmatic", "llm"]:
        """Return computation type for this validator."""
        return "programmatic"

    @property
    def supported_clients(self) -> List[ClientType]:
        """Return the list of client types this validator supports."""
        return [ClientType.CLAUDE]

    def validate(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        all_bundles: Optional[List[DocumentBundle]] = None,
    ) -> Optional[DocumentRule]:
        """Validate that MCP servers have corresponding permissions.

        -- rule: ValidationRule with optional params
        -- bundle: Document bundle being validated
        -- all_bundles: Not used for this validator

        Returns DocumentRule if MCP servers are missing permissions, None otherwise.
        """
        project_path = bundle.project_path
        mcp_file = project_path / ".mcp.json"
        settings_file = project_path / ".claude" / "settings.json"

        # Check if .mcp.json exists
        if not mcp_file.exists() or not mcp_file.is_file():
            # No MCP config - validation passes (nothing to validate)
            return None

        # Check if settings.json exists
        if not settings_file.exists() or not settings_file.is_file():
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context="settings.json not found at .claude/settings.json but .mcp.json exists",
            )

        # Read .mcp.json
        try:
            with mcp_file.open("r") as f:
                mcp_config = json.load(f)
        except json.JSONDecodeError as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Invalid JSON in .mcp.json: {e}",
            )
        except Exception as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Failed to read .mcp.json: {e}",
            )

        # Read settings.json
        try:
            with settings_file.open("r") as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Invalid JSON in settings.json: {e}",
            )
        except Exception as e:
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"Failed to read settings.json: {e}",
            )

        # Check if enableAllProjectMcpServers is true - if so, no individual permissions needed
        if settings.get("enableAllProjectMcpServers", False):
            # All MCP servers are automatically allowed
            return None

        # Extract MCP server names from .mcp.json
        # MCP config structure: {"mcpServers": {"server-name": {...}, ...}}
        mcp_servers = mcp_config.get("mcpServers", {})
        server_names = list(mcp_servers.keys())

        if not server_names:
            # No MCP servers defined - validation passes
            return None

        # Extract mcp__ permissions from settings.json
        # MCP servers are listed as "mcp__<server-name>"
        permissions = settings.get("permissions", {})
        allow_list = permissions.get("allow", [])

        # Extract server names from mcp__ entries
        permitted_servers = []
        for entry in allow_list:
            if entry.startswith("mcp__"):
                server_name = entry[5:]  # Remove "mcp__" prefix
                permitted_servers.append(server_name)

        # Check for missing permissions
        missing_servers = [server for server in server_names if server not in permitted_servers]

        if missing_servers:
            missing_list = ", ".join(missing_servers)
            return self._create_failure_learning(
                rule=rule,
                bundle=bundle,
                context=f"MCP servers missing from permissions.allow: {missing_list}. "
                f"Add entries like 'mcp__{missing_servers[0]}' to .claude/settings.json "
                "or set 'enableAllProjectMcpServers: true'",
            )

        # All MCP servers have permissions - validation passes
        return None

    def _create_failure_learning(
        self,
        rule: ValidationRule,
        bundle: DocumentBundle,
        context: str,
    ) -> DocumentRule:
        """Create a DocumentRule for a validation failure.

        -- rule: The validation rule that failed
        -- bundle: The document bundle being validated
        -- context: Additional context about the failure

        Returns DocumentRule representing the failure.
        """
        return DocumentRule(
            bundle_id=bundle.bundle_id,
            bundle_type=bundle.bundle_type,
            file_paths=[".claude/settings.json", ".mcp.json"],
            observed_issue=rule.failure_message,
            expected_quality=rule.expected_behavior,
            rule_type="",  # Will be set by analyzer
            context=f"Validation rule: {rule.description}. {context}",
        )
