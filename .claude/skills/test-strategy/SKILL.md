---
name: test-strategy
description: Expert in strategic pytest test planning for Drift's 90%+ coverage requirement, including coverage analysis with pytest-cov, edge case identification, and comprehensive test suite design. Use when determining what tests to write, analyzing coverage gaps, or planning test strategies.
skills:
  - testing
  - python-basics
---

# Test Strategy Skill

Expert in strategic test planning for comprehensive test coverage in the Drift project.

## Core Responsibilities

- Identify what tests need to be written from requirements
- Design comprehensive test coverage strategies
- Identify edge cases and boundary conditions
- Organize test suites for maintainability
- Guide test pyramid balance (unit vs integration vs e2e)
- Analyze coverage reports to find meaningful gaps

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

## 1. Identifying What Tests to Write

### From User Stories to Test Cases

**Process:**
1. **Extract Requirements** - What should the code do?
2. **Identify Behaviors** - What are all the possible behaviors?
3. **Map to Test Cases** - One test per behavior
4. **Prioritize by Risk** - Critical path first

**Example: Validator Implementation**

Given user story: "Create a validator that checks if code blocks exceed maximum line count"

**Requirements Analysis:**
- R1: Find code blocks in markdown files
- R2: Count lines in each code block
- R3: Compare against max_count parameter
- R4: Return None if under limit
- R5: Return failure if over limit
- R6: Handle files without code blocks

**Behavior Mapping:**
```python
# From R2, R3, R4, R5:
def test_passes_when_block_under_max()
def test_fails_when_block_exceeds_max()
def test_passes_when_block_equals_max()  # Boundary case!

# From R6:
def test_passes_when_no_code_blocks()

# Additional behaviors discovered:
def test_handles_empty_code_block()
def test_handles_multiple_code_blocks()
def test_counts_only_block_content_not_fence()
```

### Test Pyramid Guidance

**Drift's Test Pyramid:**
```
        /\        E2E (< 5%)
       /  \       - Full CLI workflows
      /____\      - Multi-validator scenarios
     /      \
    /  INTEG \    Integration (10-15%)
   /__________\   - Multi-phase analysis
  /            \  - Validator with DocumentBundle
 /     UNIT     \ Unit (80-90%)
/________________\ - Individual validators
                   - Utility functions
```

**When to write each type:**

**Unit Tests (80-90% of tests):**
- Individual validator logic
- Utility functions
- Model validation
- Parser functions
- Format functions

**Integration Tests (10-15% of tests):**
- Validator with DocumentBundle
- Analyzer with multiple phases
- Config loading with file system
- CLI with multiple validators

**E2E Tests (< 5% of tests):**
- Full `drift --no-llm` workflow
- Complete analysis pipeline
- Real configuration files

---

## 2. Getting Good Coverage

### Coverage ≠ Quality

**90% coverage means:**
✅ 90% of lines are executed during tests
❌ NOT that 90% of behaviors are tested

**Good Coverage Strategy:**

1. **Start with behaviors, not lines**
   - List all expected behaviors
   - Write tests for each behavior
   - Check coverage to find gaps

2. **Use coverage reports to identify gaps**
   ```bash
   pytest --cov=drift --cov-report=term-missing
   ```

   Look for:
   - Uncovered error handling paths
   - Untested branches (if/else)
   - Edge cases in conditionals

3. **Branch coverage over line coverage**
   ```bash
   pytest --cov-branch
   ```

   Ensures both paths of if/else are tested

### Coverage Analysis Workflow

**When coverage is below 90%:**

1. Run coverage with missing lines
2. Analyze uncovered lines (error handling? branch? edge case?)
3. Write meaningful tests for behaviors, not just line hits

**Example - Good vs Bad Coverage:**

```python
# BAD: Just hitting lines
def test_coverage_filler():
    validator.validate(rule, bundle)  # Just runs the code

# GOOD: Testing behavior
def test_fails_when_schema_validation_fails():
    # Specifically tests schema validation failure path
    invalid_rule = ValidationRule(...)
    result = validator.validate(invalid_rule, bundle)
    assert result is not None
    assert "schema validation failed" in result.observed_issue
```

### Coverage Patterns from Drift

**Pattern 1: Test all validator outcomes**
```python
def test_passes_when_valid()           # Happy path
def test_fails_when_invalid()          # Failure path
def test_handles_file_not_found()      # Error path
def test_handles_missing_params()      # Configuration error
```

**Pattern 2: Test exception paths**
```python
def test_missing_package(monkeypatch)  # ImportError
def test_file_read_error(monkeypatch)  # IOError
def test_invalid_yaml(tmp_path)        # YAMLError
```

---

## 3. Identifying Edge Cases

### Equivalence Partitioning

**Concept:** Divide input domain into classes that should behave similarly.

**Example: Line count validator**

Input: code block line count (integer)

**Partitions:**
1. Below minimum (if min specified): 0, min-1
2. Valid range: min, min+1, max-1, max
3. Above maximum: max+1, max+100

**Test strategy:** Test one value from each partition + boundaries

```python
# Partition 1: No code blocks
def test_passes_when_no_code_blocks():
    # content with no code blocks

# Partition 2: Valid range
def test_passes_when_in_valid_range():
    # code block with 50 lines (middle of range)

# Partition 3: Above max (if max=100)
def test_fails_when_above_maximum():
    # code block with 150 lines
```

### Boundary Value Analysis

**Critical insight:** Bugs cluster at boundaries!

**For any constraint, test:**
1. Just below boundary
2. At boundary
3. Just above boundary

**Example from BlockLineCountValidator:**

If max_count = 100:
```python
def test_passes_with_99_lines()   # Just below
def test_passes_with_100_lines()  # At boundary
def test_fails_with_101_lines()   # Just above
```

**Common boundaries in Drift:**
- Empty collections: [], "", {}, None
- Zero values: 0, 0.0
- File boundaries: empty file, no code blocks
- String boundaries: "", "a", very long string

### Type-Specific Edge Cases

**Strings:**
```python
# Empty, whitespace, special chars, very long
"", "   ", "\n\t", "!" * 10000
```

**Lists/Arrays:**
```python
# Empty, single item, many items
[], [item], [i1, i2, ...]
```

**Files:**
```python
# Non-existent, empty, unreadable, malformed
Path("missing.txt"), empty_file, invalid_markdown
```

**Numbers:**
```python
# Zero, negative, boundary, overflow
0, -1, MAX_COUNT, MAX_COUNT + 1
```

### Error Guessing Technique

**Based on Drift patterns, common edge cases:**

1. **File operations:**
   - File doesn't exist
   - File is empty
   - File is unreadable (permissions)
   - File is malformed

2. **YAML/JSON parsing:**
   - Unclosed frontmatter
   - Invalid YAML syntax
   - Empty frontmatter
   - Missing required fields

3. **Validation logic:**
   - Missing required parameters
   - Invalid parameter types
   - Boundary conditions
   - Resource not found

4. **Bundle operations:**
   - Empty bundle.files
   - Missing file_path in rule
   - all_bundles is None

---

## 4. Test Organization

### File Naming Conventions

**Drift's pattern:**
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

**Drift's pattern:**
```python
class Test<ComponentName>:
    """Tests for <ComponentName>."""

    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return ComponentValidator()

    @pytest.fixture
    def bundle(self, tmp_path):
        """Create test bundle."""
        return DocumentBundle(...)

    # Happy path tests
    def test_passes_when_valid(self, validator, bundle):
        ...

    # Failure tests
    def test_fails_when_invalid(self, validator, bundle):
        ...

    # Edge case tests
    def test_handles_empty_file(self, validator, bundle):
        ...
```

### Test Method Naming

**Convention:** `test_<component>_<behavior>_<condition>`

**Good names:**
```python
def test_validator_passes_when_within_limit()
def test_parser_raises_error_on_invalid_json()
def test_analyzer_skips_disabled_rules()
```

**Bad names:**
```python
def test_validator()              # Too vague
def test_case_1()                 # No context
def test_this_should_work()       # Unclear
```

### Fixture Management

**Fixture hierarchy in Drift:**

```python
# conftest.py - Shared across all tests
@pytest.fixture
def temp_dir():
    """Temporary directory for all tests."""

# test_file.py - Test-specific fixtures
class TestValidator:
    @pytest.fixture
    def validator(self):
        """Validator instance for this test class."""

    @pytest.fixture
    def bundle(self, tmp_path):
        """Test bundle with specific setup."""
```

**Fixture composition:**
```python
# Build complex fixtures from simple ones
@pytest.fixture
def sample_drift_config(
    sample_provider_config,
    sample_model_config,
    sample_learning_type
):
    """Compose complex config from simpler fixtures."""
    return DriftConfig(
        providers={"bedrock": sample_provider_config},
        models={"haiku": sample_model_config},
        ...
    )
```

---

## 5. Mocking Strategies

### When to Mock

**Mock when:**
- Testing code that depends on external services (APIs, databases)
- Testing code with non-deterministic behavior (time, random)
- Testing code with slow operations (file I/O, network calls)
- Isolating the unit under test from its dependencies

**Don't mock when:**
- Testing simple pure functions
- Testing internal implementation details
- Over-isolating leads to meaningless tests
- The real dependency is fast and reliable

### Choosing Your Tool

**pytest monkeypatch:**
- Simple attribute/function replacements
- Environment variables
- Dictionary/object modifications
- Built-in, no extra dependencies

**unittest.mock / pytest-mock:**
- Complex mocking with call tracking
- Need to verify how mocks are called
- Decorator-based patching
- More advanced features (return_value, side_effect)

### Mock Verification

Always verify mocks are called correctly:
- `assert_called_once()`
- `assert_called_with(args)`
- `mock.call_count`
- `mock.call_args_list`

**Example from Drift:**

```python
from unittest.mock import Mock, patch

@patch("drift.providers.anthropic.Anthropic", autospec=True)
def test_token_counting(mock_anthropic):
    """Test with autospec for type safety."""
    # Configure mock
    mock_client = Mock()
    mock_client.count_tokens.return_value = 500
    mock_anthropic.return_value = mock_client

    # Test
    result = count_tokens("test content")

    # Verify
    assert result == 500
    mock_client.count_tokens.assert_called_once_with("test content")
```

**Common anti-patterns to avoid:**
- Over-mocking (too many mocks = brittle tests)
- Not using `autospec=True` (allows invalid method signatures)
- Mocking implementation instead of interface
- Mocks falling out of sync with reality

---

## Test Strategy Workflow

### Planning Tests for New Feature

1. **Understand the requirement**
   - Read user story/issue
   - Identify acceptance criteria
   - List expected behaviors

2. **Identify test types needed**
   - Primarily unit tests?
   - Need integration tests?
   - Any e2e scenarios?

3. **List all behaviors to test**
   - Happy path
   - Failure cases
   - Edge cases
   - Error conditions

4. **Design test structure**
   - Test class name
   - Fixture requirements
   - Test method names

5. **Implement tests**
   - Use testing skill for pytest details
   - Follow Drift patterns from similar tests

### Analyzing Coverage Gaps

1. **Run coverage report:**
   ```bash
   pytest --cov=drift --cov-report=term-missing --cov-branch
   ```

2. **For each uncovered line, ask:**
   - What behavior triggers this line?
   - Is it an edge case I missed?
   - Is it error handling?
   - Is it defensive code that's OK to skip?

3. **Write targeted tests:**
   - One test per uncovered behavior
   - Focus on meaningful coverage, not just lines

4. **Verify coverage improvement:**
   ```bash
   pytest --cov=drift --cov-report=term
   ```

---

## Resources

### 📖 [Test Identification Guide](resources/test-identification.md)
Step-by-step process for identifying what tests to write from requirements, user stories, and code changes.

**Use when:** Planning tests for a new feature or analyzing existing code for missing tests.

### 📖 [Coverage Strategies](resources/coverage-strategies.md)
Techniques for achieving meaningful 90%+ coverage beyond just hitting lines, including branch coverage and gap analysis.

**Use when:** Coverage is below target or you want to improve test quality.

### 📖 [Edge Case Techniques](resources/edge-case-techniques.md)
Comprehensive guide to equivalence partitioning, boundary value analysis, and error guessing with Drift-specific examples.

**Use when:** Identifying what edge cases to test or reviewing test completeness.

### 📖 [Test Organization Patterns](resources/test-organization.md)
Drift's patterns for organizing tests, naming conventions, fixture management, and test data strategies.

**Use when:** Setting up tests for a new module or refactoring test structure.

### 📖 [Mocking Strategies](resources/mocking-strategies.md)
Comprehensive guide to mocking in Python/pytest, including when to mock, monkeypatch vs unittest.mock, common anti-patterns, and Drift-specific patterns.

**Use when:** Deciding whether to mock, choosing mocking tools, or implementing mocks for external dependencies.
