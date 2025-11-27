# Good vs Bad Issue Examples

Examples of well-written and poorly-written GitHub issues.

## Feature Request Examples

### ❌ Bad Example

```markdown
Add OpenAI support

The tool should support OpenAI.
```

**Problems:**
- No context about why
- No details about what "support" means
- No acceptance criteria
- No technical details
- Too vague to implement

### ✅ Good Example

```markdown
## Problem Statement

Users want to use Drift with OpenAI models instead of only AWS Bedrock.
This limits adoption for users without AWS accounts or those who prefer
OpenAI's models.

## Proposed Solution

Add OpenAI as a provider option alongside Bedrock. Users should be able to:
- Specify `provider: openai` in config
- Pass API key via OPENAI_API_KEY environment variable
- Use any OpenAI chat model (gpt-4, gpt-3.5-turbo, etc.)

## Acceptance Criteria

- [ ] Config supports `provider: openai` option
- [ ] OpenAI API key read from OPENAI_API_KEY env var
- [ ] All drift types work with OpenAI provider
- [ ] Tests cover OpenAI provider (mocked)
- [ ] README documents OpenAI setup
- [ ] Error messages guide users on missing API key
- [ ] Same output format as Bedrock provider

## Technical Notes

- Use openai Python package
- Support gpt-4 and gpt-3.5-turbo models
- Maintain same prompt structure as Bedrock
- Consider token limits (may differ from Bedrock)
- Add provider abstraction layer if not exists

## Related Issues

- Part of multi-provider support (#5)
- Enables #23 (Azure OpenAI support)
```

**Why it's good:**
- Clear problem and motivation
- Specific acceptance criteria
- Technical details for implementation
- Links to related work
- Complete but not overwhelming

---

## Bug Report Examples

### ❌ Bad Example

```markdown
Parser is broken

It doesn't work.
```

**Problems:**
- No details about what's broken
- No reproduction steps
- No error message
- No context
- Impossible to fix

### ✅ Good Example

```markdown
## Problem Statement

The conversation parser fails when messages contain nested JSON strings.
This crashes analysis for conversation logs that include code snippets
or JSON examples in message content.

Expected: Parser handles nested JSON gracefully
Actual: JSONDecodeError crashes the entire analysis

## Steps to Reproduce

1. Create conversation log with nested JSON:
   \`\`\`json
   {
     "messages": [{
       "role": "user",
       "content": "Parse this: {\\"key\\": \\"value\\"}"
     }]
   }
   \`\`\`
2. Run: `drift analyze conversation.json`
3. See error: JSONDecodeError

## Error Output

\`\`\`
Traceback (most recent call last):
  File "drift/parser.py", line 67, in parse_message
    content_json = json.loads(message['content'])
JSONDecodeError: Expecting ',' delimiter: line 1 column 15 (char 14)
\`\`\`

## Proposed Solution

Don't attempt to parse message content as JSON - treat it as plain text.
Only the outer structure should be JSON, not message content.

## Acceptance Criteria

- [ ] Parser handles messages with JSON-like content
- [ ] Parser handles messages with escaped quotes
- [ ] Parser handles messages with code blocks
- [ ] Tests cover nested JSON scenarios
- [ ] No regressions in existing parsing

## Technical Notes

- Issue is in parser.py:67
- Remove or make optional the content JSON parsing
- Content should be treated as plain string
- May need to update drift detection if it relies on parsed content

## Related Issues

- Similar to #45 (handling code in messages)
```

**Why it's good:**
- Clear reproduction steps
- Actual error output
- Root cause identified
- Specific fix proposed
- Tests prevent regression

---

## Documentation Examples

### ❌ Bad Example

```markdown
Improve docs

The docs need to be better.
```

**Problems:**
- No specifics about what's wrong
- No clear deliverable
- Can't determine when done

### ✅ Good Example

```markdown
## Problem Statement

New users are confused about configuration file structure. The README
shows examples but doesn't explain the schema or what each field does.

Common questions from users:
- What fields are required vs optional?
- What are valid values for each field?
- How do config files merge (global vs project)?

## Proposed Solution

Add "Configuration Reference" section to docs/ with:
- Complete schema for config.yaml and .drift.yaml
- Description of each configuration field
- Valid values and defaults
- Examples for common scenarios
- Explanation of config merging behavior

## Acceptance Criteria

- [ ] New docs/configuration.md file created
- [ ] All config fields documented with types and defaults
- [ ] Examples for: basic, advanced, multi-type configs
- [ ] Explanation of global vs project config
- [ ] README links to configuration docs
- [ ] Reviewed by 2 team members

## Technical Notes

- Reference existing config schema in config.py
- Include .drift.yaml example from tests/fixtures
- Show both minimal and full configs
- Explain precedence: CLI > project config > global config

## Related Issues

- Addresses questions in #34, #56, #78
```

**Why it's good:**
- Specific documentation gap identified
- Clear deliverable (new doc file)
- Examples of what to include
- Testable acceptance criteria

---

## Anti-Patterns to Avoid

### 1. Vague Problem

❌ "The tool is slow"
✅ "Analyzing 100+ message conversations takes >30 seconds due to sequential LLM calls"

### 2. Implementation Instead of Outcome

❌ "Add a function called process_batch() that uses multiprocessing.Pool"
✅ "Process multiple conversation logs in parallel to reduce batch analysis time"

### 3. No Acceptance Criteria

❌ Just a description, no criteria
✅ Clear checklist of what "done" means

### 4. Too Many Things

❌ Single issue covering 5 unrelated features
✅ Focused issue for one feature, with related issues linked

### 5. Assumptions About Implementation

❌ "Refactor to use class X and pattern Y"
✅ "Improve maintainability of drift detection logic" (let implementer choose how)

### 6. Missing Context

❌ "Fix the bug in detector.py"
✅ Explains what bug, how to reproduce, expected vs actual behavior

---

## Quick Validation Checklist

Before creating an issue, ask:

1. **Can someone understand the problem without asking me?**
   - If no: Add more context

2. **Could I test/verify each acceptance criterion?**
   - If no: Make criteria more specific

3. **Is the scope reasonable for one PR?**
   - If no: Split into multiple issues

4. **Do I explain why, not just what?**
   - If no: Add motivation/impact

5. **Are there related issues I should link?**
   - If yes: Add "Related Issues" section

6. **Would I want to implement this issue?**
   - If no: Improve clarity and completeness

---

## Templates Quick Reference

- **Feature:** Problem → Solution → Acceptance Criteria → Technical Notes
- **Bug:** Problem → Steps → Error → Solution → Acceptance Criteria
- **Docs:** Gap → Proposed Content → Acceptance Criteria
- **Refactor:** Current State → Proposed Improvement → Criteria → Technical Notes

All should have:
- Clear problem statement
- Specific acceptance criteria
- Technical context
- Related issues (if applicable)
