---
name: pr-writing
description: Expert in creating well-structured pull requests with clear summaries and test plans. Use when writing or structuring PRs.
---

# PR Writing Skill

Expert in creating well-structured, reviewable pull requests using the GitHub MCP server.

## Core Responsibilities

- Write clear PR descriptions
- Provide comprehensive test plans
- Summarize changes effectively
- Link to related issues
- Make PRs easy to review

## PR Template Structure

All PRs should include these sections:
- **Summary** - 3-5 bullet points covering what changed and why
- **Test Plan** - Specific tests run, coverage %, manual testing scenarios
- **Changes** - Organized by Added/Modified/Removed with file paths
- **Related Issues** - Links to relevant issues

**Example (brief):**
```markdown
## Summary
- Added multi-drift-type analysis support
- Implemented sequential processing

## Test Plan
- [x] Unit tests added (10 new tests)
- [x] Coverage at 92%

## Changes
### Added
- `drift/multi_analyzer.py` - Multi-pass analysis

### Modified
- `drift/cli.py:45-67` - Multi-type support
```

📖 **See [resources/template.md](resources/template.md) for complete PR template with detailed examples.**

## PR Quality Guidelines

### Title Format

Format: `Issue #<number>: <Descriptive title>`

**Good:**
- `Issue #42: Add multi-drift-type analysis support`
- `Issue #15: Fix config parser KeyError on missing sections`
- `Issue #8: Improve CLI output formatting`

**Bad:**
- `Update cli.py` (no context)
- `Fix bug` (which bug?)
- `Add feature` (which feature?)

### Summary Section

**Good:**
- 3-5 bullet points
- Focuses on what and why
- Mentions key decisions
- Highlights any trade-offs

**Bad:**
- Too verbose (wall of text)
- Lists every single change
- Missing the "why"
- Implementation minutiae

### Test Plan

**Good:**
- Specific test types listed
- Coverage percentage stated
- Manual testing scenarios
- Validation steps clear

**Bad:**
- "Tests added" (too vague)
- Missing coverage info
- No manual testing
- Linting not verified

### Changes Section

**Good:**
- Organized by Added/Modified/Removed
- File paths with line numbers for context
- Brief description of each change
- Highlights important files

**Bad:**
- Unorganized list
- No file paths
- Missing descriptions
- Every file listed (use summary instead)

## Creating PRs with MCP

Use `mcp__github__create_pull_request`:

```python
mcp__github__create_pull_request(
    owner="your-org",
    repo="drift",
    title="Issue #42: Add multi-drift-type support",
    head="issue-42-add-multi-type",
    base="main",
    body="""## Summary

- Added multi-drift-type analysis support to CLI
- Implemented sequential processing for each drift type
- Combined results in unified output format

## Test Plan

- [x] Unit tests added (10 new tests)
- [x] Coverage at 92%
- [x] Manual testing with multiple types
- [x] All linters passing

## Changes

### Added
- `drift/multi_analyzer.py` - Multi-pass analysis
- Tests in `tests/integration/test_multi_pass.py`

### Modified
- `drift/cli.py:45-67` - Multi-type support
- `README.md` - Usage examples

## Related Issues

Closes #42

""",
    draft=False
)
```

## Pre-PR Checklist

Before creating PR:

1. **Validate Quality**
   ```bash
   ./lint.sh && ./test.sh --coverage
   ```

2. **Review Your Changes**
   ```bash
   git diff main...HEAD
   ```

3. **Update Branch**
   ```bash
   git fetch origin
   git rebase origin/main
   ```

4. **Push Branch**
   ```bash
   git push -u origin issue-42-add-feature
   ```

5. **Create PR via MCP**
   Use `mcp__github__create_pull_request` as shown above

## Review Readiness

A good PR is:
- **Focused** - Single feature/fix, not multiple unrelated changes
- **Tested** - Comprehensive tests with 90%+ coverage
- **Documented** - Code docs and README updated
- **Clean** - No debug code, commented blocks, or unrelated changes
- **Validated** - All linters and tests passing

## Resources

### 📖 [PR Template](resources/template.md)
Complete pull request templates for features, bug fixes, and refactoring.

**Use when:** Creating a new pull request and need structure.

### 📖 [Good PR Examples](resources/good-examples.md)
Real examples of excellent pull requests with annotations.

**Use when:** Learning what makes a good PR or validating your PR before creating it.
