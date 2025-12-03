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

**CRITICAL REQUIREMENTS:**
1. **MUST use the Task tool with subagent_type='developer'** for implementation - do NOT implement code directly
2. **MUST use the Task tool with subagent_type='qa'** for testing - do NOT write tests directly
3. **MUST activate the `github-operations` skill** for GitHub operations
4. **DO NOT use the `gh` CLI command** - always use the GitHub MCP server tools (mcp__github__*)
5. Delegate all implementation work to the developer agent
6. Delegate all test writing to the qa agent
7. Only coordinate the workflow and handle git operations yourself

This workflow ensures specialized agents handle their domains of expertise from issue assignment to implementation ready for PR.
