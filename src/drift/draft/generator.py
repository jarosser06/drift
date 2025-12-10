"""Prompt generator for draft functionality.

Generates AI prompts from Drift rule definitions, either using custom templates
or inferring requirements from validator phases.
"""

from pathlib import Path
from typing import Any, Dict, List

import yaml

from drift.config.models import PhaseDefinition, RuleDefinition


class PromptGenerator:
    """Generates draft prompts from rule definitions."""

    def generate(
        self,
        rule_name: str,
        rule: RuleDefinition,
        target_files: List[Path],
        project_path: Path,
    ) -> str:
        """Generate draft prompt.

        Strategy:
        1. Use rule.draft_instructions if provided (custom template)
        2. Otherwise, infer from phases and validator params
        3. Combine both if both present

        Parameters
        ----------
        rule_name : str
            Name of the rule being drafted.
        rule : RuleDefinition
            The rule definition containing validation requirements.
        target_files : List[Path]
            List of target file paths to be created.
        project_path : Path
            Root path of the project.

        Returns
        -------
        str
            Generated draft prompt as markdown text.

        Examples
        --------
        >>> generator = PromptGenerator()
        >>> prompt = generator.generate("skill_validation", rule, [Path("file.md")], Path("/proj"))
        >>> print(prompt)
        """
        # Use custom prompt if provided
        if rule.draft_instructions:
            return self._render_template(
                rule.draft_instructions,
                rule_name=rule_name,
                rule=rule,
                target_files=target_files,
                project_path=project_path,
            )

        # Infer from phases
        return self._generate_from_phases(
            rule_name=rule_name,
            rule=rule,
            target_files=target_files,
            project_path=project_path,
        )

    def _generate_from_phases(
        self,
        rule_name: str,
        rule: RuleDefinition,
        target_files: List[Path],
        project_path: Path,
    ) -> str:
        """Generate prompt by analyzing phases.

        Parameters
        ----------
        rule_name : str
            Name of the rule.
        rule : RuleDefinition
            The rule definition.
        target_files : List[Path]
            Target files to create.
        project_path : Path
            Project root path.

        Returns
        -------
        str
            Generated prompt as markdown.
        """
        sections = []

        # Header
        sections.append(f"# Draft Prompt: {rule_name}\n")
        sections.append(f"**Description**: {rule.description}\n")
        if rule.context:
            sections.append(f"**Context**: {rule.context}\n")

        # Target files
        sections.append("\n## Target Files to Create\n")
        for file_path in target_files:
            try:
                rel_path = file_path.relative_to(project_path)
            except ValueError:
                rel_path = file_path
            sections.append(f"- `{rel_path}`")

        # Requirements extracted from phases
        if rule.phases:
            requirements = self._extract_requirements(rule.phases, target_files, project_path)
            if requirements:
                sections.append("\n## Validation Requirements\n")
                sections.append("Your generated files must satisfy these requirements:\n")

                for req_type, req_details in requirements.items():
                    sections.append(f"\n### {req_type}")
                    sections.append(req_details)

        # Instructions
        sections.append("\n## Instructions\n")
        sections.append("Create the files listed above that satisfy all validation requirements.")
        sections.append(f"The files will be validated against the `{rule_name}` rule in Drift.\n")
        sections.append("You can verify your work by running:")
        sections.append("```bash")
        sections.append(f"drift --rules {rule_name} --no-llm  # Programmatic checks only")
        sections.append(f"drift --rules {rule_name}           # Full validation including LLM")
        sections.append("```")

        return "\n".join(sections)

    def _extract_requirements(
        self, phases: List[PhaseDefinition], target_files: List[Path], project_path: Path
    ) -> Dict[str, str]:
        """Extract requirements from phase definitions.

        Parameters
        ----------
        phases : List[PhaseDefinition]
            List of validation phases.
        target_files : List[Path]
            List of target file paths to be created.
        project_path : Path
            Root path of the project.

        Returns
        -------
        Dict[str, str]
            Dictionary mapping requirement type to requirement details.
        """
        requirements = {}

        for phase in phases:
            phase_type = phase.type

            # File existence requirements
            if phase_type == "core:file_exists":
                # Use actual target file instead of pattern from params
                if target_files:
                    try:
                        rel_path = target_files[0].relative_to(project_path)
                    except ValueError:
                        rel_path = target_files[0]
                    requirements["File Existence"] = f"- File must exist at: `{rel_path}`"

            # Frontmatter requirements
            elif phase_type == "core:yaml_frontmatter":
                required_fields = phase.params.get("required_fields", [])
                schema = phase.params.get("schema")

                req_parts = []
                if required_fields:
                    req_parts.append("- YAML frontmatter required with fields:")
                    for field in required_fields:
                        req_parts.append(f"  - `{field}`")

                if schema:
                    req_parts.append("\n- Schema validation:")
                    req_parts.append(f"```yaml\n{self._format_schema(schema)}\n```")

                if req_parts:
                    requirements["YAML Frontmatter"] = "\n".join(req_parts)

            # Regex pattern requirements
            elif phase_type == "core:regex_match":
                pattern = phase.params.get("pattern")
                if pattern:
                    requirements["Content Pattern"] = f"- Must match regex: `{pattern}`"

            # List match requirements
            elif phase_type == "core:list_match":
                expected_items = phase.params.get("expected_items", [])
                if expected_items:
                    req_parts = ["- Must contain these items:"]
                    for item in expected_items:
                        req_parts.append(f"  - `{item}`")
                    requirements["Required Items"] = "\n".join(req_parts)

            # File size requirements
            elif phase_type == "core:file_size":
                max_size = phase.params.get("max_size")
                min_size = phase.params.get("min_size")
                req_parts = []
                if max_size:
                    req_parts.append(f"- Maximum size: {max_size} bytes")
                if min_size:
                    req_parts.append(f"- Minimum size: {min_size} bytes")
                if req_parts:
                    requirements["File Size"] = "\n".join(req_parts)

            # Token count requirements
            elif phase_type == "core:token_count":
                max_tokens = phase.params.get("max_tokens")
                min_tokens = phase.params.get("min_tokens")
                req_parts = []
                if max_tokens:
                    req_parts.append(f"- Maximum tokens: {max_tokens}")
                if min_tokens:
                    req_parts.append(f"- Minimum tokens: {min_tokens}")
                if req_parts:
                    requirements["Token Count"] = "\n".join(req_parts)

            # Block line count requirements
            elif phase_type == "core:block_line_count":
                max_lines = phase.params.get("max_lines")
                block_pattern = phase.params.get("block_pattern")
                if max_lines and block_pattern:
                    requirements["Block Size"] = (
                        f"- Code blocks matching `{block_pattern}` "
                        f"must not exceed {max_lines} lines"
                    )

            # Markdown link validation
            elif phase_type == "core:markdown_link":
                requirements["Links"] = "- All markdown links must be valid (no broken links)"

            # JSON schema validation
            elif phase_type == "core:json_schema":
                schema = phase.params.get("schema")
                if schema:
                    formatted_schema = self._format_schema(schema)
                    requirements["JSON Schema"] = (
                        f"- Must be valid JSON matching schema:\n"
                        f"```yaml\n{formatted_schema}\n```"
                    )

            # YAML schema validation
            elif phase_type == "core:yaml_schema":
                schema = phase.params.get("schema")
                if schema:
                    formatted_schema = self._format_schema(schema)
                    requirements["YAML Schema"] = (
                        f"- Must be valid YAML matching schema:\n"
                        f"```yaml\n{formatted_schema}\n```"
                    )

            # Prompt-based requirements
            elif phase_type == "prompt":
                if phase.prompt:
                    prompt_summary = self._summarize_prompt(phase.prompt)
                    if phase.name:
                        req_name = phase.name.replace("_", " ").title()
                        requirements[req_name] = prompt_summary
                    else:
                        requirements["Quality Requirements"] = prompt_summary

        return requirements

    def _summarize_prompt(self, prompt: str) -> str:
        """Extract key requirements from LLM prompt.

        Parameters
        ----------
        prompt : str
            The LLM prompt text.

        Returns
        -------
        str
            Summarized requirements.
        """
        # Extract lines with "MUST", "REQUIRED", or bullet points
        lines = prompt.split("\n")
        key_reqs = []
        for line in lines:
            line_upper = line.upper()
            if "MUST" in line_upper or "REQUIRED" in line_upper:
                key_reqs.append(line.strip())
            elif line.strip().startswith("-") or line.strip().startswith("*"):
                key_reqs.append(line.strip())

        if key_reqs:
            # Limit to 5 most important requirements
            return "\n".join(f"  {req}" for req in key_reqs[:5])
        else:
            # Fallback: take first few non-empty lines
            non_empty = [line.strip() for line in lines if line.strip()]
            if non_empty:
                return "\n".join(f"  {line}" for line in non_empty[:3])
            return "  See rule definition for detailed requirements"

    def _render_template(
        self,
        template: str,
        rule_name: str,
        rule: RuleDefinition,
        target_files: List[Path],
        project_path: Path,
    ) -> str:
        """Render template with placeholders.

        Supported placeholders:
        - {rule_name}
        - {description}
        - {context}
        - {bundle_type}
        - {file_path} (first target file)
        - {file_paths} (all target files, comma-separated)

        Parameters
        ----------
        template : str
            Template string with placeholders.
        rule_name : str
            Name of the rule.
        rule : RuleDefinition
            The rule definition.
        target_files : List[Path]
            Target files to create.
        project_path : Path
            Project root path.

        Returns
        -------
        str
            Rendered template.
        """
        result = template

        # Prepare file paths
        rel_paths = []
        for file_path in target_files:
            try:
                rel_path = file_path.relative_to(project_path)
            except ValueError:
                rel_path = file_path
            rel_paths.append(str(rel_path))

        # Replace placeholders
        replacements = {
            "{rule_name}": rule_name,
            "{description}": rule.description,
            "{context}": rule.context or "",
            "{bundle_type}": rule.document_bundle.bundle_type if rule.document_bundle else "",
            "{file_path}": rel_paths[0] if rel_paths else "",
            "{file_paths}": ", ".join(rel_paths),
        }

        for placeholder, value in replacements.items():
            if placeholder in result:
                result = result.replace(placeholder, value)

        return result

    def _format_schema(self, schema: Dict[str, Any]) -> str:
        """Format JSON schema for display.

        Parameters
        ----------
        schema : Dict[str, Any]
            JSON schema dict.

        Returns
        -------
        str
            YAML-formatted schema.
        """
        try:
            return yaml.dump(schema, default_flow_style=False, sort_keys=False)
        except Exception:
            return str(schema)
