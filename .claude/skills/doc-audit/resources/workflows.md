# Documentation Audit Workflows

Example workflows for conducting documentation audits.

## Auditing a Single Documentation File

```python
# 1. Read the documentation file
# (Use standard Read tool or cat command)

# 2. Extract code examples
# - Identify all code blocks
# - Note line numbers

# 3. Validate each import
for import_path in imports:
    result = mcp__serena__find_symbol(
        name_path_pattern=symbol_name,
        relative_path=module_path
    )
    if not result:
        report_issue("Import not found", import_path)

# 4. Check for subjective language
subjective_words = ["easily", "simply", "powerful", ...]
for word in subjective_words:
    matches = mcp__serena__search_for_pattern(
        substring_pattern=word,
        relative_path="docs/file.rst"
    )
    for match in matches:
        report_issue("Subjective language", match)

# 5. Generate report with findings
```

## Validating All CLI Examples

```python
# 1. Extract all CLI commands from docs
commands = extract_cli_examples("docs/")

# 2. Test each command
for cmd in commands:
    # Check if command format is valid
    result = test_command(cmd)
    if not result.success:
        report_issue("Invalid CLI example", cmd)

# 3. Verify flags exist
for flag in extract_flags(commands):
    if not check_flag_exists(flag):
        report_issue("Flag doesn't exist", flag)
```

## Complete Audit Workflow

```python
# Phase 1: Code Examples
print("Phase 1: Validating code examples...")
code_issues = validate_all_code_examples("docs/")

# Phase 2: Subjective Language
print("Phase 2: Detecting subjective language...")
language_issues = detect_subjective_language("docs/")

# Phase 3: Implementation Cross-Reference
print("Phase 3: Cross-referencing implementation...")
api_issues = cross_reference_apis("docs/")

# Generate final report
generate_report(code_issues + language_issues + api_issues)
```
