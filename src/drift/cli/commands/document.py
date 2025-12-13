"""Document command for drift CLI.

Generates documentation for Drift rules from their definitions in configuration files.
Supports both .drift_rules.yaml and .claude/rules/ formats.
"""

import html
import logging
import sys
from pathlib import Path
from typing import List, Optional

from drift.cli.logging_config import setup_logging
from drift.config.loader import ConfigLoader
from drift.config.models import DriftConfig, RuleDefinition

logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_error(message: str) -> None:
    """Print error message to stderr with red color.

    -- message: Error message to print
    """
    print(f"{RED}{message}{RESET}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print warning message to stderr with yellow color.

    -- message: Warning message to print
    """
    print(f"{YELLOW}{message}{RESET}", file=sys.stderr)


def print_success(message: str) -> None:
    """Print success message to stdout with green color.

    -- message: Success message to print
    """
    print(f"{GREEN}{message}{RESET}")


def format_rule_markdown(rule_name: str, rule_def: RuleDefinition, config: DriftConfig) -> str:
    """Format a single rule definition as markdown documentation.

    -- rule_name: Name of the rule
    -- rule_def: Rule definition object
    -- config: Full configuration object for context

    Returns formatted markdown string.
    """
    lines = []

    # Title
    lines.append(f"# {rule_name}")
    lines.append("")

    # Description
    lines.append("## Description")
    lines.append("")
    lines.append(rule_def.description)
    lines.append("")

    # Metadata
    lines.append("## Metadata")
    lines.append("")
    lines.append(f"- **Scope**: {rule_def.scope}")
    lines.append(f"- **Requires Project Context**: {rule_def.requires_project_context}")

    # Severity
    if rule_def.severity:
        lines.append(f"- **Severity**: {rule_def.severity.value}")
    else:
        # Show default severity
        default_severity = "warning" if rule_def.scope == "conversation_level" else "fail"
        lines.append(f"- **Severity**: {default_severity} (default)")

    # Group name
    group_name = rule_def.group_name or config.default_group_name
    lines.append(f"- **Group**: {group_name}")

    # Supported clients
    if rule_def.supported_clients:
        lines.append(f"- **Supported Clients**: {', '.join(rule_def.supported_clients)}")
    else:
        lines.append("- **Supported Clients**: all")

    lines.append("")

    # Context
    lines.append("## Context")
    lines.append("")
    lines.append(rule_def.context)
    lines.append("")

    # Document Bundle
    if rule_def.document_bundle:
        lines.append("## Document Bundle")
        lines.append("")
        lines.append(f"- **Bundle Type**: {rule_def.document_bundle.bundle_type}")
        lines.append(f"- **Bundle Strategy**: {rule_def.document_bundle.bundle_strategy.value}")
        lines.append("- **File Patterns**:")
        for pattern in rule_def.document_bundle.file_patterns:
            lines.append(f"  - `{pattern}`")
        if rule_def.document_bundle.resource_patterns:
            lines.append("- **Resource Patterns**:")
            for pattern in rule_def.document_bundle.resource_patterns:
                lines.append(f"  - `{pattern}`")
        lines.append("")

    # Validation Rules
    if rule_def.validation_rules:
        lines.append("## Validation Rules")
        lines.append("")
        for idx, val_rule in enumerate(rule_def.validation_rules.rules, start=1):
            lines.append(f"### {idx}. {val_rule.rule_type}")
            lines.append("")
            lines.append(f"**Description**: {val_rule.description}")
            lines.append("")
            if val_rule.params:
                lines.append("**Parameters**:")
                for param_name, param_value in val_rule.params.items():
                    lines.append(f"- `{param_name}`: {param_value}")
                lines.append("")

    # Phases
    if rule_def.phases:
        lines.append("## Phases")
        lines.append("")
        for idx, phase in enumerate(rule_def.phases, start=1):
            lines.append(f"### {idx}. {phase.name}")
            lines.append("")
            lines.append(f"- **Type**: {phase.type}")
            if phase.provider:
                lines.append(f"- **Provider**: {phase.provider}")
            if phase.model:
                lines.append(f"- **Model**: {phase.model}")
            if phase.prompt:
                lines.append("")
                lines.append("**Prompt**:")
                lines.append("")
                lines.append("```")
                lines.append(phase.prompt.strip())
                lines.append("```")
            if phase.params:
                lines.append("")
                lines.append("**Parameters**:")
                for param_name, param_value in phase.params.items():
                    lines.append(f"- `{param_name}`: {param_value}")
            if phase.available_resources:
                lines.append("")
                lines.append(f"**Available Resources**: {', '.join(phase.available_resources)}")
            lines.append("")

    # Draft Instructions
    if rule_def.draft_instructions:
        lines.append("## Draft Instructions")
        lines.append("")
        lines.append(rule_def.draft_instructions)
        lines.append("")

    return "\n".join(lines)


def format_rule_html(rule_name: str, rule_def: RuleDefinition, config: DriftConfig) -> str:
    """Format a single rule definition as HTML documentation.

    -- rule_name: Name of the rule
    -- rule_def: Rule definition object
    -- config: Full configuration object for context

    Returns formatted HTML string.
    """
    lines = []

    # Title
    lines.append(f"<h1>{html.escape(rule_name)}</h1>")
    lines.append("")

    # Description
    lines.append("<h2>Description</h2>")
    lines.append(f"<p>{html.escape(rule_def.description)}</p>")
    lines.append("")

    # Metadata
    lines.append("<h2>Metadata</h2>")
    lines.append("<ul>")
    lines.append(f"  <li><strong>Scope</strong>: {html.escape(rule_def.scope)}</li>")
    lines.append(
        f"  <li><strong>Requires Project Context</strong>: "
        f"{html.escape(str(rule_def.requires_project_context))}</li>"
    )

    # Severity
    if rule_def.severity:
        severity_value = html.escape(rule_def.severity.value)
        lines.append(f"  <li><strong>Severity</strong>: {severity_value}</li>")
    else:
        default_severity = "warning" if rule_def.scope == "conversation_level" else "fail"
        severity_text = html.escape(default_severity)
        lines.append(f"  <li><strong>Severity</strong>: {severity_text} (default)</li>")

    # Group name
    group_name = rule_def.group_name or config.default_group_name
    lines.append(f"  <li><strong>Group</strong>: {html.escape(group_name)}</li>")

    # Supported clients
    if rule_def.supported_clients:
        clients_str = ", ".join(rule_def.supported_clients)
        lines.append(f"  <li><strong>Supported Clients</strong>: {html.escape(clients_str)}</li>")
    else:
        lines.append("  <li><strong>Supported Clients</strong>: all</li>")

    lines.append("</ul>")
    lines.append("")

    # Context
    lines.append("<h2>Context</h2>")
    lines.append(f"<p>{html.escape(rule_def.context)}</p>")
    lines.append("")

    # Document Bundle
    if rule_def.document_bundle:
        lines.append("<h2>Document Bundle</h2>")
        lines.append("<ul>")
        lines.append(
            f"  <li><strong>Bundle Type</strong>: "
            f"{html.escape(rule_def.document_bundle.bundle_type)}</li>"
        )
        lines.append(
            f"  <li><strong>Bundle Strategy</strong>: "
            f"{html.escape(rule_def.document_bundle.bundle_strategy.value)}</li>"
        )
        lines.append("  <li><strong>File Patterns</strong>:")
        lines.append("    <ul>")
        for pattern in rule_def.document_bundle.file_patterns:
            lines.append(f"      <li><code>{html.escape(pattern)}</code></li>")
        lines.append("    </ul>")
        lines.append("  </li>")
        if rule_def.document_bundle.resource_patterns:
            lines.append("  <li><strong>Resource Patterns</strong>:")
            lines.append("    <ul>")
            for pattern in rule_def.document_bundle.resource_patterns:
                lines.append(f"      <li><code>{html.escape(pattern)}</code></li>")
            lines.append("    </ul>")
            lines.append("  </li>")
        lines.append("</ul>")
        lines.append("")

    # Validation Rules
    if rule_def.validation_rules:
        lines.append("<h2>Validation Rules</h2>")
        for idx, val_rule in enumerate(rule_def.validation_rules.rules, start=1):
            rule_type_escaped = html.escape(val_rule.rule_type)
            lines.append(f"<h3>{idx}. {rule_type_escaped}</h3>")
            desc_escaped = html.escape(val_rule.description)
            lines.append(f"<p><strong>Description</strong>: {desc_escaped}</p>")
            if val_rule.params:
                lines.append("<p><strong>Parameters</strong>:</p>")
                lines.append("<ul>")
                for param_name, param_value in val_rule.params.items():
                    lines.append(
                        f"  <li><code>{html.escape(param_name)}</code>: "
                        f"{html.escape(str(param_value))}</li>"
                    )
                lines.append("</ul>")

    # Phases
    if rule_def.phases:
        lines.append("<h2>Phases</h2>")
        for idx, phase in enumerate(rule_def.phases, start=1):
            lines.append(f"<h3>{idx}. {html.escape(phase.name)}</h3>")
            lines.append("<ul>")
            lines.append(f"  <li><strong>Type</strong>: {html.escape(phase.type)}</li>")
            if phase.provider:
                lines.append(f"  <li><strong>Provider</strong>: {html.escape(phase.provider)}</li>")
            if phase.model:
                lines.append(f"  <li><strong>Model</strong>: {html.escape(phase.model)}</li>")
            if phase.prompt:
                lines.append("</ul>")
                lines.append("<p><strong>Prompt</strong>:</p>")
                lines.append(f"<pre><code>{html.escape(phase.prompt.strip())}</code></pre>")
                lines.append("<ul>")
            if phase.params:
                lines.append("  <li><strong>Parameters</strong>:")
                lines.append("    <ul>")
                for param_name, param_value in phase.params.items():
                    lines.append(
                        f"      <li><code>{html.escape(param_name)}</code>: "
                        f"{html.escape(str(param_value))}</li>"
                    )
                lines.append("    </ul>")
                lines.append("  </li>")
            if phase.available_resources:
                resources_str = ", ".join(phase.available_resources)
                lines.append(
                    f"  <li><strong>Available Resources</strong>: "
                    f"{html.escape(resources_str)}</li>"
                )
            lines.append("</ul>")

    # Draft Instructions
    if rule_def.draft_instructions:
        lines.append("<h2>Draft Instructions</h2>")
        lines.append(f"<p>{html.escape(rule_def.draft_instructions)}</p>")

    return "\n".join(lines)


def document_command(
    rules: Optional[str] = None,
    all_rules: bool = False,
    output: Optional[str] = None,
    format_type: str = "markdown",
    project: Optional[str] = None,
    rules_file: Optional[List[str]] = None,
    verbose: int = 0,
) -> None:
    """Generate documentation for Drift rules.

    This command reads rule definitions from configuration and generates
    documentation in markdown or HTML format. The output is either printed
    to stdout or saved to a file.

    -- rules: Comma-separated list of rule names to document
    -- all_rules: If True, document all loaded rules
    -- output: Output file path (if None, prints to stdout)
    -- format_type: Output format ('markdown' or 'html')
    -- project: Project path (if None, uses current directory)
    -- rules_file: List of custom rules files to load
    -- verbose: Verbosity level (0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG)
    """
    setup_logging(verbose)

    try:
        # Ensure global config exists on first run
        ConfigLoader.ensure_global_config_exists()

        # Determine project path
        project_path = Path(project) if project else Path.cwd()
        if not project_path.exists():
            print_error(f"Error: Project path does not exist: {project_path}")
            sys.exit(1)

        # Load configuration
        try:
            config = ConfigLoader.load_config(project_path, rules_files=rules_file)
        except ValueError as e:
            print_error(f"Configuration error: {e}")
            sys.exit(1)

        # Determine which rules to document
        if all_rules:
            rule_names = list(config.rule_definitions.keys())
        elif rules:
            rule_names = [r.strip() for r in rules.split(",")]
        else:
            print_error("Error: Must specify either --rules or --all")
            print_error("Usage:")
            print_error("  drift document --rules skill_validation,agent_validation")
            print_error("  drift document --all")
            sys.exit(1)

        # Validate all rule names exist
        missing_rules = [r for r in rule_names if r not in config.rule_definitions]
        if missing_rules:
            print_error(f"Error: Rules not found: {', '.join(missing_rules)}")
            available_rules = ", ".join(config.rule_definitions.keys())
            print_error(f"Available rules: {available_rules}")
            sys.exit(1)

        # Generate documentation
        output_lines = []

        # Add header for multi-rule documentation
        if len(rule_names) > 1:
            if format_type == "markdown":
                output_lines.append("# Drift Rules Documentation")
                output_lines.append("")
                output_lines.append(f"Documentation for {len(rule_names)} rules.")
                output_lines.append("")
                output_lines.append("---")
                output_lines.append("")
            elif format_type == "html":
                output_lines.append("<!DOCTYPE html>")
                output_lines.append("<html>")
                output_lines.append("<head>")
                output_lines.append('  <meta charset="UTF-8">')
                output_lines.append("  <title>Drift Rules Documentation</title>")
                output_lines.append("</head>")
                output_lines.append("<body>")
                output_lines.append("  <h1>Drift Rules Documentation</h1>")
                output_lines.append(f"  <p>Documentation for {len(rule_names)} rules.</p>")
                output_lines.append("  <hr>")
                output_lines.append("")

        # Generate documentation for each rule
        for idx, rule_name in enumerate(rule_names):
            rule_def = config.rule_definitions[rule_name]

            if format_type == "markdown":
                doc = format_rule_markdown(rule_name, rule_def, config)
            elif format_type == "html":
                doc = format_rule_html(rule_name, rule_def, config)
            else:
                print_error(f"Error: Unsupported format '{format_type}'. Use 'markdown' or 'html'.")
                sys.exit(1)

            output_lines.append(doc)

            # Add separator between rules (except after last rule)
            if idx < len(rule_names) - 1:
                if format_type == "markdown":
                    output_lines.append("---")
                    output_lines.append("")
                elif format_type == "html":
                    output_lines.append("<hr>")
                    output_lines.append("")

        # Add footer for HTML
        if len(rule_names) > 1 and format_type == "html":
            output_lines.append("</body>")
            output_lines.append("</html>")

        documentation = "\n".join(output_lines)

        # Output documentation
        if output:
            output_path = Path(output)
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(documentation, encoding="utf-8")
                print_success(f"Documentation written to: {output_path}")
            except Exception as e:
                print_error(f"Error writing to file: {e}")
                sys.exit(1)
        else:
            # Print to stdout
            print(documentation)

        sys.exit(0)

    except KeyboardInterrupt:
        print_error("\nDocument interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during document")
        print_error(f"Unexpected error: {e}")
        sys.exit(1)
