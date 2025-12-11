---
name: code-review
description: Expert in conducting thorough code reviews for Python projects using GitHub MCP, covering test coverage, security practices, PEP 8 compliance, and code organization. Use when reviewing code or PRs.
skills:
  - python-basics
---

# Code Review Skill

Learn how to conduct thorough, constructive code reviews using the GitHub MCP server.

## How to Review Code

### Overview of Review Process

A complete code review follows these steps:
1. **Get PR context** - Understand what's being changed
2. **Review files** - Check code quality, tests, docs
3. **Identify issues** - Flag problems by severity
4. **Provide feedback** - Constructive, specific, research-backed
5. **Submit review** - Approve, request changes, or comment

## How to Start a Code Review

### Step 1: Get PR Details

```python
# Fetch PR information
pr = mcp__github__get_pull_request(
    owner="jarosser06",
    repo="drift",
    pull_number=42
)

# Review key information:
print(f"Title: {pr['title']}")
print(f"Description: {pr['body']}")
print(f"Author: {pr['user']['login']}")
print(f"Base branch: {pr['base']['ref']}")
print(f"Head branch: {pr['head']['ref']}")
```

Key information to note:
- What issue does this address?
- What's the scope of changes?
- Are there related PRs?

### Step 2: Get Changed Files

```python
# Fetch list of changed files
files = mcp__github__get_pull_request_files(
    owner="jarosser06",
    repo="drift",
    pull_number=42
)

# Review files:
for file in files:
    print(f"{file['filename']}: +{file['additions']} -{file['deletions']}")
    print(f"Status: {file['status']}")  # added, modified, removed
```

Categorize files:
- **Core logic** - src/drift/
- **Tests** - tests/
- **Documentation** - README.md, docs/
- **Configuration** - .drift.yaml, pyproject.toml

### Step 3: Check CI Status

```python
# Get status checks
status = mcp__github__get_pull_request_status(
    owner="jarosser06",
    repo="drift",
    pull_number=42
)

print(f"Status: {status['state']}")  # success, pending, failure
print("Check runs:")
for check in status.get('statuses', []):
    print(f"  {check['context']}: {check['state']}")
```

Verify:
- [ ] All CI checks passing
- [ ] Tests pass
- [ ] Linters pass
- [ ] Coverage meets threshold

## How to Review Different Aspects

### How to Review Code Quality

**What to look for:**
- Clear, readable code
- Descriptive variable/function names
- No code duplication
- Appropriate abstraction
- Consistent with codebase style

**Example review comments:**

**Good - specific and constructive:**
```
In drift/analyzer.py:45

The variable name `d` is unclear. Consider renaming to `detector`
for better readability:

```python
for detector in self.detectors:
    results.append(detector.analyze(conversation))
```
```

**Avoid vague feedback:**
```
The code quality could be better.
```

### How to Review Architecture

**What to look for:**
- Proper separation of concerns
- Follows existing patterns
- Scalable design
- Clear module boundaries
- Good error handling

**Example review comments:**

**Good - explains reasoning:**
```
In drift/detector.py:120-150

This function is doing three distinct things:
1. Building the prompt
2. Calling the LLM
3. Parsing the response

Consider splitting into separate methods:
- `_build_prompt(conversation)` → str
- `_call_llm(prompt)` → dict
- `_parse_response(response)` → List[DriftInstance]

Benefits:
- Easier to test each step independently
- Can swap LLM providers more easily
- More reusable components
```

### How to Review Tests

**What to check:**
- Unit tests for new code
- Edge cases covered
- Clear test names
- Proper mocks/fixtures
- Coverage report

**Example review comments:**

**Good - specific gap identified:**
```
In tests/test_analyzer.py

Tests cover the happy path well, but missing edge cases:

1. What happens with empty conversation logs?
2. How does it handle malformed JSON?
3. What if LLM returns unexpected format?

Please add tests for these scenarios:

```python
def test_analyze_empty_conversation():
    """Test analyzer handles empty conversation gracefully."""
    result = analyzer.analyze({"messages": []})
    assert result == []

def test_analyze_malformed_json():
    """Test analyzer handles malformed input."""
    with pytest.raises(ValueError, match="Invalid conversation"):
        analyzer.analyze({"invalid": "structure"})
```
```

**Check coverage:**
```python
# Review coverage report from CI
# Look for uncovered lines
# Ensure critical paths are tested
```

### How to Review Documentation

**What to check:**
- Docstrings on public functions
- Parameters documented
- Return values described
- Examples for complex features
- Configuration docs updated

**Example review comments:**

**Good - identifies missing documentation:**
```
In drift/validators.py:78

The new `CustomValidator` class is missing a docstring. Please add:

```python
class CustomValidator(BaseValidator):
    """Validates custom rules defined by users.

    Loads validation rules from .drift_rules.yaml and applies them
    to project files. Supports regex patterns, file paths, and
    content validation.

    -- config_path: Path to .drift_rules.yaml
    -- strict_mode: If True, fail on first violation

    Returns:
        List of ValidationResult objects
    """
```
```

### How to Review Security

**What to check:**
- No hardcoded credentials
- Input validation
- Safe file path handling
- API key security
- No command injection risks

**Example review comments:**

**Good - identifies security issue:**
```
In drift/utils.py:45

SECURITY ISSUE: This code is vulnerable to path traversal:

```python
# Current (vulnerable):
file_path = f"/logs/{user_input}.json"
with open(file_path) as f:
    data = f.read()
```

An attacker could use `../../../etc/passwd` as input.

Fix:
```python
from pathlib import Path

# Resolve and validate path
log_dir = Path("/logs").resolve()
file_path = (log_dir / user_input).with_suffix(".json").resolve()

# Ensure path is within log_dir
if not file_path.is_relative_to(log_dir):
    raise ValueError("Invalid log file path")
```
```

## How to Research Recommendations

**CRITICAL REQUIREMENT**: Before making ANY recommendation, you MUST:
1. Research using authoritative sources (Python docs, library docs, PEPs, project docs)
2. Verify against official documentation using mcp__context7 tools
3. Include source citations in your feedback

This ensures recommendations are trustworthy and verifiable, not based on assumptions.

### How to Use Context7 MCP for Research

```python
# Step 1: Resolve library ID
library_result = mcp__context7__resolve_library_id(
    libraryName="pytest"
)

library_id = library_result["libraries"][0]["id"]

# Step 2: Get documentation
docs = mcp__context7__get_library_docs(
    context7CompatibleLibraryID=library_id,
    topic="fixtures",
    mode="code"
)

# Step 3: Review docs and cite in your recommendation
```

### Example: Research-Backed Recommendation

**Before recommending a pattern, research it:**

```python
# Want to recommend pytest fixtures? Research first:
pytest_docs = mcp__context7__get_library_docs(
    context7CompatibleLibraryID="/pytest/pytest",
    topic="fixture scopes",
    mode="code"
)
```

**Then provide research-backed feedback:**
```
In tests/conftest.py:23

Consider using `pytest.fixture(scope="session")` for the database
connection fixture. According to pytest documentation, session-scoped
fixtures are initialized once per test session, which improves
performance by avoiding repeated setup.

Source: pytest official docs - Fixture Scopes (via Context7)

Example:
```python
@pytest.fixture(scope="session")
def db_connection():
    """Database connection shared across all tests."""
    conn = create_connection()
    yield conn
    conn.close()
```
```

**Never make recommendations without research:**
```
❌ BAD: "You should probably use a session fixture here, it's faster."
✅ GOOD: Research pytest docs, then explain with citation
```

## How to Provide Constructive Feedback

See [Feedback Examples](resources/feedback-examples.md) for detailed guidance on:
- Being specific and actionable
- Explaining the why
- Offering solutions
- Prioritizing issues (critical, important, minor)
- Research-backed recommendations

## How to Prioritize Issues

See [Prioritization Guide](resources/prioritization.md) for detailed guidance on:
- Critical issues (must fix before merge)
- Important issues (should fix)
- Minor issues (nice to have)
- Example comments for each priority level


## Review Checklist

See [Review Checklist](resources/checklist.md) for complete checklists covering:
- Before starting review
- During review (code quality, architecture, testing, docs, security, performance)
- Before submitting review

## Common Issues to Watch For

### Inline Imports

```python
# ❌ BAD - inline import
def analyze_conversation():
    from drift.detector import DriftDetector
    detector = DriftDetector()
    ...

# ✅ GOOD - import at top
from drift.detector import DriftDetector

def analyze_conversation():
    detector = DriftDetector()
    ...
```

### Missing Edge Cases in Tests

```python
# Common missing tests:
- Empty input ([], "", {}, None)
- Invalid input (malformed JSON, wrong types)
- Boundary values (0, -1, MAX_VALUE)
- Error conditions (file not found, API errors)
```

### Insufficient Error Handling

```python
# ❌ BAD - catches everything
try:
    process_data()
except:
    pass

# ✅ GOOD - specific exceptions
try:
    process_data()
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    raise
except JSONDecodeError as e:
    logger.error(f"Invalid JSON: {e}")
    raise ValueError(f"Malformed data: {e}")
```

### Missing Documentation Updates

When code changes, check if documentation needs updates:
- [ ] Docstrings match new parameters
- [ ] README reflects new features
- [ ] CLI help text updated
- [ ] Configuration docs current

## Example Workflows

See [Workflows](resources/workflows.md) for detailed PR review workflows including:
- Complete PR review workflow (7 steps)
- Quick review workflow for small PRs
- How to submit reviews (approve, request changes, comment)

## Resources

### 📖 [Review Checklist](resources/checklist.md)
Comprehensive code review checklist covering quality, testing, security, and more.

**Use when:** Performing a code review to ensure nothing is missed.

### 📖 [Common Issues](resources/common-issues.md)
Anti-patterns and common problems to watch for in Drift code.

**Use when:** Looking for specific problems or learning what to avoid.

### 📖 [Feedback Examples](resources/feedback-examples.md)
Examples of constructive, specific code review feedback.

**Use when:** Writing review comments or learning how to give better feedback.

### 📖 [Workflows](resources/workflows.md)
Complete and quick PR review workflows with MCP examples.

**Use when:** Conducting a full PR review or submitting review feedback via MCP.

### 📖 [Prioritization Guide](resources/prioritization.md)
How to prioritize issues by severity (critical, important, minor).

**Use when:** Determining which issues must be fixed before merge and which are optional.
