---
name: test-strategy
description: Plans pytest test strategies for Drift's 90%+ coverage requirement using coverage analysis, edge case identification, and test suite design. Use when determining what tests to write, analyzing coverage gaps, or planning test strategies.
skills:
  - testing
  - python-basics
---

# Test Strategy Skill

Learn how to plan comprehensive test coverage for the Drift project.

## When to Use This Skill

**Use test-strategy when:**
- Planning tests for a new feature or code change
- Analyzing why coverage is below 90%
- Identifying missing edge cases
- Organizing tests for a new module
- Reviewing test suites for completeness

**Use testing skill when:**
- Writing the actual pytest code
- Creating fixtures and mocks
- Running tests and interpreting results

---

## How to Identify What Tests to Write

### From Requirements to Test Cases

Follow this process:
1. **Extract Requirements** - What should the code do?
2. **Identify Behaviors** - What are all the possible behaviors?
3. **Map to Test Cases** - One test per behavior
4. **Prioritize by Risk** - Critical path first

**Example: Validator Implementation**

Given: "Create a validator that checks if code blocks exceed maximum line count"

**Step 1: Extract Requirements**
- R1: Find code blocks in markdown files
- R2: Count lines in each code block
- R3: Compare against max_count parameter
- R4: Return None if under limit
- R5: Return failure if over limit
- R6: Handle files without code blocks

**Step 2: Map Behaviors to Tests**
```python
# From R2, R3, R4, R5:
def test_passes_when_block_under_max():
    """Block with 50 lines, max 100."""

def test_fails_when_block_exceeds_max():
    """Block with 150 lines, max 100."""

def test_passes_when_block_equals_max():  # Boundary case!
    """Block with exactly 100 lines, max 100."""

# From R6:
def test_passes_when_no_code_blocks():
    """File with no code blocks."""

# Additional behaviors discovered:
def test_handles_empty_code_block():
    """Empty code block (no lines)."""

def test_handles_multiple_code_blocks():
    """File with multiple code blocks, one exceeds."""

def test_counts_only_block_content_not_fence():
    """Doesn't count ``` fence lines."""
```

### When to Write Each Test Type

**Unit Tests (80-90%):** Individual validators, utility functions, model validation, parsers, formatters

**Integration Tests (10-15%):** Validator with DocumentBundle, analyzer with multiple phases, config loading

**E2E Tests (<5%):** Full `drift --no-llm` workflow, complete analysis pipeline

See [Test Identification Guide](resources/test-identification.md) for examples of each type.

---

## How to Achieve Good Coverage

### Coverage ≠ Quality

**Understanding 90% coverage:**
- ✅ Means: 90% of lines are executed during tests
- ❌ Does NOT mean: 90% of behaviors are tested

### Coverage Analysis Workflow

**When coverage is below 90%:**

1. **Run coverage with missing lines**
   ```bash
   pytest --cov=src/drift --cov-report=term-missing
   ```

   Output shows:
   ```
   Name                    Stmts   Miss  Cover   Missing
   src/drift/parser.py        45      3    93%   67-69
   src/drift/detector.py     120     15    88%   45, 78-92
   ```

2. **Analyze uncovered lines**
   ```python
   # Read the file, look at lines 67-69
   # Ask: What behavior do these lines represent?
   # - Error handling?
   # - Branch condition?
   # - Edge case?
   ```

3. **Write tests for behaviors, not just line hits**
   ```python
   # BAD: Just hitting lines
   def test_coverage_filler():
       validator.validate(rule, bundle)  # Just runs the code

   # GOOD: Testing actual behavior
   def test_fails_when_schema_validation_fails():
       """Schema validation error path (lines 67-69)."""
       invalid_rule = ValidationRule(schema={})
       result = validator.validate(invalid_rule, bundle)
       assert result is not None
       assert "schema validation failed" in result.observed_issue
   ```

### Use Branch Coverage

```bash
# Check that both paths of if/else are tested
pytest --cov-branch --cov=src/drift --cov-report=term-missing
```

This ensures:
```python
# Both paths tested
if condition:
    path_a()  # Covered
else:
    path_b()  # Also covered
```

### Coverage Patterns

**Pattern 1: Test all validator outcomes**
```python
def test_passes_when_valid():           # Happy path
    """Valid input returns None."""

def test_fails_when_invalid():          # Failure path
    """Invalid input returns failure."""

def test_handles_file_not_found():      # Error path
    """Missing file raises appropriate error."""

def test_handles_missing_params():      # Configuration error
    """Missing required params detected."""
```

**Pattern 2: Test exception paths**
```python
def test_missing_package(monkeypatch):  # ImportError
    """Handles missing optional dependency."""
    monkeypatch.setattr("sys.modules", {"package": None})

def test_file_read_error(monkeypatch):  # IOError
    """Handles file read permissions error."""

def test_invalid_yaml(tmp_path):        # YAMLError
    """Handles malformed YAML gracefully."""
```

---

## How to Identify Edge Cases

### Equivalence Partitioning

**Concept:** Divide input domain into classes that should behave similarly.

**Example: Line count validator**

Input: code block line count (integer)

**Step 1: Identify Partitions**
1. No code blocks
2. Valid range (min to max)
3. Above maximum

**Step 2: Test one value from each partition + boundaries**
```python
# Partition 1: No code blocks
def test_passes_when_no_code_blocks():
    """File with no code blocks."""
    content = "# Just markdown\nNo code here"
    assert validator.check(content, max_count=100) is None

# Partition 2: Valid range
def test_passes_when_in_valid_range():
    """Code block with 50 lines (middle of range)."""
    content = "```\n" + "\n".join([f"line{i}" for i in range(50)]) + "\n```"
    assert validator.check(content, max_count=100) is None

# Partition 3: Above max
def test_fails_when_above_maximum():
    """Code block with 150 lines exceeds max."""
    content = "```\n" + "\n".join([f"line{i}" for i in range(150)]) + "\n```"
    result = validator.check(content, max_count=100)
    assert result is not None
```

### Boundary Value Analysis

**Critical insight:** Bugs cluster at boundaries!

**For any constraint, test:**
1. Just below boundary
2. At boundary
3. Just above boundary

**Example: max_count = 100**
```python
def test_passes_with_99_lines():   # Just below
    """99 lines is under limit."""
    content = create_code_block(99)
    assert validator.check(content, max_count=100) is None

def test_passes_with_100_lines():  # At boundary
    """Exactly 100 lines is at limit (inclusive)."""
    content = create_code_block(100)
    assert validator.check(content, max_count=100) is None

def test_fails_with_101_lines():   # Just above
    """101 lines exceeds limit."""
    content = create_code_block(101)
    result = validator.check(content, max_count=100)
    assert result is not None
```

**Common boundaries in Drift:**
- Empty collections: `[]`, `""`, `{}`, `None`
- Zero values: `0`, `0.0`
- File boundaries: empty file, no code blocks
- String boundaries: `""`, `"a"`, very long string

### Type-Specific Edge Cases

**Strings:**
```python
@pytest.mark.parametrize("value", [
    "",           # Empty
    "   ",        # Whitespace only
    "\n\t",       # Special chars
    "a" * 10000,  # Very long
])
def test_handles_string_edge_cases(value):
    """Test with various string edge cases."""
    result = process_string(value)
    assert result is not None
```

**Lists/Arrays:**
```python
@pytest.mark.parametrize("items", [
    [],              # Empty
    [single_item],   # Single item
    many_items,      # Many items
])
def test_handles_list_edge_cases(items):
    """Test with various list sizes."""
    result = process_list(items)
    assert isinstance(result, list)
```

**Files:**
```python
def test_handles_missing_file():
    """File doesn't exist."""
    with pytest.raises(FileNotFoundError):
        load_file("missing.txt")

def test_handles_empty_file(tmp_path):
    """File exists but is empty."""
    empty = tmp_path / "empty.txt"
    empty.touch()
    result = load_file(str(empty))
    assert result == ""

def test_handles_malformed_file(tmp_path):
    """File has invalid format."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("{invalid yaml")
    with pytest.raises(ValueError):
        load_yaml(str(bad_file))
```

**Numbers:**
```python
@pytest.mark.parametrize("count", [
    0,                # Zero
    -1,               # Negative
    MAX_COUNT,        # Boundary
    MAX_COUNT + 1,    # Overflow
])
def test_handles_number_edge_cases(count):
    """Test with various number edge cases."""
    result = validate_count(count, max_count=MAX_COUNT)
    # Assertions depend on expected behavior
```

### Error Guessing Technique

Based on Drift patterns, anticipate these common edge cases:

**1. File operations:**
```python
def test_file_doesnt_exist()     # Path("missing.txt")
def test_file_is_empty()         # Empty file
def test_file_unreadable()       # Permission denied
def test_file_malformed()        # Invalid content
```

**2. YAML/JSON parsing:**
```python
def test_unclosed_frontmatter()  # Missing ---
def test_invalid_yaml_syntax()   # {bad: yaml
def test_empty_frontmatter()     # --- ---
def test_missing_required_fields() # No 'name' field
```

**3. Validation logic:**
```python
def test_missing_required_params()  # No max_count provided
def test_invalid_parameter_types()  # max_count="not_a_number"
def test_boundary_conditions()      # Exactly at limit
def test_resource_not_found()       # Referenced file missing
```

**4. Bundle operations:**
```python
def test_empty_bundle_files()    # bundle.files = []
def test_missing_file_path()     # rule.file_path is None
def test_all_bundles_none()      # all_bundles parameter = None
```

---

## How to Organize Tests

### File Naming Conventions

Follow Drift's pattern:
```
tests/
├── unit/
│   ├── test_<validator_name>_validator.py
│   └── test_<module>_<feature>.py
├── integration/
│   └── test_<workflow>_integration.py
└── conftest.py
```

**Examples:**
- `test_block_line_count_validator.py`
- `test_yaml_frontmatter_validator.py`
- `test_analyzer_multi_phase.py`

### Test Class Organization

See [Test Organization Patterns](resources/test-organization.md) for detailed class organization examples.

### Test Method Naming

Use descriptive names that explain the scenario:

```python
# Good names
def test_passes_when_block_under_max()
def test_fails_when_block_exceeds_max()
def test_handles_empty_code_block()
def test_handles_multiple_blocks_one_exceeds()

# Avoid vague names
def test_validator()        # What about it?
def test_case_1()           # What is case 1?
def test_edge()             # Which edge?
```

## Test Planning Checklist

When planning tests for a feature:

1. **Requirements Analysis**
   - [ ] Listed all requirements
   - [ ] Identified all behaviors
   - [ ] Mapped behaviors to test cases

2. **Edge Cases**
   - [ ] Tested boundary values
   - [ ] Tested empty/null cases
   - [ ] Tested error conditions
   - [ ] Used equivalence partitioning

3. **Coverage**
   - [ ] Achieves 90%+ line coverage
   - [ ] Tests all branches (if/else)
   - [ ] Tests error handling paths
   - [ ] Tests are meaningful, not just line hits

4. **Organization**
   - [ ] Tests organized by type (unit/integration/e2e)
   - [ ] Test files named consistently
   - [ ] Fixtures reused effectively
   - [ ] Test names are descriptive

5. **Balance**
   - [ ] Mostly unit tests (fast feedback)
   - [ ] Some integration tests (confidence)
   - [ ] Minimal e2e tests (coverage of critical paths)

## Resources

All test strategy resources are available in the [resources/](resources/) directory:

### 📖 [Test Identification Guide](resources/test-identification.md)
Step-by-step process for identifying what tests to write from requirements.

**Use when:** Planning tests for a new feature or analyzing what's missing.

### 📖 [Coverage Strategies](resources/coverage-strategies.md)
Techniques for achieving and maintaining 90%+ coverage meaningfully.

**Use when:** Coverage is below target or analyzing coverage reports.

### 📖 [Edge Case Techniques](resources/edge-case-techniques.md)
Detailed guide on equivalence partitioning, boundary analysis, and error guessing.

**Use when:** Identifying missing edge cases or reviewing test completeness.

### 📖 [Test Organization Patterns](resources/test-organization.md)
Patterns for organizing test files, classes, and fixtures.

**Use when:** Setting up tests for a new module or refactoring test structure.

### 📖 [Mocking Strategies](resources/mocking-strategies.md)
Patterns for mocking dependencies, external APIs, and file systems.

**Use when:** Testing code with external dependencies or complex interactions.
