# CLI Output Formatting Analysis - Drift Project

## Overview
The Drift project uses a modular output formatting system with two main formatters: Markdown and JSON. Both extend from an abstract `OutputFormatter` base class.

## Key Files
1. `/Users/jim/Projects/drift/src/drift/cli/output/formatter.py` - Base interface
2. `/Users/jim/Projects/drift/src/drift/cli/output/markdown.py` - Markdown formatting (311 lines)
3. `/Users/jim/Projects/drift/src/drift/cli/output/json.py` - JSON formatting
4. `/Users/jim/Projects/drift/src/drift/cli/commands/analyze.py` - Command orchestration (521 lines)

## CLI Output Formatting (Question 1)

### MarkdownFormatter Class (src/drift/cli/output/markdown.py)
- **Main method**: `format(result: CompleteAnalysisResult) -> str` (lines 85-240)
- **Key features**:
  - Structured output with sections: Summary, Rules Passed, Rules Errored, Failures, Warnings
  - ANSI color code support (conditional on terminal TTY)
  - Categorizes learnings by severity level
  - Supports detailed execution information

### Output Structure
1. Header: "# Drift Analysis Results"
2. Summary section with statistics
3. Rules Passed section (green)
4. Rules Errored section (yellow warning)
5. Failures section (if learnings exist)
6. Warnings section (if learnings exist)
7. Optional Test Execution Details section (if --detailed flag)

### Color Coding System (lines 17-24)
- RED ("\033[31m") for failures
- GREEN ("\033[32m") for passes
- YELLOW ("\033[33m") for warnings
- BLUE ("\033[34m") and CYAN ("\033[36m") for emphasis
- BOLD ("\033[1m") for headers
- Detection of color support via `sys.stdout.isatty()` (line 36)

## LLM-Specific Rule Details (Question 2)

### Rule Type Classification
Rules are classified based on their configuration structure:

**LLM-based rules** (lines 347-353 in analyze.py):
- Have `phases` attribute with phase type = "prompt"
- Require actual LLM calls
- Can be skipped with `--no-llm` flag

**Programmatic rules** (lines 347-356 in analyze.py):
- Have `validation_rules` configured
- OR have no LLM phases
- Run without external LLM calls

### Detection Logic (analyze.py, lines 347-356)
```python
phases = getattr(type_config, "phases", []) or []
validation_rules = getattr(type_config, "validation_rules", None)
uses_llm = any(getattr(p, "type", "prompt") == "prompt" for p in phases)
is_programmatic = validation_rules is not None or not uses_llm
```

### Severity Assignment (markdown.py, lines 60-83)
- Determined by `_get_severity()` method
- Checks config for explicit `severity` setting
- Falls back to scope-based defaults:
  - "project_level" → FAIL (red)
  - "conversation_level" → WARNING (yellow)

### Execution Details Display (markdown.py, lines 311-438)
When `--detailed` flag is used, execution details include:
- Rule name and description
- Rule context (why it's important)
- Execution context: bundle type, bundle ID, files checked
- Validation details: rule type and parameters
- Phase results (for multi-phase rules): phase number and findings count

## Rule Type Formatting Differences (Question 3)

### Failures vs Warnings (markdown.py, lines 214-230)
Rules are displayed in different sections based on severity:

**Failures Section** (red, lines 216-218):
- Learning types with project_level scope
- Explicit severity=FAIL configuration
- Formatted with RED color on section headers

**Warnings Section** (yellow, lines 222-224):
- Learning types with conversation_level scope
- Explicit severity=WARNING configuration
- Formatted with YELLOW color on section headers

**Unexpected Passes Section** (green, lines 228-230):
- Only shown if a learning type is misconfigured with severity=PASS but produces learnings
- Indicates configuration error

### Within-Type Formatting (markdown.py, lines 265-307)
Each learning type section shows:
- Learning type header (colored by scope: red/yellow)
- Type context description (uncolored)
- For each violation:
  - Session ID (with project name if available)
  - Agent Tool
  - Turn number
  - Observed behavior (colored to match scope)
  - Expected behavior (always green)
  - Frequency (one-time/repeated)
  - Workflow element
  - Context (uncolored)

## Test Execution Details Section (Question 4)

### Location in Output
- Appended at the end of main output
- Only included if `--detailed` flag is set (line 177-178, 233-238)
- Also shown in "no drift" case when detailed flag is set (lines 178-183)

### Generation in markdown.py (lines 181, 236)
```python
lines.append("## Test Execution Details")
lines.extend(self._format_execution_details(execution_details))
```

### Method: _format_execution_details() (lines 311-438)
Groups execution details by status and formats each:

**Passed Rules** (lines 328-371):
- Header: "### Passed Rules ✓" (green)
- Shows: rule name, description, context, bundle info, files checked, validation type/params

**Failed Rules** (lines 374-426):
- Header: "### Failed Rules ✗" (red)
- Same details as passed, plus phase_results if available
- Phase results show: phase number and findings count

**Errored Rules** (lines 429-436):
- Header: "### Errored Rules ⚠" (yellow)
- Shows: rule name and error description

### Data Structure
Execution details come from `result.metadata.get("execution_details", [])`:
- Each detail is a dict with keys:
  - status: "passed", "failed", or "errored"
  - rule_name, rule_description, rule_context
  - execution_context: bundle_type, bundle_id, files
  - validation_results: rule_type, params
  - phase_results (optional): list of phase execution info

## CLI Flag Integration (analyze.py)

### --detailed flag (line 177-181)
- Markdown format only
- Enables "Test Execution Details" section
- Passed to MarkdownFormatter constructor (line 496)

### --no-llm flag (lines 159-162, 314-385)
- Skips rules with phase type="prompt"
- Runs only programmatic rules
- Displays warning with skipped/running rule counts
- Filters rules based on scope (conversation vs project)

### --format flag (lines 113-118)
- Controls which formatter is used
- Options: "markdown" or "json"
- Markdown enables colors and detailed formatting
- JSON provides structured output without colors
