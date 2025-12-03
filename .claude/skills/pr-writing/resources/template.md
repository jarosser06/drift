# Pull Request Template

Use this as a reference when creating PRs. Adapt based on the type of change.

## Standard Template

```markdown
## Summary
- [Brief overview of what changed]
- [Key implementation decisions]
- [Any trade-offs or notes]

## Test Plan
- [ ] Unit tests added/updated
- [ ] Coverage at 90%+
- [ ] Manual testing completed
- [ ] All linters passing

## Changes
### Added
- [New files or functionality]

### Modified
- [Changed files with file:line references]

### Removed
- [Deleted files or functionality]

## Related Issues
Closes #[number]

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Key Patterns by PR Type

**Feature PR:**
- Summary: Focus on what the feature does and why it's needed
- Test Plan: Include both unit and integration tests
- Changes: Highlight new files and integration points

**Bug Fix PR:**
- Summary: Explain root cause and solution approach
- Test Plan: Include regression test
- Changes: Focus on minimal, targeted changes

**Refactoring PR:**
- Summary: Emphasize no behavior changes, explain benefits
- Test Plan: Verify all existing tests still pass
- Changes: Show code extraction and cleanup

## Quality Tips

**Summary (3-5 bullets):**
- Focus on WHAT changed and WHY
- Mention architectural decisions
- Note any trade-offs

**Test Plan (be specific):**
- State exact test count and files
- List manual testing scenarios
- Include coverage percentage
- Confirm linters pass

**Changes (organized):**
- Use file:line format (e.g., `cli.py:45-67`)
- Group by Added/Modified/Removed
- Brief description for each change

## Pre-PR Checklist

```bash
./lint.sh && ./test.sh --coverage  # Validate quality
git diff main...HEAD               # Review changes
git fetch && git rebase main       # Update branch
```

**Size Guidelines:**
- Ideal: 200-400 lines (reviewable in 15-30 min)
- Large PRs (>500 lines): Explain why, break into sections
- Small PRs (<50 lines): Still need proper context
