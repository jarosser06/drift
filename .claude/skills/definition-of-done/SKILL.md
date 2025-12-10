---
name: definition-of-done
description: Expert in validating work meets all requirements, acceptance criteria, testing, and quality standards. Use when verifying task completion before creating a PR or reviewing pull requests against requirements.
---

# Definition of Done Skill

Expert in validating that work meets all requirements and quality standards.

## Core Responsibilities

- Validate work against issue requirements
- Ensure all acceptance criteria met
- Verify comprehensive testing
- Check documentation completeness
- Confirm code quality standards
- Create requirement traceability

## Validation Checklist

### 1. Requirements Traceability

Map each acceptance criterion to implementation:

```markdown
## Requirement Traceability

- [x] **AC1:** Add CLI argument for drift type
  - Implementation: `drift/cli.py:45-52`
  - Tests: `tests/unit/test_cli.py:test_drift_type_argument`

- [x] **AC2:** Support multiple drift types
  - Implementation: `drift/detector.py:analyze_multi_pass`
  - Tests: `tests/integration/test_multi_pass.py`

- [x] **AC3:** Output results to stdout
  - Implementation: `drift/formatter.py:format_output`
  - Tests: `tests/unit/test_formatter.py`
```

### 2. Code Quality

- [ ] All linters pass (`./lint.sh`)
- [ ] Code follows project patterns
- [ ] No code duplication
- [ ] Proper error handling
- [ ] Type hints on public functions
- [ ] No debug code or commented blocks

### 3. Testing

- [ ] Unit tests written for new code
- [ ] Integration tests for workflows
- [ ] Edge cases covered
- [ ] All tests pass (`./test.sh`)
- [ ] Coverage ≥ 90% (`./test.sh --coverage`)
- [ ] Mocks used appropriately

### 4. Documentation

- [ ] Docstrings on all public functions
- [ ] README updated if needed
- [ ] CLI help text added/updated
- [ ] Examples provided for complex features
- [ ] No TODOs in code

### 5. Functionality

- [ ] Feature works as described
- [ ] No regressions introduced
- [ ] Error messages are clear
- [ ] Performance is acceptable
- [ ] Works with sample data

### 6. Git Hygiene

- [ ] Commits are logical and atomic
- [ ] Commit messages are descriptive
- [ ] No merge conflicts
- [ ] Branch is up to date with main
- [ ] No unintended files committed

## Pre-PR Validation

Before creating a PR, verify:

1. **Run Full Check**
   ```bash
   ./lint.sh && ./test.sh --coverage
   ```

2. **Review Changes**
   ```bash
   git diff main...HEAD
   ```

3. **Test Manually**
   - Run CLI with real inputs
   - Verify output format
   - Check error scenarios

4. **Check Traceability**
   - All acceptance criteria implemented
   - Each criterion has tests
   - Requirements fully satisfied

## Common Gaps to Watch For

### Incomplete Implementation
- Feature partially works
- Edge cases not handled
- Error handling missing

### Testing Gaps
- Missing unit tests
- Integration tests not comprehensive
- Coverage below 90%
- Edge cases not tested

### Documentation Gaps
- Missing docstrings
- Unclear parameter descriptions
- No usage examples
- README not updated

### Quality Issues
- Linting errors
- Type hint missing
- Code duplication
- Poor naming

## Validation Report Template

```markdown
## Definition of Done - Validation Report

**Issue:** #<number> - <title>

### Requirements Met
✓ All acceptance criteria implemented
✓ Requirement traceability documented
✓ Functionality verified

### Code Quality
✓ All linters pass
✓ Type hints present
✓ No code duplication

### Testing
✓ Unit tests: <count> tests
✓ Integration tests: <count> tests
✓ Coverage: <percentage>%
✓ All tests passing

### Documentation
✓ Docstrings complete
✓ README updated
✓ Examples provided

### Ready for Review
All definition of done criteria satisfied.
```

## Resources

### 📖 [Validation Guide](resources/validation-guide.md)
Step-by-step guide for validating work meets all requirements and quality standards.

**Use when:** Verifying task completion before creating a PR.

### 📖 [Common Gaps](resources/common-gaps.md)
Common completion gaps to watch for with examples and fixes.

**Use when:** Checking for typical issues that cause work to be incomplete.
