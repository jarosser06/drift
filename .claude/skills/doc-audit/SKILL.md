---
name: doc-audit
description: Expert in auditing Sphinx/RST documentation for Drift project. Use when validating code examples and removing subjective language before release.
---

# Documentation Audit Skill

Learn how to audit documentation for Drift project - validate code examples and ensure objective language.

## When to Use This Skill

- Reviewing documentation before release
- Validating code examples against implementation
- Ensuring objective, factual documentation language
- Checking for outdated or incorrect examples
- Maintaining documentation quality standards

## How to Audit Documentation

### Overview of Audit Process

A complete documentation audit includes three phases:
1. **Code Example Validation** - Verify all code examples match actual implementation
2. **Subjective Language Detection** - Flag subjective or marketing language
3. **Cross-Reference Implementation** - Check against actual code using serena MCP

Work through each phase systematically for each documentation file.

## How to Validate Code Examples

### Step 1: Extract Code Examples

Look through documentation files for code blocks:

**RST files:**
```rst
.. code-block:: python

   from drift.cli import cli
   drift.analyze("log.json")
```

**Markdown files:**
```markdown
```python
from drift.cli import cli
drift.analyze("log.json")
```
```

Categorize as:
- Complete examples (should run as-is)
- Snippets (partial code for illustration)

### Step 2: Validate Imports with Serena MCP

Use `mcp__serena__find_symbol` to verify imports:

**Example validation:**
```python
# Documentation says:
from drift.cli import cli

# Verify with serena:
mcp__serena__find_symbol(
    name_path_pattern="cli",
    relative_path="src/drift/cli.py"
)
```

**Common import patterns to check:**
- `from drift.cli import ...`
- `from drift.core.analyzer import ...`
- `from drift.config.loader import ...`
- `from drift.providers import ...`
- `from drift.validation import ...`

If symbol not found, import path is incorrect.

### Step 3: Verify CLI Commands

Check all CLI examples in documentation:

**Commands to verify:**
```bash
drift                    # Basic usage
drift --no-llm           # Programmatic validation only
drift --days 7           # Analyze last 7 days
drift --format json      # JSON output
drift --cwd PATH         # Working directory
drift --rules NAMES      # Specific rules
```

**How to verify:**
```bash
# Run command to check it exists and works
drift --help

# Check for specific flags
drift --help | grep -- --no-llm
drift --help | grep -- --format
```

### Step 4: Validate Configuration Examples

Check YAML configuration examples:

**Example documentation config:**
```yaml
# From docs/configuration.rst
drift_rules:
  provider: anthropic
  model: claude-3-sonnet-20240229
```

**Validate with serena:**
```python
# Check config structure
mcp__serena__find_symbol(
    name_path_pattern="Config",
    relative_path="src/drift/config"
)

# Read actual config loading code
mcp__serena__find_symbol(
    name_path_pattern="load_config",
    relative_path="src/drift/config",
    include_body=True
)
```

Look for:
- Correct parameter names
- Valid provider values (anthropic, bedrock, claude-code)
- Correct structure and nesting

### Step 5: Verify API Methods

Use serena to check that documented APIs exist:

**Documentation example:**
```python
analyzer = Analyzer(config_path=".drift.yaml")
results = analyzer.analyze()
```

**Verify with serena:**
```python
# Find Analyzer class
mcp__serena__find_symbol(
    name_path_pattern="Analyzer",
    relative_path="src/drift",
    depth=1  # Include methods
)

# Check analyze method specifically
mcp__serena__find_symbol(
    name_path_pattern="Analyzer/analyze",
    relative_path="src/drift",
    include_body=True
)
```

Compare:
- Method exists
- Parameters match
- Return type matches
- No deprecated methods

### Step 6: Check Example Completeness

For each code example, verify:

**Complete example checklist:**
- [ ] All imports included
- [ ] No undefined variables
- [ ] No missing context
- [ ] Could theoretically run (or marked as snippet)
- [ ] Error handling shown (where relevant)

**Example of incomplete documentation:**
```python
# BAD - missing imports and context
result = analyzer.analyze()
print(result)
```

**Should be:**
```python
# GOOD - complete example
from drift.core.analyzer import Analyzer

analyzer = Analyzer(config_path=".drift.yaml")
result = analyzer.analyze()
print(result)
```

## How to Detect Subjective Language

### Step 1: Scan for Subjective Adjectives/Adverbs

Search documentation for these patterns:

**Common subjective words:**
- "easily", "simply", "just"
- "obviously", "clearly"
- "powerful", "elegant", "beautiful"
- "amazing", "best", "better"
- "great", "excellent"
- "effortlessly", "seamlessly"
- "straightforward"

**How to search:**
```bash
grep -n "easily\|simply\|just\|powerful" docs/*.rst
```

Or use serena:
```python
mcp__serena__search_for_pattern(
    substring_pattern="easily|simply|just|powerful",
    relative_path="docs/"
)
```

### Step 2: Flag Marketing Language

**Bad - marketing language:**
```
Drift provides a powerful validation system that makes
it easy to ensure code quality.
```

**Good - objective technical description:**
```
Drift validates project structure using rule-based checks.
Validation runs programmatically without LLM calls.
```

**What to look for:**
- Superlatives without data ("best", "most powerful")
- Emotional appeals
- Vague benefit claims
- Comparisons without specifics

### Step 3: Identify False User Behavior Claims

**CRITICAL - never claim user behavior without data:**

**Bad examples:**
```
Most users run drift --no-llm in CI/CD
Many teams use this for code review
Typically developers check this daily
Users commonly integrate with GitHub Actions
```

**Good alternatives:**
```
drift --no-llm runs without API calls, suitable for CI/CD
Integrates with GitHub Actions via workflow files
Can be scheduled to run periodically
```

**Prohibited phrases:**
- "most users", "most teams", "most workflows"
- "many users", "many developers"
- "typically", "commonly", "usually"
- Any claim about what users do without hard data

### Step 4: Suggest Replacements

**Pattern:** Subjective claim → Objective fact

**Example 1:**
```
Bad:  "You can easily analyze AI conversations..."
Good: "You can analyze AI conversations..."
```

**Example 2:**
```
Bad:  "Drift's powerful validation system..."
Good: "Drift's validation system..."
```

**Example 3:**
```
Bad:  "Most users run validation before commits"
Good: "Validation can run before commits via pre-commit hooks"
```

## How to Use Serena MCP for Validation

### Find Symbols

```python
# Find a class
mcp__serena__find_symbol(
    name_path_pattern="Analyzer",
    relative_path="src/drift",
    depth=1  # Include methods
)

# Find specific method
mcp__serena__find_symbol(
    name_path_pattern="Analyzer/analyze",
    relative_path="src/drift",
    include_body=True  # See implementation
)
```

### Check Module Structure

```python
# Get overview of a module
mcp__serena__get_symbols_overview(
    relative_path="src/drift/cli.py",
    depth=1
)
```

Shows all functions, classes, methods in the file.

### Search for Usage Patterns

```python
# Find how something is used
mcp__serena__search_for_pattern(
    substring_pattern="Analyzer\\(",
    relative_path="tests/",
    restrict_search_to_code_files=True
)
```

Look at test files to see correct usage patterns.

### Verify Import Paths

```python
# Check if import exists
mcp__serena__find_symbol(
    name_path_pattern="cli",
    relative_path="src/drift/cli.py"
)

# If not found, import path in docs is wrong
```

## How to Generate Audit Reports

See [Report Structure](resources/report-structure.md) for:
- Complete report template
- Issue severity guidelines
- Example issue documentation

## Drift-Specific Validation Areas

### Validation Rules Documentation

Check that documented rules exist:

```python
# Find validation rules
mcp__serena__list_dir(
    relative_path="src/drift/validators",
    recursive=True
)

# Verify rule names match documentation
mcp__serena__search_for_pattern(
    substring_pattern="class.*Validator",
    relative_path="src/drift/validators"
)
```

### Provider Configuration Examples

Validate provider examples in docs:

**Anthropic configuration:**
```yaml
provider: anthropic
model: claude-3-sonnet-20240229
```

**Bedrock configuration:**
```yaml
provider: bedrock
model: anthropic.claude-v2
region: us-east-1
```

**Verify:**
```python
# Check provider loading code
mcp__serena__find_symbol(
    name_path_pattern="load_provider",
    relative_path="src/drift"
)
```

### CLI Documentation

Validate all CLI examples:

```bash
# Documented commands to check:
drift                    # Basic usage
drift --no-llm           # No LLM mode
drift --days 7           # Time range
drift --format json      # Output format
drift --rules NAMES      # Specific rules
drift --cwd PATH         # Working directory
```

**Verify each flag exists:**
```bash
drift --help | grep "flag-name"
```

## Example Workflows

See [Workflows](resources/workflows.md) for detailed audit workflows:
- Auditing a single documentation file
- Validating all CLI examples
- Complete audit workflow (3 phases)

## Resources

### 📖 [Code Validation](resources/code-validation.md)
Detailed guide for validating code examples in documentation.

**Use when:** Checking code examples, imports, and API usage in docs.

### 📖 [Workflows](resources/workflows.md)
Step-by-step workflows for different types of documentation audits.

**Use when:** Performing a documentation audit before release.

### 📖 [Report Structure](resources/report-structure.md)
Documentation audit report template with issue severity guidelines.

**Use when:** Generating an audit report with findings and recommendations.


