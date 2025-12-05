---
description: Complete workflow for implementing a GitHub issue
skills:
  - github-operations
  - python-docs
  - testing
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
   - **MANDATORY:** Use the Task tool with subagent_type='developer' to implement the feature/fix
   - The developer agent will follow Python documentation standards and write clean code
   - DO NOT implement the code yourself - delegate to the developer agent

5. **Testing**
   - **MANDATORY:** Use the Task tool with subagent_type='qa' to create comprehensive tests
   - The qa agent will ensure 90%+ code coverage
   - DO NOT write tests yourself - delegate to the qa agent

6. **Validation**
   - Run `./lint.sh` to ensure code quality
   - Run `./test.sh --coverage` to verify coverage meets 90%+ requirement
   - Validate all requirements are met

7. **Present Summary**
   - Provide detailed summary of changes made
   - List all files created and modified
   - Show quality metrics (coverage, test counts)
   - Give user opportunity to review before committing
   - DO NOT automatically commit - wait for user to review and commit manually

**Usage:**
```
/work-on-issue <issue_number>
```

**Example:**
```
/work-on-issue 42
```

**IMPORTANT:** The assistant MUST activate the `github-operations`, `python-docs`, and `testing` skills before proceeding. DO NOT use the `gh` CLI command directly - always use the GitHub MCP server tools (mcp__github__*).

The assistant will:
1. Activate the required skills listed in the frontmatter
2. Fetch and understand the issue requirements using `mcp__github__get_issue`
3. Create a feature branch with proper naming
4. **MUST use Task tool with subagent_type='developer'** for implementation - do NOT implement code directly
5. **MUST use Task tool with subagent_type='qa'** for testing - do NOT write tests directly
6. Validate quality with ./lint.sh and ./test.sh
7. Present summary of changes for user review
8. **DO NOT commit automatically** - user will review and commit when ready

This workflow ensures specialized agents handle their domains of expertise from issue assignment to implementation, while giving the user full control over when to commit changes.
