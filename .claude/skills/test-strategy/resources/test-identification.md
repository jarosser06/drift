# Test Identification Guide

Step-by-step process for identifying what tests need to be written.

## From User Story to Test Cases

### Step 1: Extract Requirements

Read the user story and extract all explicit and implicit requirements.

**Example: Block Line Count Validator**

User story: "Create a validator that checks if code blocks in markdown files exceed a maximum line count"

**Explicit requirements:**
- R1: Find code blocks in markdown files
- R2: Count lines in each code block
- R3: Compare against max_count parameter
- R4: Fail if any block exceeds max_count

**Implicit requirements:**
- R5: Handle files without code blocks
- R6: Handle empty code blocks
- R7: Handle multiple code blocks in one file
- R8: Handle missing or invalid parameters
- R9: Follow Drift validator contract (return None for pass, DocumentRule for fail)

### Step 2: Identify All Behaviors

For each requirement, list the specific behaviors that need testing.

**From requirements above:**

**R1 (Find code blocks):**
- Behavior 1: Identify code blocks with triple backticks
- Behavior 2: Handle files with no code blocks
- Behavior 3: Handle multiple code blocks

**R2 (Count lines):**
- Behavior 4: Count only content lines, not fence markers
- Behavior 5: Handle empty code blocks (0 lines)
- Behavior 6: Count blank lines within blocks correctly

**R3 (Compare against max):**
- Behavior 7: Compare block line count to max_count
- Behavior 8: Handle max_count boundary (equals case)

**R4 (Fail if exceeds):**
- Behavior 9: Return None when all blocks under limit
- Behavior 10: Return DocumentRule when any block over limit
- Behavior 11: Report which block and file exceeded limit

**R5-R9 (Edge cases):**
- Behavior 12: Pass when file has no code blocks
- Behavior 13: Handle missing max_count parameter
- Behavior 14: Handle invalid max_count (negative, zero)
- Behavior 15: Work with DocumentBundle structure

### Step 3: Categorize by Test Type

Decide which behaviors need unit tests vs integration tests.

**Unit Tests (test validator logic in isolation):**
- All behaviors 1-14 above
- Focus on validator logic, not file system or bundle creation

**Integration Tests (test with real DocumentBundle):**
- Behavior 15: End-to-end with DocumentBundle
- Multiple files scenario
- Real markdown parsing

**E2E Tests (test in complete workflow):**
- Not needed for individual validators
- Covered by analyzer integration tests

### Step 4: Map to Test Methods

Convert each behavior to a test method name.

```python
class TestBlockLineCountValidator:
    """Tests for BlockLineCountValidator."""

    # R1 - Finding code blocks
    def test_identifies_code_blocks_with_triple_backticks()
    def test_passes_when_no_code_blocks()
    def test_handles_multiple_code_blocks()

    # R2 - Counting lines
    def test_counts_only_block_content_not_fences()
    def test_handles_empty_code_block()
    def test_counts_blank_lines_within_block()

    # R3, R4 - Comparison and failure
    def test_passes_when_block_under_max()
    def test_passes_when_block_equals_max()  # Boundary!
    def test_fails_when_block_exceeds_max()
    def test_fails_with_correct_error_message()
    def test_reports_file_and_block_location()

    # R5-R9 - Edge cases
    def test_handles_missing_max_count_param()
    def test_handles_zero_max_count()
    def test_handles_negative_max_count()
```

### Step 5: Prioritize Tests

Order tests by risk and importance:

**Priority 1 (Must have - core functionality):**
- test_passes_when_block_under_max
- test_fails_when_block_exceeds_max
- test_passes_when_block_equals_max (boundary)

**Priority 2 (Important - common cases):**
- test_handles_multiple_code_blocks
- test_passes_when_no_code_blocks
- test_reports_file_and_block_location

**Priority 3 (Edge cases):**
- test_handles_empty_code_block
- test_handles_missing_max_count_param
- test_counts_blank_lines_within_block

---

## From Code to Test Cases

### New Code

When writing tests for new code:

1. **Read the implementation** - Understand what it does
2. **Identify branches** - Every if/else needs both paths tested
3. **Find loops** - Test empty, single, multiple iterations
4. **Spot error handling** - Test each exception path
5. **Look for parameters** - Test valid, invalid, boundary values

**Example:**

```python
def validate_line_count(content, max_count):
    if max_count <= 0:
        raise ValueError("max_count must be positive")

    blocks = extract_code_blocks(content)
    if not blocks:
        return None  # No blocks = pass

    for block in blocks:
        if len(block.lines) > max_count:
            return create_failure(block)

    return None
```

**Tests needed:**
```python
def test_raises_error_when_max_count_zero()       # if max_count <= 0
def test_raises_error_when_max_count_negative()   # if max_count <= 0
def test_passes_when_no_blocks()                  # if not blocks
def test_fails_when_any_block_exceeds()           # if len > max_count
def test_passes_when_all_blocks_under_limit()     # loop completes
def test_handles_empty_blocks_list()              # blocks = []
```

### Code Changes

When testing modifications to existing code:

1. **Understand what changed** - Read the diff
2. **Identify affected behaviors** - What behaviors are modified?
3. **Check existing tests** - Do they still cover the change?
4. **Add new tests** - For new behaviors introduced
5. **Update existing tests** - If behavior contracts changed

**Example change:** Add support for inline code (single backticks)

**New tests needed:**
```python
def test_ignores_inline_code()                    # NEW behavior
def test_handles_mix_of_inline_and_block_code()  # NEW behavior
```

**Existing tests to verify:**
- Ensure existing tests still pass
- Verify they don't need updates

### Bug Fixes

When fixing a bug, always add a regression test:

1. **Write failing test** - Reproduces the bug
2. **Fix the bug** - Make the test pass
3. **Verify fix** - Run all tests

**Example bug:** Validator crashes on files with unclosed code blocks

**Regression test:**
```python
def test_handles_unclosed_code_block():
    """Test that unclosed code blocks don't crash validator.

    Regression test for bug #123.
    """
    content = "```python\ncode without closing fence"
    # Should not crash, should handle gracefully
    result = validate(content, max_count=10)
    assert result is not None  # Should fail validation
    assert "unclosed" in result.message.lower()
```

---

## Test Type Decision Matrix

### Unit Test When:

**Testing:**
- Single function/method
- Validator logic
- Data model validation
- Utility functions
- Parser logic
- Format functions

**Characteristics:**
- Fast (< 100ms each)
- Isolated (no external dependencies)
- Mocked (file system, APIs, etc.)
- Focused (one behavior per test)

**Drift Examples:**
- `test_yaml_frontmatter_validator.py` - Validator logic
- `test_circular_dependencies_validator.py` - Graph algorithm
- `test_block_line_count_validator.py` - Line counting logic

### Integration Test When:

**Testing:**
- Component interaction
- Validator with DocumentBundle
- Config loading from files
- Multi-phase workflows
- File system operations

**Characteristics:**
- Slower (< 1s each)
- Uses real components together
- May use tmp_path for files
- Tests workflows, not individual functions

**Drift Examples:**
- `test_analyzer_multi_phase.py` - Full analysis workflow
- `test_plugin_system.py` - Custom validator loading
- `test_multi_file_statistics.py` - Statistics across files

### E2E Test When:

**Testing:**
- Complete user workflows
- Full CLI commands
- Real configuration files
- End-to-end scenarios

**Characteristics:**
- Slowest (< 5s each)
- Uses real everything
- Minimal mocking
- Tests user-visible behavior

**Drift Examples:**
- CLI integration tests
- Full `drift --no-llm` workflow
- Complete analysis pipeline

### Decision Flow:

```
Is it a single function/method?
├─ YES → Unit Test
└─ NO
   │
   Is it multiple components working together?
   ├─ YES → Integration Test
   └─ NO
      │
      Is it a complete user workflow?
      ├─ YES → E2E Test
      └─ NO → Start with Unit Test, add Integration if needed
```

---

## Practical Examples

### Example 1: Circular Dependency Validator

**User Story:** "Detect circular dependencies in skill definitions"

**Requirements:**
- R1: Parse skill dependencies from frontmatter
- R2: Build dependency graph
- R3: Detect cycles in graph
- R4: Report which skills form the cycle

**Test Plan:**

```python
class TestCircularDependenciesValidator:
    # R1 - Parsing
    def test_parses_dependencies_from_frontmatter()
    def test_handles_no_dependencies()
    def test_handles_invalid_frontmatter()

    # R2 - Graph building
    def test_builds_graph_with_single_dependency()
    def test_builds_graph_with_multiple_dependencies()

    # R3 - Cycle detection
    def test_passes_when_no_cycles()
    def test_detects_self_loop()           # A → A
    def test_detects_two_node_cycle()      # A → B → A
    def test_detects_multi_node_cycle()    # A → B → C → A

    # R4 - Reporting
    def test_reports_skills_in_cycle()
    def test_reports_file_locations()
```

**Prioritization:**
1. Core: test_detects_two_node_cycle (most common)
2. Important: test_passes_when_no_cycles (happy path)
3. Edge: test_detects_self_loop, test_detects_multi_node_cycle

### Example 2: YAML Schema Validator

**User Story:** "Validate YAML frontmatter against JSON schema"

**Requirements:**
- R1: Extract YAML frontmatter
- R2: Parse JSON schema from rule
- R3: Validate YAML against schema
- R4: Report validation errors clearly

**Test Plan:**

```python
class TestYAMLSchemaValidator:
    # R1 - Extraction
    def test_extracts_yaml_frontmatter()
    def test_handles_no_frontmatter()
    def test_handles_malformed_yaml()

    # R2 - Schema parsing
    def test_parses_json_schema_from_rule()
    def test_handles_missing_schema_param()
    def test_handles_invalid_json_schema()

    # R3 - Validation
    def test_passes_when_yaml_matches_schema()
    def test_fails_when_required_field_missing()
    def test_fails_when_field_wrong_type()
    def test_fails_when_field_invalid_value()

    # R4 - Error reporting
    def test_reports_which_field_failed()
    def test_reports_expected_vs_actual()
    def test_includes_file_location()
```

---

## Checklist

Use this checklist when planning tests for a new feature:

- [ ] Read and understand the user story/issue
- [ ] Extract all explicit requirements
- [ ] Identify implicit requirements (error handling, edge cases)
- [ ] List all behaviors for each requirement
- [ ] Categorize behaviors by test type (unit/integration/e2e)
- [ ] Map each behavior to a test method name
- [ ] Prioritize tests by risk/importance
- [ ] Identify edge cases using equivalence partitioning
- [ ] Identify boundary conditions to test
- [ ] Plan fixture requirements
- [ ] Review similar tests in codebase for patterns
- [ ] Verify 90%+ coverage will be achieved

---

## Common Patterns

### Pattern 1: Validator Testing

Every validator needs:
```python
def test_validation_type_property()        # Verify validation_type
def test_passes_when_valid()               # Happy path
def test_fails_when_invalid()              # Failure path
def test_fails_with_clear_message()        # Error message quality
def test_handles_missing_parameters()      # Config edge case
def test_handles_file_not_found()          # File edge case
```

### Pattern 2: Parser Testing

Every parser needs:
```python
def test_parses_valid_input()              # Happy path
def test_raises_error_on_invalid_syntax()  # Syntax error
def test_raises_error_on_invalid_schema()  # Schema error
def test_handles_empty_input()             # Empty edge case
def test_handles_malformed_input()         # Malformed edge case
```

### Pattern 3: CLI Testing

Every CLI command needs:
```python
def test_successful_execution()            # Happy path
def test_handles_missing_file()            # File error
def test_handles_invalid_arguments()       # Arg error
def test_output_format_correct()           # Output verification
def test_exit_code_correct()               # Exit code verification
```
