# Issue Templates

Complete issue templates for different types of GitHub issues.

## Feature Request Template

```markdown
## Problem Statement

[Clear description of the problem or need]

Users want to [capability] but currently the tool [limitation].
This prevents [impact on users/workflow].

## Proposed Solution

[How this should be addressed]

Add [feature/capability] that allows users to [benefit].
Implementation should [key requirements].

## Acceptance Criteria

- [ ] [Specific, testable criterion 1]
- [ ] [Specific, testable criterion 2]
- [ ] [Specific, testable criterion 3]
- [ ] Tests cover new functionality (90%+ coverage)
- [ ] Documentation updated with examples

## Technical Notes

[Technical considerations, constraints, or implementation hints]

- Consider [constraint or edge case]
- Should integrate with [existing component]
- May require [dependency or change]

## Related Issues

- Relates to #[number] ([brief description])
- Blocks #[number] ([brief description])
```

### Example: Feature Request

```markdown
## Problem Statement

Users want to analyze multiple conversation logs in batch mode but currently
the tool only processes one log at a time. This prevents efficient analysis
of large datasets.

## Proposed Solution

Add a `--batch` mode that accepts a directory of conversation logs and
processes them in parallel, generating a consolidated report.

## Acceptance Criteria

- [ ] CLI accepts `--batch <directory>` argument
- [ ] Processes all .json files in directory
- [ ] Parallel processing (configurable concurrency)
- [ ] Generates per-file and aggregate reports
- [ ] Tests cover batch processing (90%+ coverage)
- [ ] Documentation includes batch mode examples

## Technical Notes

- Use multiprocessing for parallel analysis
- Consider rate limiting for LLM API calls
- Output should show progress for large batches
- Handle failures gracefully (don't stop entire batch)

## Related Issues

- Relates to #23 (performance improvements)
- Enables #45 (CI/CD integration)
```

---

## Bug Report Template

```markdown
## Problem Statement

[Clear description of the bug]

[Component/function] crashes/fails when [scenario].
Expected behavior: [what should happen]
Actual behavior: [what actually happens]

## Steps to Reproduce

1. [First step]
2. [Second step]
3. [See error]

## Error Output

\`\`\`
[Paste error message or stack trace]
\`\`\`

## Proposed Solution

[How to fix the bug]

Add [validation/check/fix] to handle [scenario].

## Acceptance Criteria

- [ ] Bug no longer occurs in reproduction steps
- [ ] Error handling is graceful
- [ ] Clear error message for users
- [ ] Tests prevent regression
- [ ] Edge cases covered

## Technical Notes

- Error occurs in [file:line]
- Root cause is [reason]
- Should also check [related scenarios]

## Related Issues

- Fixes regression from #[number]
- Related to #[number]
```

### Example: Bug Report

```markdown
## Problem Statement

Config parser crashes with KeyError when .drift.yaml is missing the
`drift_types` section, even though this should be optional.

Expected behavior: Use built-in default drift types
Actual behavior: KeyError: 'drift_types'

## Steps to Reproduce

1. Create .drift.yaml with only `llm_config:` section
2. Run `drift analyze test.json`
3. See error: KeyError: 'drift_types'

## Error Output

\`\`\`
Traceback (most recent call last):
  File "drift/config.py", line 45, in load_project_config
    types = config['drift_types']
KeyError: 'drift_types'
\`\`\`

## Proposed Solution

Add proper defaults and validation for config parsing. If drift_types
is missing, use built-in defaults from DRIFT_TYPES constant.

## Acceptance Criteria

- [ ] Parser handles missing drift_types gracefully
- [ ] Uses built-in defaults when not specified
- [ ] Validates config schema on load
- [ ] Clear error messages for truly invalid config
- [ ] Tests cover missing and partial configs

## Technical Notes

- Error occurs in config.py:load_project_config()
- Should use DRIFT_TYPES constant as default
- Consider using pydantic for schema validation
- Check other optional config sections too

## Related Issues

- Fixes regression from #12
```

---

## Documentation Improvement Template

```markdown
## Problem Statement

[What documentation is missing or unclear]

Users are confused about [topic] because [reason].
Current documentation [gap or issue].

## Proposed Solution

[How to improve documentation]

Add/update documentation to explain [topic] with:
- [Key concept to cover]
- [Example to include]
- [Common pitfall to address]

## Acceptance Criteria

- [ ] Documentation is clear and accurate
- [ ] Examples are provided
- [ ] Common questions addressed
- [ ] Accessible to target audience
- [ ] Reviewed for technical accuracy

## Related Issues

- Addresses question in #[number]
```

### Example: Documentation Improvement

```markdown
## Problem Statement

Users are confused about how to configure custom drift types because
the README only shows using built-in types. The .drift.yaml schema
is not documented.

## Proposed Solution

Add a "Custom Drift Types" section to README.md that explains:
- How to define custom drift types in .drift.yaml
- Required fields (name, description, prompt, signals)
- Example custom drift type with full configuration
- How custom types merge with built-in types

## Acceptance Criteria

- [ ] README has "Custom Drift Types" section
- [ ] Full example of custom drift type config
- [ ] Explains all required and optional fields
- [ ] Shows how to use custom type in CLI
- [ ] Links to example .drift.yaml in repo

## Related Issues

- Addresses question in #34
```

---

## Refactoring Template

```markdown
## Problem Statement

[What code needs refactoring and why]

[Component] is difficult to maintain/test/extend because [reason].
This impacts [development velocity/quality/etc].

## Proposed Solution

Refactor [component] to [improvement]:
- [Change 1]
- [Change 2]
- [Change 3]

## Acceptance Criteria

- [ ] Code is more maintainable
- [ ] Tests are easier to write
- [ ] No behavior changes (backward compatible)
- [ ] All existing tests still pass
- [ ] New tests added if needed
- [ ] Documentation updated

## Technical Notes

- Preserve existing API if possible
- Consider [constraint]
- May need to update [dependent code]

## Related Issues

- Enables #[number] ([future feature])
```

---

## Quick Issue Checklist

Use this to verify your issue before creating:

- [ ] **Clear problem statement** - Anyone can understand what needs to be done
- [ ] **Specific acceptance criteria** - Testable and unambiguous
- [ ] **Technical context** - Enough detail for implementation
- [ ] **Not too broad** - Can be completed in reasonable time
- [ ] **Value is clear** - Why this matters to users/project
- [ ] **Labels added** - bug, enhancement, documentation, etc.
- [ ] **Related issues linked** - Shows context and dependencies
