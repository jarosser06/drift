# Coverage Strategies

Techniques for achieving meaningful 90%+ coverage beyond just hitting lines.

## Understanding Coverage Metrics

### Line Coverage

**What it measures:**
- Percentage of code lines executed during tests
- Default metric reported by coverage.py

**What it tells you:**
```python
def validate(value):
    if value > 100:      # Line executed
        return False     # Line executed
    return True          # Line executed
```

Line coverage = 100% if test calls `validate(50)`
But we haven't tested the `if value > 100` branch!

**Limitations:**
- Doesn't ensure all branches tested
- Doesn't ensure all conditions tested
- Can miss edge cases
- Can be gamed with superficial tests

### Branch Coverage

**What it measures:**
- Percentage of code branches executed
- Tests both True and False paths of conditionals

**Example:**
```python
def validate(value):
    if value > 100:      # Branch point
        return False     # Branch 1
    return True          # Branch 2
```

**Branch coverage requires:**
- Test with `value > 100` (Branch 1)
- Test with `value <= 100` (Branch 2)

**How to use:**
```bash
pytest --cov=drift --cov-branch --cov-report=term-missing
```

**Why it's better:**
- Ensures all decision paths tested
- Catches untested conditions
- More meaningful than line coverage

### Path Coverage

**What it measures:**
- All possible execution paths through code
- Most comprehensive but often impractical

**Example:**
```python
def complex_logic(a, b):
    if a > 0:           # Branch 1
        if b > 0:       # Branch 2
            return "both positive"
        return "a positive"
    if b > 0:           # Branch 3
        return "b positive"
    return "both non-positive"
```

**Paths:**
1. a>0, b>0 → "both positive"
2. a>0, b<=0 → "a positive"
3. a<=0, b>0 → "b positive"
4. a<=0, b<=0 → "both non-positive"

Path coverage requires testing all 4 paths.

**When to use:**
- Critical algorithms
- Complex business logic
- Security-sensitive code

---

## Coverage Analysis Workflow

### Step 1: Run Coverage Report

```bash
# Basic coverage
pytest --cov=drift --cov-report=term-missing

# With branch coverage
pytest --cov=drift --cov-branch --cov-report=term-missing

# With HTML report for detailed analysis
pytest --cov=drift --cov-branch --cov-report=html
```

### Step 2: Interpret Results

**Terminal output:**
```
Name                               Stmts   Miss Branch BrPart  Cover
--------------------------------------------------------------------
src/drift/validation/validators/
  core/file_validators.py            156     12     42      8    89%
```

**What this means:**
- 156 total statements
- 12 statements not executed (shown with line numbers)
- 42 branch points
- 8 branches partially covered (one path tested, other not)
- 89% overall coverage

**Missing lines shown:**
```
src/drift/validation/validators/core/file_validators.py
  150-155, 200-202, 220
```

### Step 3: Analyze Uncovered Lines

For each uncovered line, ask:

**Question 1: What behavior triggers this line?**
```python
# Line 150-155 uncovered
except ImportError:
    raise RuntimeError("tiktoken package required")
```
→ Behavior: Handle missing tiktoken package
→ Test needed: Mock missing import

**Question 2: Is this an edge case I missed?**
```python
# Line 200 uncovered
if min_count and count < min_count:
    return create_failure("too few")
```
→ Edge case: min_count validation
→ Test needed: Test with min_count parameter

**Question 3: Is this error handling?**
```python
# Line 220 uncovered
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```
→ Error handling: Generic exception catch
→ Test needed: Simulate unexpected error

**Question 4: Is this defensive code?**
```python
# Line 250 uncovered
assert isinstance(value, int), "value must be int"
```
→ Defensive assertion
→ Consider: Is this worth testing or can skip?

### Step 4: Write Targeted Tests

For each identified gap, write a specific test:

```python
# For line 150-155 (missing tiktoken)
def test_raises_error_when_tiktoken_missing(monkeypatch):
    """Test that missing tiktoken raises clear error."""
    # Remove tiktoken from sys.modules
    monkeypatch.setitem(sys.modules, "tiktoken", None)

    with pytest.raises(RuntimeError, match="tiktoken package required"):
        validator.count_tokens("test content")

# For line 200 (min_count)
def test_fails_when_below_min_count():
    """Test validation fails when count below minimum."""
    rule = ValidationRule(min_count=10, max_count=100)
    bundle = create_bundle_with_lines(5)  # 5 < min

    result = validator.validate(rule, bundle)

    assert result is not None
    assert "too few" in result.observed_issue
```

---

## Common Coverage Gaps

### Gap 1: Error Handling Paths

**Pattern:**
```python
try:
    result = risky_operation()
except SpecificError:
    # This line uncovered!
    handle_error()
```

**How to test:**
```python
def test_handles_specific_error(monkeypatch):
    """Test error handling for SpecificError."""
    def mock_risky():
        raise SpecificError("test error")

    monkeypatch.setattr(module, "risky_operation", mock_risky)

    # Now error handling path will be executed
    validator.process()
```

**Drift examples:**
```python
def test_handles_missing_anthropic_package(monkeypatch)
def test_handles_file_read_error(monkeypatch)
def test_handles_yaml_parse_error(tmp_path)
```

### Gap 2: Branch Conditions

**Pattern:**
```python
if condition_a and condition_b:
    # Path 1
else:
    # Path 2 - only this tested!
```

**Missing tests:**
- condition_a=True, condition_b=True (Path 1)
- condition_a=True, condition_b=False (Path 2)
- condition_a=False, condition_b=True (Path 2)
- condition_a=False, condition_b=False (Path 2)

**How to test:**
```python
def test_both_conditions_true()   # Path 1
def test_first_false()             # Path 2
def test_second_false()            # Path 2
def test_both_false()              # Path 2
```

### Gap 3: Edge Case Logic

**Pattern:**
```python
if value <= 0:
    return "invalid"
elif value < 100:
    return "low"
elif value < 1000:
    return "medium"
else:
    return "high"
```

**Missing tests often:**
- Boundary values: 0, 1, 99, 100, 999, 1000
- Negative values: -1, -100

**How to test:**
```python
@pytest.mark.parametrize("value,expected", [
    (-1, "invalid"),      # Negative
    (0, "invalid"),       # Boundary
    (1, "low"),           # Boundary
    (99, "low"),          # Boundary
    (100, "medium"),      # Boundary
    (999, "medium"),      # Boundary
    (1000, "high"),       # Boundary
])
def test_categorization(value, expected):
    assert categorize(value) == expected
```

### Gap 4: Configuration Variations

**Pattern:**
```python
def process(config):
    if config.get("optional_feature"):
        # Feature enabled path - uncovered!
        use_feature()

    # Normal processing
    ...
```

**Missing tests:**
- With optional_feature=True
- With optional_feature=False
- With optional_feature missing

**How to test:**
```python
def test_with_optional_feature_enabled():
    config = {"optional_feature": True}
    result = process(config)
    # Assert feature was used

def test_with_optional_feature_disabled():
    config = {"optional_feature": False}
    result = process(config)
    # Assert feature not used

def test_with_optional_feature_missing():
    config = {}  # No optional_feature key
    result = process(config)
    # Assert feature not used
```

---

## Meaningful vs Superficial Coverage

### Bad Coverage (Line Chasing)

**Anti-pattern: Just runs code**
```python
def test_validator():
    """Test validator."""
    validator = MyValidator()
    result = validator.validate(rule, bundle)
    # No assertions!
```

**Problems:**
- Doesn't verify behavior
- Would pass even if validator is broken
- Just hits lines, doesn't test correctness

### Good Coverage (Behavior Testing)

**Pattern: Tests specific behavior**
```python
def test_fails_when_block_exceeds_max_lines():
    """Test that validation fails when code block exceeds max_count."""
    validator = BlockLineCountValidator()

    # Create bundle with block exceeding limit
    content = "```python\n" + "\n".join(["line"] * 150) + "\n```"
    bundle = create_bundle(content)

    # Rule with max_count = 100
    rule = ValidationRule(max_count=100)

    # Execute
    result = validator.validate(rule, bundle)

    # Verify specific behavior
    assert result is not None, "Should fail when block exceeds limit"
    assert result.rule_id == "block_line_count"
    assert "exceeds maximum" in result.observed_issue.lower()
    assert "150" in result.observed_issue  # Reports actual count
    assert "100" in result.observed_issue  # Reports limit
```

**Why it's good:**
- Tests specific requirement
- Verifies correct failure
- Checks error message quality
- Would fail if behavior breaks

### Coverage Quality Checklist

For each test, verify:
- [ ] Tests one specific behavior
- [ ] Has clear, descriptive name
- [ ] Includes meaningful assertions
- [ ] Would fail if behavior breaks
- [ ] Checks both success and failure paths
- [ ] Verifies error messages are helpful

---

## Coverage Improvement Techniques

### Technique 1: Parametrize for Variations

**Instead of:**
```python
def test_with_provider_anthropic():
    result = select_tokenizer("anthropic")
    assert result == "anthropic_tokenizer"

def test_with_provider_openai():
    result = select_tokenizer("openai")
    assert result == "openai_tokenizer"

def test_with_provider_llama():
    result = select_tokenizer("llama")
    assert result == "llama_tokenizer"
```

**Use parametrize:**
```python
@pytest.mark.parametrize("provider,expected", [
    ("anthropic", "anthropic_tokenizer"),
    ("openai", "openai_tokenizer"),
    ("llama", "llama_tokenizer"),
    ("unknown", "default_tokenizer"),  # Edge case added easily
])
def test_tokenizer_selection(provider, expected):
    result = select_tokenizer(provider)
    assert result == expected
```

**Benefits:**
- Less code duplication
- Easier to add edge cases
- Better coverage with less effort

### Technique 2: Fixture Composition

**Instead of:**
```python
def test_validator_with_complex_setup():
    # 20 lines of setup
    config = {...}
    provider = Provider(config)
    model = Model(config)
    validator = Validator(provider, model)
    bundle = DocumentBundle(...)
    # ... test
```

**Use fixtures:**
```python
@pytest.fixture
def validator(sample_provider, sample_model):
    return Validator(sample_provider, sample_model)

@pytest.fixture
def bundle(tmp_path):
    return create_test_bundle(tmp_path)

def test_validator(validator, bundle):
    # Clean, focused test
    result = validator.validate(rule, bundle)
    assert result is None
```

### Technique 3: Monkeypatch for Errors

**Simulate errors without complex mocking:**
```python
def test_handles_import_error(monkeypatch):
    """Test handling of missing optional dependency."""
    # Make import fail
    monkeypatch.setitem(sys.modules, "optional_package", None)

    # Now this path will be covered
    with pytest.raises(RuntimeError, match="optional_package required"):
        validator.initialize()

def test_handles_file_read_error(monkeypatch):
    """Test handling of file read errors."""
    def mock_read_text():
        raise IOError("Permission denied")

    monkeypatch.setattr(Path, "read_text", mock_read_text)

    result = validator.validate(rule, bundle)
    assert result is not None
    assert "permission denied" in result.observed_issue.lower()
```

### Technique 4: tmp_path for Files

**Test file operations cleanly:**
```python
def test_validates_multiple_files(tmp_path):
    """Test validation across multiple files."""
    # Create test files
    file1 = tmp_path / "file1.md"
    file1.write_text("```python\nshort\n```")

    file2 = tmp_path / "file2.md"
    file2.write_text("```python\n" + "\n".join(["line"] * 150) + "\n```")

    # Create bundle
    bundle = create_bundle_from_dir(tmp_path)

    # Validate
    result = validator.validate(rule, bundle)

    # Should fail because file2 exceeds limit
    assert result is not None
    assert "file2.md" in result.file_path
```

---

## Case Study: 90% → 95% Coverage

### Initial State (90% coverage)

**Missing coverage:**
```
src/drift/validation/validators/core/block_validators.py
  45-48, 67, 89-92, 110
```

### Analysis

**Lines 45-48:** ImportError handling for optional package
```python
try:
    from markdown_parser import extract_blocks
except ImportError:
    # Lines 45-48 uncovered
    raise RuntimeError("markdown_parser required")
```

**Line 67:** min_count parameter handling
```python
if min_count and count < min_count:  # min_count path uncovered
    return create_failure("too few lines")
```

**Lines 89-92:** Generic exception handling
```python
except Exception as e:
    # Lines 89-92 uncovered
    logger.error(f"Unexpected: {e}")
    raise
```

**Line 110:** Empty code block edge case
```python
if len(block.lines) == 0:  # Uncovered
    continue  # Skip empty blocks
```

### Tests Added

```python
def test_raises_error_when_parser_missing(monkeypatch):
    """Test handling of missing markdown_parser package."""
    monkeypatch.setitem(sys.modules, "markdown_parser", None)
    with pytest.raises(RuntimeError, match="markdown_parser required"):
        BlockLineCountValidator()

def test_fails_when_below_min_count():
    """Test validation fails when below minimum."""
    rule = ValidationRule(min_count=10, max_count=100)
    bundle = create_bundle_with_lines(5)
    result = validator.validate(rule, bundle)
    assert result is not None
    assert "too few" in result.observed_issue

def test_handles_unexpected_error(monkeypatch):
    """Test handling of unexpected errors."""
    def mock_extract():
        raise RuntimeError("Unexpected!")
    monkeypatch.setattr(validator, "_extract_blocks", mock_extract)
    with pytest.raises(RuntimeError, match="Unexpected"):
        validator.validate(rule, bundle)

def test_skips_empty_code_blocks():
    """Test that empty code blocks are skipped."""
    content = "```python\n```\n```python\ncode\n```"
    bundle = create_bundle(content)
    result = validator.validate(rule, bundle)
    # Should only count the non-empty block
```

### Result

Coverage: 90% → 95% ✅

All meaningful paths now tested.

---

## When to Skip Coverage

### Acceptable Gaps

**1. Main block:**
```python
if __name__ == "__main__":
    main()
```
→ Skip: Entry points tested via CLI tests

**2. Defensive assertions:**
```python
assert isinstance(value, int), "Developer error"
```
→ Skip: Type hints + validation prevent this

**3. Logger configuration:**
```python
logging.basicConfig(
    format="%(message)s",
    level=logging.INFO
)
```
→ Skip: Infrastructure, not business logic

**4. Development-only code:**
```python
if DEBUG:
    print(f"Debug: {state}")
```
→ Skip: Not production code

**5. Abstract methods:**
```python
def validate(self):
    raise NotImplementedError
```
→ Skip: Tested via implementations

### How to Skip

**Add pragma comment:**
```python
if __name__ == "__main__":  # pragma: no cover
    main()
```

**Configure in pyproject.toml:**
```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]
```

---

## Coverage Best Practices

### Do:
- Start with behaviors, not lines
- Use branch coverage
- Test error paths
- Parametrize for variations
- Use fixtures for reusable setup
- Focus on meaningful coverage

### Don't:
- Chase 100% coverage
- Write tests just to hit lines
- Skip error handling tests
- Ignore branch coverage
- Test implementation details
- Skip boundary conditions

### Remember:

**Coverage is a tool, not a goal.**

The goal is comprehensive, maintainable tests that give confidence in the code. Coverage helps find gaps, but 95% meaningful coverage is better than 100% superficial coverage.
