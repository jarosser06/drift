# Common Completion Gaps

Common issues to watch for when validating work completion.

## Testing Gaps

### Gap 1: Missing Edge Case Tests

**Problem:**
Tests only cover the happy path.

**Example:**
```python
# Only tests valid input
def test_parse_conversation():
    conv = {"messages": [{"role": "user", "content": "hi"}]}
    result = parse_conversation(conv)
    assert len(result["messages"]) == 1
```

**Missing:**
- Empty conversation
- Invalid JSON
- Missing required fields
- Large conversations (performance)

**Fix:**
```python
def test_parse_conversation_empty():
    conv = {"messages": []}
    result = parse_conversation(conv)
    assert len(result["messages"]) == 0

def test_parse_conversation_invalid_json():
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_conversation("not json")

def test_parse_conversation_missing_messages():
    with pytest.raises(KeyError, match="messages"):
        parse_conversation({"other": "data"})
```

### Gap 2: Low Test Coverage

**Problem:**
Coverage is below 90% threshold.

**Identify:**
```bash
./test.sh --coverage
# Look for "Missing" column showing untested lines
```

**Fix:**
1. Find untested code in coverage report
2. Add tests for those code paths
3. Focus on error handling and edge cases
4. Re-run coverage

### Gap 3: Tests Don't Actually Test Behavior

**Problem:**
Tests check implementation details, not actual behavior.

**Example (Bad):**
```python
def test_detector():
    detector = DriftDetector()
    assert detector.client is not None  # Tests internal state
    assert hasattr(detector, '_parse_response')  # Tests implementation
```

**Fix (Good):**
```python
def test_detector_finds_incomplete_work():
    detector = DriftDetector()
    conv = load_fixture('conv_with_incomplete_work.json')

    result = detector.detect('incomplete_work', conv)

    assert len(result) > 0
    assert 'incomplete' in result[0].lower()
```

### Gap 4: Insufficient Integration Tests

**Problem:**
Unit tests pass but workflow doesn't work end-to-end.

**Example:**
All components tested individually but not together.

**Fix:**
Add integration tests in `tests/integration/`:
```python
def test_full_analysis_workflow():
    """Test complete analysis from CLI to output."""
    runner = CliRunner()
    result = runner.invoke(
        main,
        ['analyze', 'test.json', '--drift-type', 'incomplete_work']
    )

    assert result.exit_code == 0
    assert 'incomplete_work' in result.output
    assert 'Summary:' in result.output
```

---

## Code Quality Gaps

### Gap 5: Inline Imports

**Problem:**
Imports not at top of file.

**Example (Wrong):**
```python
def analyze_file(path: str):
    from drift.core.parser import parse_conversation  # WRONG!
    return parse_conversation(path)
```

**Fix:**
```python
from drift.core.parser import parse_conversation

def analyze_file(path: str):
    return parse_conversation(path)
```

**Why this matters:**
- Violates PEP 8 and python-basics skill
- Critical blocker in code review

### Gap 6: Missing Type Hints

**Problem:**
Public functions lack type annotations.

**Example (Incomplete):**
```python
def detect_drift(conversation, drift_type):
    # Missing type hints
    pass
```

**Fix:**
```python
def detect_drift(
    conversation: dict,
    drift_type: str
) -> list[str]:
    """Detect drift in conversation."""
    pass
```

### Gap 7: Poor Error Handling

**Problem:**
Errors are caught too broadly or not at all.

**Example (Bad):**
```python
try:
    data = json.load(f)
except Exception:  # Too broad
    return None
```

**Fix:**
```python
try:
    data = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"Config not found: {path}")
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid JSON in {path}: {e}")
```

### Gap 8: Uncommented Complexity

**Problem:**
Complex logic without explanation.

**When to add comments:**
- Non-obvious algorithms
- Workarounds for bugs/limitations
- Performance optimizations
- Business logic constraints

**Example:**
```python
# Process types sequentially to avoid rate limiting.
# Parallel processing caused 429 errors with >3 types.
for drift_type in drift_types:
    result = analyze_type(drift_type)
    results.append(result)
```

---

## Documentation Gaps

### Gap 9: Missing Docstrings

**Problem:**
Public functions without docstrings.

**Example (Missing):**
```python
def detect_drift(conversation: dict, drift_type: str) -> list[str]:
    # No docstring!
    pass
```

**Fix:**
```python
def detect_drift(
    conversation: dict,
    drift_type: str
) -> list[str]:
    """Detect specific drift type in conversation.

    Performs single-pass LLM analysis to identify instances
    of the specified drift type.

    -- conversation: Parsed conversation log dictionary
    -- drift_type: Type of drift to detect (e.g., 'incomplete_work')

    Returns list of detected drift instances with descriptions.
    Raises ValueError if drift_type is not recognized.
    """
    pass
```

### Gap 10: README Not Updated

**Problem:**
New feature added but README doesn't mention it.

**Check:**
- Does README show new CLI arguments?
- Are there usage examples?
- Is the feature listed in capabilities?

**Fix:**
Add to README:
- Quick start example using new feature
- Detailed usage in appropriate section
- Update feature list

### Gap 11: Unclear CLI Help

**Problem:**
CLI help text is vague or missing.

**Example (Bad):**
```python
@click.option('--drift-type', help='Type')  # Vague
```

**Fix:**
```python
@click.option(
    '--drift-type',
    multiple=True,
    help='Drift type to detect. Can specify multiple times. '
         'Options: incomplete_work, incorrect_tool, scope_creep, etc.'
)
```

---

## Functional Gaps

### Gap 12: Acceptance Criteria Not Fully Met

**Problem:**
Some criteria from the issue are missed.

**How to catch:**
Create traceability matrix mapping each AC to:
- Implementation (file:line)
- Test (test_file::test_name)
- Manual verification

**Example:**
```markdown
Issue #42 Acceptance Criteria:

- [x] AC1: CLI accepts multiple --drift-type ✓
  - Code: drift/cli.py:45
  - Test: test_cli.py::test_multiple_types
  - Verified: Manually tested

- [ ] AC2: Results combined in single output ✗
  - MISSING: Output shows separate reports
  - TODO: Combine in formatter.py
```

### Gap 13: Edge Cases Not Handled

**Problem:**
Code works for normal inputs but fails on edge cases.

**Common edge cases:**
- Empty inputs
- Very large inputs
- Malformed inputs
- Null/None values
- Duplicate values
- Special characters
- Boundary values

**Fix:**
Add handling and tests for each edge case.

### Gap 14: Error Messages Are Unclear

**Problem:**
Errors don't help users understand what's wrong.

**Example (Bad):**
```python
raise ValueError("Invalid input")
```

**Fix (Good):**
```python
raise ValueError(
    f"Invalid drift type '{drift_type}'. "
    f"Valid types: {', '.join(VALID_TYPES)}"
)
```

---

## Performance Gaps

### Gap 15: Obvious Performance Issues

**Problem:**
Code has clear bottlenecks.

**Common issues:**
- Nested loops with large datasets
- Repeated API calls that could be batched
- Loading large files into memory
- No caching of expensive operations

**How to identify:**
- Profile with large inputs
- Look for O(n²) or worse algorithms
- Check for redundant operations

**Fix:**
Optimize critical paths:
- Use appropriate data structures
- Cache when sensible
- Batch operations
- Stream large data

---

## Git Gaps

### Gap 16: Debug Code Still Present

**Problem:**
Temporary debug code left in.

**Look for:**
```python
print("DEBUG: ", value)  # Remove
import pdb; pdb.set_trace()  # Remove
# TODO: fix this  # Should be an issue
```

**Fix:**
Remove before committing.

### Gap 17: Unintended Changes

**Problem:**
Files changed that aren't related to the feature.

**Check:**
```bash
git diff origin/main...HEAD
```

**Look for:**
- Whitespace changes
- Reformatting of unrelated files
- Config changes
- IDE settings

**Fix:**
Revert unintended changes.

### Gap 18: Poor Commit Messages

**Problem:**
Commit messages are vague.

**Example (Bad):**
```
update code
fix bug
changes
```

**Fix (Good):**
```
Add multi-drift-type CLI support

- Added --drift-type multiple argument
- Implemented sequential processing
- Added integration tests
```

---

## Security Gaps

### Gap 19: Hardcoded Secrets

**Problem:**
API keys or credentials in code.

**Never commit:**
- API keys
- Passwords
- Tokens
- Private keys
- Database credentials

**Fix:**
Use environment variables or config files (that are .gitignored).

### Gap 20: Unsafe Input Handling

**Problem:**
User input used without validation.

**Example (Unsafe):**
```python
def load_file(user_path):
    with open(user_path) as f:  # Path traversal risk!
        return f.read()
```

**Fix:**
```python
from pathlib import Path

def load_file(user_path: str) -> str:
    path = Path(user_path).resolve()
    if not path.is_relative_to(ALLOWED_DIR):
        raise ValueError(f"Path not allowed: {user_path}")
    return path.read_text()
```

---

## Quick Gap Checklist

Before marking work as done, check for these common gaps:

**Testing:**
- [ ] Edge cases tested
- [ ] Coverage ≥ 90%
- [ ] Integration tests included

**Code Quality:**
- [ ] No inline imports
- [ ] Type hints present
- [ ] Error handling specific
- [ ] No debug code

**Documentation:**
- [ ] Docstrings complete
- [ ] README updated
- [ ] Help text clear

**Functionality:**
- [ ] All ACs met
- [ ] Edge cases handled
- [ ] Error messages clear

**Performance:**
- [ ] No obvious bottlenecks
- [ ] Tested with realistic data

**Security:**
- [ ] No hardcoded secrets
- [ ] Input validation present

**Git:**
- [ ] Clean commits
- [ ] No unintended changes
