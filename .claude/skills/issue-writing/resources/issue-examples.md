# Issue Examples by Type

Complete examples for different issue types.

## Common Issue Workflows

### Creating Issue for New Feature

```python
# 1. Gather context about the feature
# - What problem does it solve?
# - Who needs it?
# - What's the expected behavior?

# 2. Draft issue with all sections
issue_body = """## Problem Statement
Users need to...

## Proposed Solution
Add support for...

## Acceptance Criteria
- [ ] Feature works as described
- [ ] Tests added
- [ ] Docs updated

## Technical Notes
Consider...
"""

# 3. Create issue with appropriate labels
issue = mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Add feature X",
    body=issue_body,
    labels=["enhancement"]
)

# 4. Link related issues if applicable
mcp__github__add_issue_comment(
    owner="jarosser06",
    repo="drift",
    issue_number=issue["number"],
    body="Related to #42 and #45"
)
```

### Creating Bug Report

```python
# 1. Reproduce the bug
# - Document steps to reproduce
# - Capture error messages
# - Note expected vs actual behavior

# 2. Create detailed bug report
bug_report = """## Problem Statement
When doing X, Y happens instead of Z.

Steps to reproduce:
1. Run command: drift analyze log.json
2. See error: KeyError: 'drift_types'

Expected: Should use default drift types
Actual: Crashes with KeyError

## Proposed Solution
Add defaults for config...

## Acceptance Criteria
- [ ] Bug fixed
- [ ] Tests prevent regression
"""

# 3. Create issue with bug label and priority
mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Fix config parser crash",
    body=bug_report,
    labels=["bug", "priority:high"]
)
```

## Feature Request Example

```python
mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Add OpenAI provider support",
    body="""## Problem Statement

Users want to use Drift with OpenAI models instead of only AWS Bedrock.
This limits adoption for users without AWS accounts or those who prefer
OpenAI's API and pricing model.

Current workaround: None - users must use Bedrock or fork the project.

## Proposed Solution

Add OpenAI as a provider option alongside Bedrock.

Users should be able to configure:
```yaml
provider: openai
model: gpt-4
```

And set their API key via environment variable.

## Acceptance Criteria

- [ ] Config supports `provider: openai` option
- [ ] OpenAI API key read from environment variable
- [ ] All drift types work with OpenAI provider
- [ ] Tests cover OpenAI provider (mocked API calls)
- [ ] README documents OpenAI setup and configuration
- [ ] Error messages guide users on missing API key
- [ ] Maintains backward compatibility (defaults to bedrock)

## Related Issues

- Part of multi-provider support initiative (#5)
""",
    labels=["enhancement"],
    assignees=[]
)
```

## Bug Report Example

```python
mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Config parser crashes on missing drift_types section",
    body="""## Problem Statement

The config parser crashes with KeyError when .drift.yaml is missing
the `drift_types` section, even though this section should be optional.

Steps to reproduce:
1. Create minimal .drift.yaml: `provider: bedrock`
2. Run: `drift analyze log.json`
3. Error: `KeyError: 'drift_types'`

Expected: Should use default drift types when not specified.

Impact: Users cannot use minimal config files, must specify all sections.

## Proposed Solution

Add defaults for optional config sections. When a section is missing,
use built-in defaults instead of crashing.

## Acceptance Criteria

- [ ] Parser handles missing drift_types gracefully
- [ ] Uses built-in defaults when sections missing
- [ ] Parser handles missing provider section
- [ ] Clear error messages for invalid values
- [ ] Tests cover: missing sections, empty file, invalid values
- [ ] Works with minimal config: `provider: bedrock`

## Related Issues

- Fixes regression introduced in #12 (config refactoring)
""",
    labels=["bug", "priority:high"],
    assignees=[]
)
```

## Refactoring Example

```python
mcp__github__create_issue(
    owner="jarosser06",
    repo="drift",
    title="Refactor detector to use plugin architecture",
    body="""## Problem Statement

Current detector implementation has all drift type detection logic in
a single 500+ line file. Adding new drift types requires modifying
core detector code, making it hard to:
- Add custom drift type detections
- Test individual detectors in isolation
- Maintain as complexity grows

## Proposed Solution

Refactor to plugin-based architecture where each drift type has its
own detector class with a common interface.

Benefits:
- Easy to add new detectors without modifying core
- Better testability (test each detector independently)
- Enables user-defined custom detectors

## Acceptance Criteria

- [ ] Base detector interface defined
- [ ] Each drift type has dedicated detector class
- [ ] Main analyzer orchestrates detector plugins
- [ ] Tests refactored to test individual detectors
- [ ] Documentation explains plugin architecture
- [ ] No behavior changes (refactoring only)
- [ ] All existing tests still pass
- [ ] Code coverage remains ≥ 90%

## Related Issues

- Enables #45 (custom user-defined detectors)
- Improves #30 (better test isolation)
""",
    labels=["refactoring", "architecture"],
    assignees=[]
)
```
