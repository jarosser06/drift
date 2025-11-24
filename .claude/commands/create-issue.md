---
description: Create well-structured GitHub issue
skills:
  - issue-writing
  - github-operations
---

Create a well-structured GitHub issue with clear requirements.

**Issue Structure:**

```markdown
## Problem Statement
<Clear description of the problem or feature need>

## Proposed Solution
<How this should be addressed>

## Acceptance Criteria
- [ ] <Specific, testable criterion 1>
- [ ] <Specific, testable criterion 2>
- [ ] <Specific, testable criterion 3>

## Technical Notes
<Any technical considerations, constraints, or implementation hints>

## Related Issues
<Link to related issues if applicable>
```

**Usage:**
```
/create-issue
```

**IMPORTANT:** The assistant MUST activate the `github-operations` and `issue-writing` skills before proceeding. DO NOT use the `gh` CLI command directly - always use the GitHub MCP server tools (mcp__github__*).

The assistant will:
1. Activate the required skills listed in the frontmatter
2. Gather information about the issue from the user
3. Create a properly formatted issue using `mcp__github__create_issue` from the GitHub MCP server
