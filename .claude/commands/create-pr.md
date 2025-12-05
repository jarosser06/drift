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
title: "Issue #<number>: <descriptive title from issue>"
body:
## Summary
- <3-5 bullet points describing what changed>
- <Focus on what was implemented, not how>

## Test Plan
- [ ] Unit tests added/updated
- [ ] Coverage at X%
- [ ] Manual testing completed
- [ ] All linters passing

## Changes
### Added
- <New files with brief description>

### Modified
- <Changed files with brief description>

## Related Issues
Closes #<number>

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Usage:**
```
/create-pr
```

**IMPORTANT:** The assistant MUST activate the `pr-writing`, `testing`, `linting`, and `github-operations` skills before proceeding. DO NOT use the `gh` CLI command directly - always use the GitHub MCP server tools (mcp__github__*).

The assistant will:
1. Activate the required skills listed in the frontmatter
2. Check current branch name to determine issue number (format: issue-<number>-description)
3. Fetch the issue details using `mcp__github__get_issue` to understand what's being solved
4. Run pre-PR validation (tests and linters)
5. Review changes to ensure quality
6. Draft the PR content following the template and present it to the user for approval
7. **ONLY** create the PR using `mcp__github__create_pull_request` after receiving explicit user approval

**CRITICAL:** The assistant MUST NOT create the GitHub pull request until the user has explicitly approved the drafted PR content.

This will validate code quality and create a well-structured PR ready for review.
