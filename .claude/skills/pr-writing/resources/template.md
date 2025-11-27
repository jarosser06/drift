# Pull Request Template

Complete template for creating well-structured pull requests.

## Standard PR Template

```markdown
## Summary

- [Brief overview of what changed]
- [Key implementation decisions]
- [Any trade-offs or architectural notes]

## Test Plan

- [ ] Unit tests added/updated
- [ ] Coverage at 90%+
- [ ] Manual testing completed
- [ ] All linters passing
- [ ] [Specific test scenarios]

## Changes

### Added
- [New files or major new functionality]

### Modified
- [Changed files with brief description]
- [Use file:line format for specific changes]

### Removed
- [Deleted files or removed functionality]

## Related Issues

Closes #[issue_number]
Relates to #[issue_number]

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## PR Template by Type

### Feature PR Template

```markdown
## Summary

- Implemented [feature name] to [purpose]
- Added [key components]
- Integrated with [existing system]
- Supports [use cases]

## Test Plan

- [ ] Unit tests for new components (15 tests added)
- [ ] Integration tests for workflow (tests/integration/test_[feature].py)
- [ ] Coverage at [X]% (above 90% threshold)
- [ ] Manual testing:
  - [ ] [Scenario 1]
  - [ ] [Scenario 2]
  - [ ] [Edge case handling]
- [ ] All linters passing (./lint.sh)

## Changes

### Added
- `drift/core/[feature].py` - [Core feature implementation]
- `tests/unit/test_[feature].py` - [Unit tests]
- `tests/integration/test_[feature]_integration.py` - [Integration tests]

### Modified
- `drift/cli.py:45-67` - [Added CLI argument for feature]
- `drift/config.py:23-34` - [Added config options]
- `README.md` - [Added usage examples and documentation]

### Removed
- None

## Related Issues

Closes #42 - [Feature name]
Relates to #15 - [Related feature]

---

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Bug Fix PR Template

```markdown
## Summary

- Fixed [bug description]
- Root cause was [explanation]
- Solution: [approach taken]

## Test Plan

- [ ] Tests prevent regression (test_[scenario].py)
- [ ] Manual verification of bug fix
- [ ] Coverage maintained at 90%+
- [ ] All existing tests still pass
- [ ] Linters passing

## Changes

### Modified
- `[file]:L[line]` - [Fix description]
- `tests/[file]` - [Regression test]

### Added
- Test case for [bug scenario]

## Related Issues

Fixes #[bug_number]

---

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Refactoring PR Template

```markdown
## Summary

- Refactored [component] to improve [quality aspect]
- Extracted [new abstractions]
- No behavior changes (backward compatible)
- Improves [testability/maintainability/performance]

## Test Plan

- [ ] All existing tests pass (no behavior change)
- [ ] New tests for extracted components
- [ ] Coverage maintained or improved
- [ ] Manual testing confirms no regressions
- [ ] Linters passing

## Changes

### Added
- `[new_file].py` - [Extracted component]
- Tests for new component

### Modified
- `[refactored_file].py` - [Refactoring description]
- Updated imports in dependent files

### Removed
- Duplicate code from [location]

## Related Issues

Enables #[future_feature]
Improves #[quality_issue]

---

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## Section Guidelines

### Summary Section

**Good:**
```
- Added OpenAI provider support alongside Bedrock
- Implemented provider abstraction layer for future providers
- Maintained backward compatibility with existing configs
- Trade-off: Slightly more complex initialization for abstraction benefits
```

**Bad:**
```
- Changed some stuff
- Fixed things
- Updated code
```

### Test Plan Section

**Good:**
```
- [ ] Unit tests for OpenAI provider (8 tests, all passing)
- [ ] Integration tests for provider switching (tests/integration/test_providers.py)
- [ ] Coverage at 92% (above 90% threshold)
- [ ] Manual testing:
  - [ ] OpenAI with gpt-4 model
  - [ ] OpenAI with gpt-3.5-turbo model
  - [ ] Error handling for missing API key
  - [ ] Fallback to Bedrock when OpenAI unavailable
- [ ] All linters passing (flake8, black, isort, mypy)
```

**Bad:**
```
- [ ] Tests added
- [ ] Tested manually
```

### Changes Section

**Good:**
```
### Added
- `drift/providers/openai.py` - OpenAI provider implementation
- `drift/providers/base.py` - Base provider abstraction
- `tests/unit/test_openai_provider.py` - OpenAI provider tests

### Modified
- `drift/core/detector.py:34-56` - Use provider abstraction
- `drift/config.py:23-29` - Add provider configuration
- `drift/cli.py:45` - Add --provider argument
- `README.md` - Document OpenAI setup and usage

### Removed
- Hard-coded Bedrock client initialization
```

**Bad:**
```
### Modified
- Updated a bunch of files
- Changed things in detector
```

---

## Title Format

```
Issue #[number]: [Descriptive title matching issue]
```

**Examples:**
- `Issue #42: Add OpenAI provider support`
- `Issue #56: Fix config parser crash on missing sections`
- `Issue #23: Refactor drift detection for multi-provider support`

---

## Pre-PR Checklist

Before creating the PR, verify:

```bash
# 1. All linters pass
./lint.sh

# 2. All tests pass with coverage
./test.sh --coverage

# 3. Branch is up to date
git fetch origin
git rebase origin/main

# 4. Review your own changes
git diff origin/main...HEAD

# 5. Verify commit messages are clean
git log origin/main..HEAD --oneline
```

---

## Size Guidelines

**Ideal PR size:**
- 200-400 lines changed (sweet spot)
- Can be reviewed in 15-30 minutes
- Focused on one feature/fix

**If PR is large (>500 lines):**
- Explain why in summary
- Break into reviewable sections
- Consider splitting if possible
- Provide detailed test plan

**Small PRs (<50 lines):**
- Still need proper description
- Explain context
- Show test coverage
