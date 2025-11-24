---
description: Create PR with quality validation
skills:
  - pr-writing
  - testing
  - linting
  - github-operations
---

Create a pull request with comprehensive quality checks.

**Pre-PR Validation:**

1. **Run Tests with Coverage**
   ```bash
   ./test.sh --coverage
   ```
   - Requires 90% minimum coverage
   - All tests must pass

2. **Run Linters**
   ```bash
   ./lint.sh
   ```
   - All linters must pass (flake8, black, isort, mypy)

3. **Review Changes**
   - Ensure all changes are intentional
   - Verify no debug code or commented blocks
   - Check for proper error handling

**Create PR:**

Use `mcp__github__create_pull_request` with standardized format:

```
title: "Issue #<number>: <descriptive title>"
body:
## Summary
- <Brief overview of changes>
- <Key implementation details>
- <Any architectural decisions>

## Test Plan
- [ ] Unit tests added/updated
- [ ] Coverage at 90%+
- [ ] Manual testing completed
- [ ] All linters passing

## Changes
- <List of main changes>
- <Files modified and why>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Usage:**
```
/create-pr
```

**IMPORTANT:** The assistant MUST activate the `pr-writing`, `testing`, `linting`, and `github-operations` skills before proceeding. DO NOT use the `gh` CLI command - always use the GitHub MCP server tools (mcp__github__*).

This will validate code quality and create a well-structured PR ready for review.
