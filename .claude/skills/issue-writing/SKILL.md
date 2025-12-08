---
name: issue-writing
description: Expert in creating well-structured GitHub issues with clear problem statements and acceptance criteria using GitHub MCP. Covers feature requests, bug reports, and refactoring tasks. Use when writing or structuring GitHub issues.
---

# Issue Writing Skill

Expert in creating well-structured, actionable GitHub issues using the GitHub MCP server.

## Core Responsibilities

- Write clear problem statements
- Define specific acceptance criteria
- Provide technical context
- Make issues actionable
- Link related issues

## Issue Template

```markdown
## Problem Statement

<Clear, concise description of the problem or feature need>

Example:
The CLI currently only supports analyzing a single drift type per run.
Users need to analyze multiple drift types in one execution to avoid
running the tool multiple times on the same conversation log.

## Proposed Solution

<How this should be addressed>

Example:
Add support for specifying multiple --drift-type arguments. The tool
should perform multi-pass analysis, running each drift type detection
separately and combining results in the output.

## Acceptance Criteria

- [ ] <Specific, testable criterion 1>
- [ ] <Specific, testable criterion 2>
- [ ] <Specific, testable criterion 3>

Example:
- [ ] CLI accepts multiple --drift-type arguments
- [ ] Each drift type runs in separate LLM call
- [ ] Results are combined in single output
- [ ] Tests cover multi-type analysis
- [ ] Documentation updated with examples

## Technical Notes

<Any technical considerations, constraints, or implementation hints>

Example:
- Maintain separate LLM calls per drift type (don't combine in single prompt)
- Consider rate limiting for multiple API calls
- Output format should clearly separate results by type
- Config merge should work with multiple types

## Related Issues

<Link to related issues if applicable>

Example:
- Relates to #15 (configuration improvements)
- Blocks #22 (batch processing feature)
```

## Issue Quality Guidelines

### Problem Statement

**Good:**
- Describes specific problem or need
- Provides context and motivation
- Explains impact on users
- Includes examples if helpful

**Bad:**
- Vague or unclear
- No context provided
- Too broad or unfocused
- Assumes reader knows background

### Acceptance Criteria

**Good:**
- Specific and testable
- Focused on outcomes, not implementation
- Complete but not excessive
- Includes testing and docs

**Bad:**
- Vague ("should be better")
- Too many criteria (split into multiple issues)
- Implementation details instead of outcomes
- Missing test/doc requirements

### Technical Notes

**Good:**
- Highlights constraints
- Suggests approach without mandating
- Points out edge cases
- Links to relevant code/docs

**Bad:**
- Prescribes exact implementation
- Includes irrelevant details
- Overly technical without reason
- Missing important constraints

## Creating Issues with MCP

Use `mcp__github__create_issue`:

```python
mcp__github__create_issue(
    owner="your-org",
    repo="drift",
    title="Add multi-drift-type analysis support",
    body="""## Problem Statement

The CLI currently only supports analyzing a single drift type per run.

## Proposed Solution

Add support for multiple --drift-type arguments.

## Acceptance Criteria

- [ ] CLI accepts multiple --drift-type arguments
- [ ] Each drift type runs in separate LLM call
- [ ] Results combined in single output
- [ ] Tests cover multi-type analysis

## Technical Notes

- Maintain separate LLM calls per drift type
- Consider rate limiting for API calls
""",
    labels=["enhancement"],
    assignees=["your-username"]
)
```

## Examples

### Feature Request

```python
mcp__github__create_issue(
    owner="org",
    repo="drift",
    title="Add OpenAI provider support",
    body="""## Problem Statement

Users want to use Drift with OpenAI models instead of only AWS Bedrock.
This limits adoption for users without AWS accounts.

## Proposed Solution

Add OpenAI as a provider option alongside Bedrock. Users should be able
to specify provider in config and pass API key via environment variable.

## Acceptance Criteria

- [ ] Config supports `provider: openai` option
- [ ] OpenAI API key read from OPENAI_API_KEY env var
- [ ] All drift types work with OpenAI provider
- [ ] Tests cover OpenAI provider (mocked)
- [ ] README documents OpenAI setup
- [ ] Error messages guide users on missing API key

## Technical Notes

- Use openai Python package
- Support GPT-4 and GPT-3.5-turbo models
- Maintain same prompt structure as Bedrock
- Consider token limits (may differ from Bedrock)

## Related Issues

- Part of multi-provider support (#5)
""",
    labels=["enhancement", "provider-support"]
)
```

### Bug Report

```python
mcp__github__create_issue(
    owner="org",
    repo="drift",
    title="Config parser crashes on missing drift_types section",
    body="""## Problem Statement

The config parser crashes with KeyError when .drift.yaml is missing
the `drift_types` section, even though this should be optional.

## Proposed Solution

Add proper defaults and validation for config parsing. If drift_types
is missing, use built-in defaults. Provide clear error for invalid config.

## Acceptance Criteria

- [ ] Parser handles missing drift_types gracefully
- [ ] Uses built-in defaults when not specified
- [ ] Validates config schema on load
- [ ] Clear error messages for invalid config
- [ ] Tests cover missing and invalid configs

## Technical Notes

- Error occurs in config.py:load_project_config()
- Should use built-in DRIFT_TYPES constant as default
- Consider using pydantic for schema validation

## Related Issues

- Fixes regression from #12
""",
    labels=["bug", "priority:high"]
)
```

## Resources

### 📖 [Issue Templates](resources/templates.md)
Complete templates for feature requests, bug reports, documentation, and refactoring issues.

**Use when:** Creating a new GitHub issue and need structure.
