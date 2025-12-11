---
name: definition-of-done
description: Expert in validating work meets all requirements, acceptance criteria, testing, and quality standards. Use when verifying task completion before creating a PR or reviewing pull requests against requirements.
---

# Definition of Done Skill

Learn how to validate that work meets all requirements and quality standards before creating PRs.

## When to Use This Skill

- Before creating a pull request
- Validating work against issue requirements
- Reviewing PRs against acceptance criteria
- Ensuring work is complete and ready for review
- Creating requirement traceability documentation

## How to Validate Work is Complete

### Overview of Validation Process

Complete validation includes:
1. **Requirements Traceability** - Map acceptance criteria to implementation
2. **Quality Checks** - Run linters and verify standards
3. **Testing Verification** - Check coverage and test quality
4. **Documentation Review** - Ensure docs are complete
5. **Functional Testing** - Manually verify it works
6. **Git Hygiene** - Check commits and branch status

## How to Create Requirement Traceability

### Step 1: Review Issue Acceptance Criteria

From the issue, list all acceptance criteria:

**Example issue #42:**
```markdown
## Acceptance Criteria
- [ ] CLI accepts multiple --drift-type arguments
- [ ] Each drift type runs in separate LLM call
- [ ] Results combined in single output
- [ ] Tests cover multi-type analysis
- [ ] Documentation updated with examples
```

### Step 2: Map Each Criterion to Implementation

For each acceptance criterion, identify:
- Where it's implemented (file and lines)
- Which tests cover it
- Any related documentation updates

**Traceability mapping:**
```markdown
## Requirement Traceability - Issue #42

### AC1: CLI accepts multiple --drift-type arguments
**Status:** ✅ Complete
- **Implementation:** `src/drift/cli.py:45-52`
- **Code:**
  ```python
  @click.option('--drift-type', multiple=True)
  def analyze(drift_type):
      types = drift_type or config.get('drift_types')
  ```
- **Tests:** `tests/unit/test_cli.py::test_multiple_drift_types`
- **Verification:** Tested with `drift --drift-type incomplete --drift-type spec`

### AC2: Each drift type runs in separate LLM call
**Status:** ✅ Complete
- **Implementation:** `src/drift/detector.py:120-145`
- **Code:** MultiPassAnalyzer class, analyze_multi() method
- **Tests:** `tests/integration/test_multi_pass.py::test_separate_llm_calls`
- **Verification:** Mocked LLM calls show one call per type

### AC3: Results combined in single output
**Status:** ✅ Complete
- **Implementation:** `src/drift/formatter.py:67-82`
- **Code:** CombinedResultFormatter.format() method
- **Tests:** `tests/unit/test_formatter.py::test_combined_output`
- **Verification:** Output shows all types in single JSON/text output

### AC4: Tests cover multi-type analysis
**Status:** ✅ Complete
- **Unit tests:** 8 tests in test_multi_pass.py
- **Integration tests:** 3 tests in test_integration_multi.py
- **Coverage:** 94% for new code
- **Edge cases:** empty types, single type, three types

### AC5: Documentation updated with examples
**Status:** ✅ Complete
- **README:** Section "Multi-Type Analysis" added
- **CLI help:** --drift-type option documented
- **Examples:** Three usage examples provided
```

### Step 3: Verify All Criteria Met

Check each criterion:
- [ ] Implementation exists and works
- [ ] Tests cover the functionality
- [ ] Documentation is updated
- [ ] Manual verification passed

## How to Run Quality Checks

### Step 1: Run Linters

```bash
# Run all linters
./lint.sh
```

Check output:
- ✅ All linters pass: Ready to proceed
- ❌ Linting errors: Fix before continuing

**Common linting issues:**
- Line too long (> 100 chars)
- Import order incorrect
- Missing type hints
- Trailing whitespace

### Step 2: Run Tests with Coverage

```bash
# Run tests with coverage report
./test.sh --coverage
```

Check output:
- Coverage percentage
- Which files are below threshold
- Which lines aren't covered

**Coverage checklist:**
- [ ] Overall coverage ≥ 90%
- [ ] New code coverage ≥ 90%
- [ ] Critical paths covered
- [ ] Edge cases tested

### Step 3: Review Test Quality

Not just coverage percentage, but quality:

**Check for:**
- Tests have clear names
- Tests are independent
- Edge cases covered
- Error scenarios tested
- Mocks used appropriately

**Example quality check:**
```python
# Review test file
# tests/unit/test_multi_pass.py

# Good test indicators:
✅ def test_analyze_empty_drift_types():  # Clear name
✅ def test_analyze_with_api_error():     # Error case
✅ def test_analyze_three_types():        # Edge case

# Issues to fix:
❌ def test_case_1():                     # Vague name
❌ Only happy path tested                 # Missing edge cases
```

## How to Verify Documentation

### Step 1: Check Docstrings

For each new/modified public function:

```python
# Verify docstring exists and is complete
def analyze_multi_pass(drift_types: List[str]) -> List[DriftResult]:
    """Analyze conversation for multiple drift types.

    Runs separate LLM analysis for each drift type and combines
    results. Each type is analyzed independently to avoid
    cross-contamination.

    -- drift_types: List of drift types to analyze
        Valid values: incomplete_work, spec_adherence, context_loss

    Returns:
        List of DriftResult objects, one per detected issue

    Raises:
        ValueError: If drift_types is empty or contains invalid types
        APIError: If LLM API calls fail
    """
```

**Checklist:**
- [ ] Purpose explained
- [ ] Parameters documented
- [ ] Return value described
- [ ] Exceptions listed
- [ ] Examples provided (if complex)

### Step 2: Check User-Facing Documentation

**README updates:**
- [ ] New features documented
- [ ] Usage examples added
- [ ] Configuration options explained
- [ ] Installation instructions current

**Example README section:**
```markdown
## Multi-Type Analysis

Analyze for multiple drift types in one run:

```bash
drift --drift-type incomplete_work --drift-type spec_adherence
```

Results show all detected issues organized by type.
```

**CLI help text:**
```bash
# Verify help text updated
drift --help

# Should show:
--drift-type TEXT  Drift type to analyze (can be specified multiple times)
```

## How to Test Functionality Manually

### Step 1: Test Happy Path

Run the feature with expected inputs:

```bash
# Example for multi-type feature
drift --drift-type incomplete_work --drift-type spec_adherence log.json

# Verify:
✅ Command executes without errors
✅ Output shows both drift types
✅ Results are formatted correctly
✅ Exit code is appropriate
```

### Step 2: Test Edge Cases

Try unusual but valid inputs:

```bash
# Single type (should still work)
drift --drift-type incomplete_work log.json

# No types specified (should use defaults)
drift log.json

# Empty conversation log
drift --drift-type incomplete_work empty.json
```

### Step 3: Test Error Scenarios

Verify error handling:

```bash
# Invalid drift type
drift --drift-type invalid_type log.json
# Expect: Clear error message explaining valid types

# Missing log file
drift --drift-type incomplete_work missing.json
# Expect: FileNotFoundError with helpful message

# Malformed JSON
drift --drift-type incomplete_work bad.json
# Expect: JSONDecodeError with clear explanation
```

## How to Check Git Hygiene

### Review Commits

```bash
# List commits on branch
git log main..HEAD --oneline
```

**Check for:**
- [ ] Commits are logical and atomic
- [ ] Each commit message is descriptive
- [ ] No "WIP" or "fix" commits (squash if present)
- [ ] Commit messages follow project format

**Good commit history:**
```
abc1234 Add MultiPassAnalyzer for multi-type analysis
def5678 Add CLI support for multiple --drift-type flags
ghi9012 Update documentation with multi-type examples
```

**Bad commit history (needs cleanup):**
```
abc1234 WIP
def5678 fix bug
ghi9012 more fixes
jkl3456 actually works now
```

### Check Branch Status

```bash
# Check for merge conflicts and remote status
git status
```

**Verify:**
- [ ] No merge conflicts
- [ ] Branch is up to date with main
- [ ] No untracked files that should be committed
- [ ] No unintended files committed (.DS_Store, __pycache__, etc.)

**Update branch if needed:**
```bash
git fetch origin
git rebase origin/main

# Or merge if preferred
git merge origin/main
```

## Pre-PR Validation Checklist

See [Validation Guide](resources/validation-guide.md) for complete checklist workflow.

## How to Generate Validation Report

See [Report Template](resources/report-template.md) for a complete validation report template covering:
- Requirements traceability
- Code quality verification
- Testing summary
- Documentation checklist
- Functionality validation
- Git hygiene check
- Summary and next steps

## Common Gaps and How to Fix Them

### Gap: Incomplete Implementation

**Symptom:**
- Feature partially works
- Edge cases not handled
- Only happy path implemented

**Example:**
```python
# Current (incomplete):
def analyze_multi(drift_types):
    return [analyze(t) for t in drift_types]
    # Missing: empty list check, invalid type validation
```

**How to fix:**
```python
def analyze_multi(drift_types):
    if not drift_types:
        raise ValueError("drift_types cannot be empty")

    for dtype in drift_types:
        if dtype not in VALID_TYPES:
            raise ValueError(f"Invalid drift type: {dtype}")

    return [analyze(t) for t in drift_types]
```

### Gap: Testing Gaps

**Symptom:**
- Coverage below 90%
- Only happy path tested
- Edge cases missing
- No error scenario tests

**How to identify:**
```bash
# Run coverage with missing lines
pytest --cov=src/drift --cov-report=term-missing

# Output shows uncovered lines:
# src/drift/detector.py:78-82  (error handling not tested)
```

**How to fix:**
Add tests for uncovered code:
```python
def test_analyze_multi_empty_types():
    """Test error when drift_types is empty."""
    with pytest.raises(ValueError, match="cannot be empty"):
        analyze_multi([])

def test_analyze_multi_invalid_type():
    """Test error with invalid drift type."""
    with pytest.raises(ValueError, match="Invalid drift type"):
        analyze_multi(["invalid_type"])
```

### Gap: Documentation Missing

**Symptom:**
- Missing docstrings on new functions
- README not updated for new features
- CLI help text not updated
- No usage examples

**How to identify:**
```python
# Check for missing docstrings
grep -r "^def " src/drift/new_module.py | while read line; do
    # Check if function has docstring
done
```

**How to fix:**
Add complete docstrings:
```python
def analyze_multi(drift_types: List[str]) -> List[DriftResult]:
    """Analyze conversation for multiple drift types.

    -- drift_types: List of drift types to analyze

    Returns:
        List of DriftResult objects

    Raises:
        ValueError: If drift_types is empty or invalid
    """
```

Update README:
```markdown
## New Feature: Multi-Type Analysis

```bash
drift --drift-type incomplete_work --drift-type spec_adherence
```
```

## Resources

### 📖 [Validation Guide](resources/validation-guide.md)
Step-by-step validation process and quality checks.

**Use when:** Starting a validation workflow before creating a PR.

### 📖 [Common Gaps](resources/common-gaps.md)
Common implementation, testing, and documentation gaps with fixes.

**Use when:** Identifying why validation is failing or improving code quality.

### 📖 [Report Template](resources/report-template.md)
Complete validation report template with all sections.

**Use when:** Generating a validation report before creating a PR.

