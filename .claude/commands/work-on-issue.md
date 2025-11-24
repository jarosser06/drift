---
description: Complete workflow for implementing a GitHub issue
skills:
  - github-operations
  - python-docs
  - testing
  - definition-of-done
---

Implement a complete workflow for a GitHub issue from start to finish.

**Workflow:**

1. **Fetch Issue Details**
   - Use `mcp__github__get_issue` to get full issue details
   - Understand requirements and acceptance criteria

2. **Assign Issue**
   - Assign the issue to the current user
   - Use `mcp__github__update_issue` with assignees parameter

3. **Create Branch**
   - Create feature branch: `git checkout -b issue-<number>-<short-description>`
   - Branch naming: lowercase, hyphenated, descriptive

4. **Implementation**
   - Implement the feature/fix following the issue requirements
   - Follow Python documentation standards (python-docs skill)
   - Write clean, maintainable code

5. **Testing**
   - Create comprehensive tests (testing skill)
   - Ensure 90% code coverage
   - Run `./test.sh --coverage` to validate

6. **Validation**
   - Run `./lint.sh` to ensure code quality
   - Use definition-of-done skill to validate all requirements met
   - Create requirement traceability checklist

7. **Commit**
   - Create descriptive commit message
   - Reference issue number in commit

**Usage:**
```
/work-on-issue <issue_number>
```

**Example:**
```
/work-on-issue 42
```

**IMPORTANT:** The assistant MUST activate the `github-operations`, `python-docs`, `testing`, and `definition-of-done` skills before proceeding. DO NOT use the `gh` CLI command - always use the GitHub MCP server tools (mcp__github__*).

This will guide you through the complete workflow from issue assignment to implementation ready for PR.
