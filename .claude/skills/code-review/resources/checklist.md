# Code Review Checklist

Comprehensive checklist for reviewing code in Drift.

## Pre-Review

- [ ] Linked issue reviewed
- [ ] Understand the context and purpose
- [ ] Know what problem is being solved
- [ ] Check acceptance criteria

## Code Quality

### Structure & Organization
- [ ] Code is well-organized and logical
- [ ] Functions/methods have single responsibility
- [ ] No code duplication (DRY principle)
- [ ] Appropriate abstraction levels
- [ ] Clear module boundaries

### Naming & Readability
- [ ] Names are descriptive and accurate
- [ ] No misleading or confusing names
- [ ] Consistent naming conventions
- [ ] Code is self-explanatory
- [ ] Comments explain "why", not "what"

### Imports
- [ ] **CRITICAL:** All imports at top of file (NO inline imports)
- [ ] Imports organized: stdlib → third-party → local
- [ ] No unused imports
- [ ] No wildcard imports (`from x import *`)

## Architecture & Design

- [ ] Fits with existing architecture
- [ ] Proper separation of concerns
- [ ] Scalable design
- [ ] Appropriate use of patterns
- [ ] Error handling is comprehensive
- [ ] No circular dependencies

## Testing

### Test Coverage
- [ ] Unit tests for all new code
- [ ] Integration tests for workflows
- [ ] Coverage ≥ 90% (`./test.sh --coverage`)
- [ ] All tests passing (`./test.sh`)

### Test Quality
- [ ] Tests verify behavior, not implementation
- [ ] Edge cases covered
- [ ] Error scenarios tested
- [ ] Tests are clear and maintainable
- [ ] Proper use of mocks/fixtures
- [ ] No flaky tests

## Documentation

**CRITICAL: Verify documentation matches code changes**

- [ ] Docstrings on all public functions
- [ ] Parameters documented with `-- param:`
- [ ] Return values documented
- [ ] Exceptions documented (Raises)
- [ ] **Configuration changes documented where appropriate**
- [ ] **CLI changes reflected in help text**
- [ ] Examples for complex features in docstrings
- [ ] **All code changes reflected in documentation**
- [ ] **New attributes/parameters documented in docstrings**
- [ ] **Breaking changes clearly documented**

## Recommendations

**CRITICAL: All recommendations must be research-backed**

- [ ] Recommendations researched using Context7 MCP or official docs
- [ ] Sources cited for each recommendation
- [ ] Recommendations verified against project's Python version
- [ ] Recommendations checked against existing codebase patterns
- [ ] Only high-impact, well-researched recommendations included

## Security

- [ ] No hardcoded credentials
- [ ] Proper input validation
- [ ] Safe file path handling
- [ ] No command injection risks
- [ ] API keys handled securely
- [ ] No sensitive data in logs
- [ ] No SQL injection vulnerabilities

## Performance

- [ ] No obvious bottlenecks
- [ ] Efficient algorithms
- [ ] Appropriate data structures
- [ ] Resources cleaned up properly
- [ ] No unnecessary API calls
- [ ] Reasonable memory usage

## Linting & Style

- [ ] All linters pass (`./lint.sh`)
- [ ] flake8 clean
- [ ] black formatting applied
- [ ] isort imports sorted
- [ ] mypy type checks pass
- [ ] No debug code or commented blocks

## Git Hygiene

- [ ] Commits are logical and atomic
- [ ] Commit messages are descriptive
- [ ] No merge conflicts
- [ ] Branch up to date with main
- [ ] No unintended files committed
- [ ] Proper branch naming (`issue-N-description`)

## Final Checks

- [ ] Manual testing performed
- [ ] No regressions introduced
- [ ] Performance is acceptable
- [ ] Error messages are clear
- [ ] All acceptance criteria met
- [ ] Ready for production
