# Good Pull Request Examples

Examples of excellent pull requests with annotations.

## Example 1: Feature Implementation

```markdown
## Summary

- Added multi-drift-type analysis support to CLI
- Implemented sequential processing for each drift type (maintaining prompt clarity)
- Combined results in unified linter-style output with type labels
- Added comprehensive tests with 92% coverage

**Key decisions:**
- Chose sequential over parallel LLM calls to avoid rate limiting issues
- Each drift type gets separate API call for clearer prompts and better results
- Output format groups detections by type for easy scanning

## Test Plan

- [ ] Unit tests for multi-type argument parsing (tests/unit/test_cli.py)
- [ ] Integration tests for multi-pass analysis (tests/integration/test_multi_pass.py)
- [ ] Coverage at 92% (above 90% threshold)
- [ ] Manual testing:
  - [ ] Single drift type (backward compatibility)
  - [ ] Two drift types (incomplete_work + incorrect_tool)
  - [ ] All built-in drift types (5 types)
  - [ ] Custom + built-in types mixed
  - [ ] Empty results handling
- [ ] All linters passing (flake8, black, isort, mypy)

## Changes

### Added
- `drift/core/multi_analyzer.py` - Multi-pass analysis orchestration
- `tests/unit/test_multi_analyzer.py` - Unit tests (12 tests)
- `tests/integration/test_multi_pass.py` - Integration tests (5 tests)
- `tests/fixtures/multi_type_conversation.json` - Test fixture

### Modified
- `drift/cli.py:45-67` - Added `--drift-type` multiple argument support
- `drift/core/detector.py:23-34` - Extract single-type detection to helper
- `drift/formatter.py:56-89` - Enhanced output to show drift type labels
- `README.md:78-95` - Added multi-type usage examples
- `README.md:34-38` - Updated quick start with multi-type example

### Removed
- None

## Related Issues

Closes #42 - Add multi-drift-type analysis support
Relates to #15 - Configuration improvements (enables per-type config)

---

```

**Why this is excellent:**
- ✅ Clear summary with key decisions explained
- ✅ Comprehensive test plan with specific scenarios
- ✅ File changes with line numbers
- ✅ Shows backward compatibility consideration
- ✅ Links related issues
- ✅ Trade-offs documented (sequential vs parallel)

---

## Example 2: Bug Fix

```markdown
## Summary

- Fixed config parser crash when .drift.yaml is missing `drift_types` section
- Root cause: Code assumed all config sections were present
- Solution: Added safe dict access with built-in defaults

## Test Plan

- [ ] Test prevents regression (tests/unit/test_config.py::test_missing_drift_types)
- [ ] Verified fix with minimal .drift.yaml (only llm_config section)
- [ ] All existing tests still pass (no behavior change for valid configs)
- [ ] Coverage maintained at 91%
- [ ] Linters passing

## Changes

### Modified
- `drift/config.py:45-52` - Use dict.get() with DRIFT_TYPES default
- `drift/config.py:67-73` - Added schema validation helper
- `tests/unit/test_config.py` - Added regression test for missing sections

### Added
- Test cases for missing drift_types, llm_config, and custom_prompts

## Related Issues

Fixes #56 - Config parser crashes on missing drift_types section

---

```

**Why this is excellent:**
- ✅ Explains root cause and solution
- ✅ Shows regression test added
- ✅ Confirms no side effects
- ✅ Concise but complete

---

## Example 3: Refactoring

```markdown
## Summary

- Refactored drift detection to use provider abstraction layer
- Extracted LLM client logic to separate provider classes
- No behavior changes - backward compatible with existing code
- Enables future multi-provider support (OpenAI, Azure, etc.)

**Benefits:**
- Easier to test (providers can be mocked independently)
- Simpler to add new providers (implement base interface)
- Clearer separation of concerns (detection vs LLM interaction)

## Test Plan

- [ ] All existing tests pass (158/158 passing)
- [ ] New tests for provider abstraction (tests/unit/test_providers.py)
- [ ] Coverage increased to 93% (was 91%)
- [ ] Manual verification:
  - [ ] Bedrock provider works as before
  - [ ] All drift types still functional
  - [ ] Error handling unchanged
- [ ] Linters passing

## Changes

### Added
- `drift/providers/__init__.py` - Provider package
- `drift/providers/base.py` - BaseProvider abstract class
- `drift/providers/bedrock.py` - BedrockProvider implementation
- `tests/unit/test_providers.py` - Provider tests

### Modified
- `drift/core/detector.py:34-89` - Use provider abstraction
- `drift/config.py:45-52` - Load provider from config
- `tests/unit/test_detector.py` - Update mocks for new structure

### Removed
- Hard-coded boto3 client initialization in detector.py

## Related Issues

Enables #42 - OpenAI provider support
Improves #23 - Better testability

---

```

**Why this is excellent:**
- ✅ Explains refactoring motivation
- ✅ Shows no behavior change (all tests pass)
- ✅ Documents benefits clearly
- ✅ Links to future work enabled

---

## Example 4: Small Fix

Even small PRs should have proper structure:

```markdown
## Summary

- Fixed typo in error message: "converstion" → "conversation"
- Updated help text for clarity

## Test Plan

- [ ] Verified error message displays correctly
- [ ] All tests still pass
- [ ] No functional changes

## Changes

### Modified
- `drift/parser.py:67` - Fixed typo in error message
- `drift/cli.py:23` - Clarified help text for --config argument

## Related Issues

N/A

---

```

**Why this is good:**
- ✅ Even small changes have context
- ✅ Shows what changed and where
- ✅ Confirms testing

---

## Example 5: Documentation Update

```markdown
## Summary

- Added "Custom Drift Types" section to README
- Documented .drift.yaml schema for custom types
- Included complete example configuration
- Addressed common user questions from issues

## Test Plan

- [ ] Reviewed by 2 team members
- [ ] All links work
- [ ] Code examples are valid
- [ ] Screenshots are clear

## Changes

### Modified
- `README.md:123-187` - Added "Custom Drift Types" section
- `README.md:34-42` - Added link to new section
- `.drift.yaml.example` - Added example custom drift type

### Added
- `docs/custom-drift-types.md` - Detailed guide

## Related Issues

Addresses questions in #34, #56, #78

---

```

---

## Common Patterns in Good PRs

### 1. Context is Clear

Every PR answers:
- **What:** What changed?
- **Why:** Why was this needed?
- **How:** How does it work?
- **Impact:** What else might be affected?

### 2. Testing is Thorough

- Specific test files and scenarios listed
- Coverage percentage stated
- Manual testing documented
- Edge cases covered

### 3. Changes are Organized

- Grouped by Added/Modified/Removed
- File paths with line numbers
- Brief description of each change
- No surprises for reviewer

### 4. Trade-offs are Explained

Good PRs explain decisions:
- "Chose X over Y because Z"
- "Trade-off: slightly more complexity for better testability"
- "Alternative considered: A, but rejected because B"

### 5. Size is Manageable

- Focused on one thing
- Can be reviewed in reasonable time
- If large, broken into logical sections
- Related changes grouped in commits

---

## PR Review Readiness Checklist

A good PR is ready when:

- [ ] Title follows format: `Issue #N: Description`
- [ ] Summary explains what, why, and how
- [ ] Test plan is specific and complete
- [ ] All tests passing locally
- [ ] All linters passing locally
- [ ] Changes section shows what changed
- [ ] Related issues linked
- [ ] Branch is up to date with main
- [ ] Commits are clean and logical
- [ ] No debug code or commented blocks
- [ ] Documentation updated if needed

---

## Tips for Writing Great PRs

1. **Write for your reviewer**
   - They don't have context
   - Help them understand quickly
   - Make review easy and fast

2. **Show your work**
   - Include test results
   - Show coverage numbers
   - List what you tested

3. **Explain decisions**
   - Why this approach?
   - What else did you consider?
   - What are the trade-offs?

4. **Keep it focused**
   - One feature/fix per PR
   - Separate refactoring from features
   - Split large changes if possible

5. **Make it reviewable**
   - Logical commits
   - Clear change descriptions
   - Easy to verify correctness
