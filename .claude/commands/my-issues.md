---
description: View your assigned GitHub issues
skills:
  - github-operations
---

View GitHub issues assigned to you using the GitHub MCP server.

Use `mcp__github__list_issues` with your username as assignee filter.

Shows:
- Issue number
- Title
- Status (open/closed)
- Labels
- Last updated

Use this to check your current work items and prioritize tasks.

**Usage:**
```
/my-issues
```

**IMPORTANT:** The assistant MUST activate the `github-operations` skill before proceeding. DO NOT use the `gh` CLI command - always use the GitHub MCP server tools (mcp__github__*).
