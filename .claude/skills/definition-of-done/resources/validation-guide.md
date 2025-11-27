# Validation Guide

Step-by-step guide for validating work meets all requirements and quality standards.

## Overview

Definition of Done validation ensures that:
1. All acceptance criteria are met
2. Code quality standards are satisfied
3. Testing is comprehensive
4. Documentation is complete
5. No regressions introduced

## Step-by-Step Validation Process

### Step 1: Review Original Issue

**Action:** Re-read the linked issue completely

**Checklist:**
- [ ] Understand the problem statement
- [ ] Review all acceptance criteria
- [ ] Note any technical constraints
- [ ] Check for related issues

**Output:** List of all acceptance criteria to verify

---

### Step 2: Create Requirement Traceability Matrix

**Action:** Map each acceptance criterion to implementation

**Format:**
```markdown
## Requirement Traceability

- [x] **AC1:** [Description of criterion]
  - Implementation: [file:line]
  - Tests: [test file:test name]
  - Verified: [how you verified it works]

- [x] **AC2:** [Description of criterion]
  - Implementation: [file:line]
  - Tests: [test file:test name]
  - Verified: [how you verified it works]
```

**Example:**
```markdown
## Requirement Traceability

- [x] **AC1:** CLI accepts multiple --drift-type arguments
  - Implementation: drift/cli.py:45-52
  - Tests: tests/unit/test_cli.py::test_multiple_drift_types
  - Verified: Manually tested with 2, 3, and 5 types

- [x] **AC2:** Each drift type runs in separate LLM call
  - Implementation: drift/core/multi_analyzer.py:34-67
  - Tests: tests/integration/test_multi_pass.py::test_sequential_calls
  - Verified: Logged LLM calls, confirmed sequential execution
```

---

### Step 3: Run Full Quality Check

**Action:** Execute all linters and tests

```bash
# Run linting
./lint.sh

# Run tests with coverage
./test.sh --coverage
```

**Checklist:**
- [ ] flake8 passes (no warnings)
- [ ] black formatting passes
- [ ] isort import sorting passes
- [ ] mypy type checking passes
- [ ] All tests pass (100% pass rate)
- [ ] Coverage ≥ 90%

**If any fail:** Fix before proceeding

---

### Step 4: Verify Code Quality

**Action:** Review code changes for quality standards

**Checklist:**

**Structure:**
- [ ] No code duplication
- [ ] Functions have single responsibility
- [ ] Appropriate abstraction levels
- [ ] Clear module boundaries

**Naming:**
- [ ] Names are descriptive
- [ ] Consistent with codebase conventions
- [ ] No misleading names

**Imports:**
- [ ] **CRITICAL:** All imports at top of file
- [ ] No inline imports (except TYPE_CHECKING)
- [ ] Organized: stdlib → third-party → local
- [ ] No unused imports

**Documentation:**
- [ ] Docstrings on all public functions
- [ ] Parameters documented with `-- param:`
- [ ] Return values documented
- [ ] Exceptions documented

**Error Handling:**
- [ ] Specific exception catching (not broad `except Exception`)
- [ ] Clear error messages for users
- [ ] Proper cleanup in error paths

---

### Step 5: Validate Testing

**Action:** Review test coverage and quality

**Coverage Check:**
```bash
# View coverage report
./test.sh --coverage

# Check for untested code
# Look at "Missing" column in coverage output
```

**Test Quality Checklist:**
- [ ] Tests verify behavior, not implementation
- [ ] Edge cases covered:
  - [ ] Empty/null inputs
  - [ ] Invalid inputs
  - [ ] Boundary conditions
  - [ ] Error scenarios
- [ ] Tests are clear and maintainable
- [ ] Proper use of fixtures and mocks
- [ ] No flaky tests

**Example Edge Cases to Check:**
```python
# For conversation parser:
- Empty conversation (no messages)
- Single message
- 1000+ messages (performance)
- Malformed JSON
- Missing required fields
- Nested JSON in content
- Unicode characters
```

---

### Step 6: Manual Testing

**Action:** Test the actual functionality

**Basic Manual Test:**
1. Run the feature with real inputs
2. Verify output is correct
3. Test error scenarios
4. Check edge cases

**Example for multi-drift-type feature:**
```bash
# Happy path
drift analyze sample.json --drift-type incomplete_work --drift-type incorrect_tool

# Single type (backward compat)
drift analyze sample.json --drift-type incomplete_work

# All types
drift analyze sample.json --drift-type incomplete_work --drift-type incorrect_tool --drift-type scope_creep

# Invalid type (error handling)
drift analyze sample.json --drift-type invalid_type

# Empty conversation
drift analyze empty.json --drift-type incomplete_work
```

**Checklist:**
- [ ] Feature works as described
- [ ] Output format is correct
- [ ] Error messages are clear
- [ ] Performance is acceptable
- [ ] No unexpected side effects

---

### Step 7: Verify Documentation

**Action:** Check that documentation is complete and accurate

**Checklist:**
- [ ] README updated if needed
- [ ] CLI help text added/updated
- [ ] Examples provided for complex features
- [ ] Docstrings complete
- [ ] No TODOs in code

**Test Documentation:**
```bash
# Verify CLI help is accurate
drift --help
drift analyze --help

# Check that examples in README work
# Copy/paste and run them
```

---

### Step 8: Check for Regressions

**Action:** Verify existing functionality still works

**Checklist:**
- [ ] All existing tests pass (not just new tests)
- [ ] Backward compatibility maintained
- [ ] No breaking changes (or properly documented)
- [ ] Related features still work

**Regression Test Examples:**
```bash
# Test features that might be affected
drift analyze old_conversation.json  # Original functionality
drift analyze --config custom.yaml   # Config still works
drift analyze --format json          # Output formats still work
```

---

### Step 9: Git Hygiene

**Action:** Verify git history is clean

**Checklist:**
- [ ] Commits are logical and atomic
- [ ] Commit messages are descriptive
- [ ] No merge conflicts
- [ ] Branch up to date with main
- [ ] No unintended files committed
- [ ] No debug code or commented blocks

**Verify:**
```bash
# Review commit history
git log origin/main..HEAD --oneline

# Check for unintended changes
git diff origin/main...HEAD

# Ensure branch is up to date
git fetch origin
git log HEAD..origin/main  # Should be empty
```

---

### Step 10: Final Validation Report

**Action:** Document that all criteria are met

**Template:**
```markdown
## Definition of Done - Validation Report

**Issue:** #[number] - [title]

### Requirements Met ✓
- All [N] acceptance criteria implemented and verified
- Requirement traceability documented above
- Functionality manually verified

### Code Quality ✓
- All linters pass (flake8, black, isort, mypy)
- No code duplication
- Type hints present
- Clear, maintainable code

### Testing ✓
- Unit tests: [N] tests added
- Integration tests: [N] tests added
- Coverage: [X]% (above 90% threshold)
- All tests passing ([N]/[N])
- Edge cases covered

### Documentation ✓
- Docstrings complete
- README updated
- CLI help updated
- Examples provided

### No Regressions ✓
- All existing tests pass
- Backward compatibility maintained
- Related features verified

### Ready for Review ✓
All definition of done criteria satisfied.
```

---

## Quick Validation Checklist

Use this for quick verification:

```markdown
## Pre-PR Validation

### Requirements
- [ ] All acceptance criteria met
- [ ] Traceability documented

### Quality
- [ ] `./lint.sh` passes
- [ ] `./test.sh --coverage` passes (90%+)
- [ ] Manual testing completed

### Documentation
- [ ] Docstrings complete
- [ ] README updated if needed
- [ ] Help text accurate

### Git
- [ ] Clean commits
- [ ] Branch up to date
- [ ] No unintended changes

Ready to create PR? ✓
```

---

## When to Stop and Fix

**Stop immediately if:**
- Linting fails
- Tests fail
- Coverage < 90%
- Core acceptance criteria not met

**Fix before PR if:**
- Missing docstrings
- Poor test quality
- Unclear commit messages
- Debug code present

**Can defer (with issue) if:**
- Nice-to-have features
- Performance optimizations
- Additional documentation
- Future refactoring ideas
