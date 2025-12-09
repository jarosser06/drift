# Edge Case Techniques

Comprehensive techniques for identifying and testing edge cases.

## What is an Edge Case?

**Definition:** An edge case is a scenario that occurs at an extreme (edge) of operating parameters.

**Examples:**
- Empty input: `[]`, `""`, `{}`
- Boundary values: `0`, `MAX_VALUE`, `-1`
- Special characters: `\n`, `\t`, `None`
- Unusual combinations: empty string in required field

**Why they matter:**
- Bugs cluster at boundaries
- Edge cases often overlooked in normal testing
- Can cause crashes, security issues, or incorrect behavior
- Often discovered in production if not tested

---

## Equivalence Partitioning

### Concept

**Divide input domain into equivalence classes** - groups of inputs that should behave the same way.

**Test strategy:** Test one representative from each class + all boundaries between classes.

### How to Apply

**Step 1: Identify input domain**

Example: Block line count validator
- Input: Number of lines in a code block
- Range: 0 to infinity

**Step 2: Divide into equivalence classes**

Given max_count = 100:

**Class 1:** No code blocks (special case)
- Representative: File with no code blocks

**Class 2:** Valid blocks (0 < lines <= max_count)
- Representative: Block with 50 lines

**Class 3:** Invalid blocks (lines > max_count)
- Representative: Block with 150 lines

**Step 3: Select representatives**

```python
# Class 1
def test_passes_when_no_code_blocks():
    content = "# Just markdown, no code"
    bundle = create_bundle(content)
    result = validator.validate(rule, bundle)
    assert result is None

# Class 2
def test_passes_when_block_in_valid_range():
    content = "```python\n" + "\n".join(["line"] * 50) + "\n```"
    bundle = create_bundle(content)
    result = validator.validate(rule, bundle)
    assert result is None

# Class 3
def test_fails_when_block_exceeds_max():
    content = "```python\n" + "\n".join(["line"] * 150) + "\n```"
    bundle = create_bundle(content)
    result = validator.validate(rule, bundle)
    assert result is not None
```

### Drift Example: Token Count Validator

**Input domain:** Token count (integer)

**Given rule:** min_count=500, max_count=1500

**Equivalence classes:**

1. Below minimum: count < 500
2. Valid range: 500 <= count <= 1500
3. Above maximum: count > 1500

**Tests:**
```python
def test_fails_when_below_minimum():
    """Test with 300 tokens (Class 1 representative)."""
    content = "short text"  # ~300 tokens
    result = validator.validate(rule, bundle)
    assert result is not None
    assert "below minimum" in result.observed_issue

def test_passes_when_in_valid_range():
    """Test with 1000 tokens (Class 2 representative)."""
    content = generate_text(1000)  # Exactly 1000 tokens
    result = validator.validate(rule, bundle)
    assert result is None

def test_fails_when_above_maximum():
    """Test with 2000 tokens (Class 3 representative)."""
    content = generate_text(2000)  # Exactly 2000 tokens
    result = validator.validate(rule, bundle)
    assert result is not None
    assert "exceeds maximum" in result.observed_issue
```

### Multi-Dimensional Partitioning

**Example: File validation with multiple parameters**

**Parameters:**
- file_exists: True/False
- file_readable: True/False
- file_valid: True/False

**Equivalence classes:**
```
1. exists=False, readable=N/A, valid=N/A → File not found error
2. exists=True, readable=False, valid=N/A → Permission error
3. exists=True, readable=True, valid=False → Validation error
4. exists=True, readable=True, valid=True → Success
```

**Tests:**
```python
def test_fails_when_file_not_found():
    """Class 1: File doesn't exist."""
    result = validator.validate_file("missing.md")
    assert "not found" in result.error

def test_fails_when_file_unreadable(tmp_path):
    """Class 2: File exists but can't be read."""
    file = tmp_path / "unreadable.md"
    file.write_text("content")
    file.chmod(0o000)  # No permissions
    result = validator.validate_file(str(file))
    assert "permission" in result.error.lower()

def test_fails_when_file_invalid(tmp_path):
    """Class 3: File readable but invalid content."""
    file = tmp_path / "invalid.md"
    file.write_text("---\ninvalid: yaml: content\n---")
    result = validator.validate_file(str(file))
    assert "invalid" in result.error.lower()

def test_passes_when_file_valid(tmp_path):
    """Class 4: Everything valid."""
    file = tmp_path / "valid.md"
    file.write_text("---\ntitle: Test\n---\nContent")
    result = validator.validate_file(str(file))
    assert result.success
```

---

## Boundary Value Analysis

### The Boundary Bug Principle

**Research shows:** 70-80% of defects occur at boundaries!

**Why?**
- Off-by-one errors
- Incorrect comparison operators (`<` vs `<=`)
- Integer overflow
- Edge of valid ranges

### Standard Boundaries to Test

For any range [min, max]:

**Always test:**
- `min - 1` (just below)
- `min` (at lower boundary)
- `min + 1` (just above lower)
- `max - 1` (just below upper)
- `max` (at upper boundary)
- `max + 1` (just above)

**Additionally:**
- `0` (if applicable)
- `1` (smallest positive)
- `-1` (if negative values possible)
- Empty/null (if applicable)

### Drift-Specific Boundaries

#### File Operations

**Code block line count:**
```python
# If max_count = 100
def test_passes_with_99_lines():
    """Just below boundary."""
    content = create_code_block(99)
    assert validator.validate(rule, bundle) is None

def test_passes_with_100_lines():
    """At boundary - critical test!"""
    content = create_code_block(100)
    assert validator.validate(rule, bundle) is None

def test_fails_with_101_lines():
    """Just above boundary."""
    content = create_code_block(101)
    result = validator.validate(rule, bundle)
    assert result is not None
    assert "exceeds" in result.observed_issue
```

**Empty file boundary:**
```python
def test_handles_empty_file(tmp_path):
    """Boundary: 0 bytes."""
    file = tmp_path / "empty.md"
    file.write_text("")
    bundle = create_bundle_from_file(file)
    result = validator.validate(rule, bundle)
    # Should handle gracefully, not crash

def test_handles_single_line_file(tmp_path):
    """Boundary: 1 line."""
    file = tmp_path / "single.md"
    file.write_text("one line")
    bundle = create_bundle_from_file(file)
    result = validator.validate(rule, bundle)
    # Should process normally
```

#### Numeric Constraints

**Token count limits:**
```python
# If max_count = 1500
def test_passes_with_1499_tokens():
    """Just below maximum."""
    content = generate_text_with_tokens(1499)
    assert validator.validate(rule, bundle) is None

def test_passes_with_1500_tokens():
    """At maximum boundary."""
    content = generate_text_with_tokens(1500)
    assert validator.validate(rule, bundle) is None

def test_fails_with_1501_tokens():
    """Just above maximum."""
    content = generate_text_with_tokens(1501)
    result = validator.validate(rule, bundle)
    assert result is not None
```

**Zero boundary:**
```python
def test_handles_zero_tokens():
    """Boundary: empty content."""
    content = ""
    result = validator.validate(rule, bundle)
    # How should this be handled?

def test_handles_one_token():
    """Boundary: minimal content."""
    content = "word"
    result = validator.validate(rule, bundle)
    # Should process normally
```

#### String Lengths

**Validation message length:**
```python
def test_handles_empty_string():
    """Boundary: zero length."""
    result = validator.process("")
    assert result is not None

def test_handles_single_char():
    """Boundary: length 1."""
    result = validator.process("a")
    assert result is not None

def test_handles_very_long_string():
    """Boundary: max length."""
    content = "a" * 10000
    result = validator.process(content)
    # Should handle or reject gracefully
```

---

## Type-Specific Edge Cases

### Strings

**Edge cases:**
```python
# Empty
""

# Whitespace only
"   "
"   \t\n   "

# Special characters
"\n\n\n"
"\t\t\t"
"!@#$%^&*()"

# Unicode
"测试"
"🚀"

# Very long
"a" * 100000

# Quotes and escaping
"string with \"quotes\""
"string with 'quotes'"
"string with \\backslash"
```

**Drift example: Frontmatter parsing**
```python
def test_handles_empty_frontmatter():
    """Edge: Empty frontmatter block."""
    content = "---\n---\nContent"
    result = parse_frontmatter(content)
    assert result == {}

def test_handles_whitespace_only_frontmatter():
    """Edge: Only whitespace in frontmatter."""
    content = "---\n   \n---\nContent"
    result = parse_frontmatter(content)
    assert result == {}

def test_handles_unicode_in_frontmatter():
    """Edge: Unicode characters."""
    content = "---\ntitle: 测试\n---\nContent"
    result = parse_frontmatter(content)
    assert result["title"] == "测试"

def test_handles_special_chars_in_values():
    """Edge: Special YAML characters."""
    content = '---\ntitle: "Value: with colons"\n---'
    result = parse_frontmatter(content)
    assert result["title"] == "Value: with colons"
```

### Collections (Lists/Dicts)

**Lists edge cases:**
```python
# Empty
[]

# Single element
[x]

# Duplicates
[x, x, x]

# None values
[None, None]
[x, None, y]

# Mixed types (if applicable)
[1, "string", None]
```

**Drift example: Bundle files**
```python
def test_handles_empty_files_list():
    """Edge: No files in bundle."""
    bundle = DocumentBundle(
        bundle_id="test",
        bundle_type="skill",
        files=[],  # Empty!
        project_path="/test"
    )
    result = validator.validate(rule, bundle)
    # Should handle gracefully

def test_handles_single_file():
    """Edge: One file only."""
    bundle = create_bundle_with_files(1)
    result = validator.validate(rule, bundle)
    assert result is not None or result is None  # Valid case

def test_handles_duplicate_file_paths():
    """Edge: Same file path twice."""
    file = DocumentFile(relative_path="test.md", ...)
    bundle = DocumentBundle(files=[file, file])
    result = validator.validate(rule, bundle)
    # How should this be handled?
```

**Dictionaries edge cases:**
```python
# Empty
{}

# Missing required keys
{"key1": "value"}  # When key2 required

# Extra unexpected keys
{"key1": "v1", "unexpected": "v2"}

# None values
{"key": None}

# Nested empty
{"key": {}}
{"key": []}
```

**Drift example: Rule parameters**
```python
def test_handles_missing_required_param():
    """Edge: Required parameter not provided."""
    rule = ValidationRule()  # No max_count!
    result = validator.validate(rule, bundle)
    assert result is not None
    assert "missing" in result.observed_issue.lower()

def test_handles_none_parameter():
    """Edge: Parameter explicitly None."""
    rule = ValidationRule(max_count=None)
    result = validator.validate(rule, bundle)
    assert result is not None

def test_handles_extra_parameters():
    """Edge: Unexpected parameters provided."""
    rule = ValidationRule(
        max_count=100,
        unexpected_param="value"
    )
    # Should ignore extra params or raise error?
```

### Files

**File edge cases:**
```python
# Non-existent
Path("missing.txt")

# Empty file (0 bytes)
Path("empty.txt")  # file.stat().st_size == 0

# Unreadable (permissions)
Path("no_perms.txt")  # chmod 000

# Malformed content
Path("invalid.yaml")  # Contains: "key: [unclosed"

# Very large file
Path("huge.txt")  # 1GB+

# Binary file (when expecting text)
Path("image.png")

# Symlink (if relevant)
Path("link.txt")  # -> real_file.txt
```

**Drift example: File validation**
```python
def test_handles_file_not_found():
    """Edge: File doesn't exist."""
    rule = ValidationRule(file_path="missing.md")
    result = validator.validate(rule, bundle)
    assert result is not None
    assert "not found" in result.observed_issue

def test_handles_empty_file(tmp_path):
    """Edge: Zero-byte file."""
    file = tmp_path / "empty.md"
    file.write_text("")
    bundle = create_bundle_from_file(file)
    result = validator.validate(rule, bundle)
    # Should handle gracefully

def test_handles_unreadable_file(tmp_path):
    """Edge: File exists but can't be read."""
    file = tmp_path / "secret.md"
    file.write_text("content")
    file.chmod(0o000)
    # Simulate permission error
    result = validator.validate_file(str(file))
    assert "permission" in str(result).lower()

def test_handles_malformed_file(tmp_path):
    """Edge: File with invalid format."""
    file = tmp_path / "bad.yaml"
    file.write_text("---\nkey: [unclosed\n---")
    result = validator.validate_file(str(file))
    assert result is not None
```

### Numbers

**Numeric edge cases:**
```python
# Zero
0
0.0

# Negative
-1
-100

# Boundary
MAX_INT
MIN_INT

# Overflow
MAX_INT + 1

# Precision (floats)
0.1 + 0.2  # != 0.3

# Special values (if applicable)
float('inf')
float('-inf')
float('nan')
```

**Drift example: Count validation**
```python
def test_handles_zero_count():
    """Edge: Zero value."""
    rule = ValidationRule(max_count=0)
    result = validator.validate(rule, bundle)
    # Should this be valid or error?

def test_handles_negative_count():
    """Edge: Negative value."""
    rule = ValidationRule(max_count=-1)
    result = validator.validate(rule, bundle)
    assert result is not None
    assert "positive" in result.observed_issue

def test_handles_very_large_count():
    """Edge: Maximum integer."""
    rule = ValidationRule(max_count=sys.maxsize)
    result = validator.validate(rule, bundle)
    # Should handle without overflow
```

---

## Error Guessing Technique

### Based on Experience

**Common failure patterns in Python:**

1. **Import errors** - Missing optional dependencies
2. **File operations** - Permissions, missing files, corruption
3. **Parsing** - Malformed JSON/YAML, encoding issues
4. **Type errors** - None when object expected, wrong type
5. **Index errors** - Empty lists, out of bounds access
6. **Key errors** - Missing dictionary keys
7. **Encoding errors** - Unicode, special characters

### Based on Code Review

**When reviewing code, look for:**

**Pattern 1: File operations without error handling**
```python
# Risky code
content = Path(file_path).read_text()
```

**Edge cases to test:**
```python
def test_handles_file_not_found()
def test_handles_permission_error()
def test_handles_encoding_error()
```

**Pattern 2: Dictionary access without .get()**
```python
# Risky code
value = config["optional_key"]
```

**Edge cases to test:**
```python
def test_handles_missing_key()
def test_handles_none_value()
```

**Pattern 3: List access without bounds check**
```python
# Risky code
first_item = items[0]
```

**Edge cases to test:**
```python
def test_handles_empty_list()
def test_handles_single_item_list()
```

**Pattern 4: External API calls without error handling**
```python
# Risky code
response = api.call_llm(prompt)
```

**Edge cases to test:**
```python
def test_handles_api_timeout()
def test_handles_api_rate_limit()
def test_handles_invalid_response()
```

### Drift-Specific Error Patterns

#### Pattern 1: Package Availability

**Code pattern:**
```python
try:
    import optional_package
except ImportError:
    raise RuntimeError("optional_package required")
```

**Tests needed:**
```python
def test_raises_error_when_package_missing(monkeypatch):
    """Test handling of missing optional dependency."""
    monkeypatch.setitem(sys.modules, "optional_package", None)

    with pytest.raises(RuntimeError, match="optional_package required"):
        validator = MyValidator()
```

**Drift examples:**
```python
def test_anthropic_missing_package(monkeypatch)
def test_tiktoken_missing_package(monkeypatch)
def test_pyyaml_missing_package(monkeypatch)
```

#### Pattern 2: YAML/Frontmatter Parsing

**Common issues:**
```python
# Unclosed frontmatter
"---\ntitle: Test\n"

# Invalid YAML syntax
"---\nkey: [unclosed\n---"

# Empty frontmatter
"---\n---\n"

# Missing frontmatter
"No frontmatter here"
```

**Tests needed:**
```python
def test_handles_unclosed_frontmatter()
def test_handles_invalid_yaml_syntax()
def test_handles_empty_frontmatter()
def test_handles_missing_frontmatter()
```

#### Pattern 3: Validation Logic

**Common issues:**
```python
# Missing required parameters
rule = ValidationRule()  # No max_count!

# Invalid parameter types
rule = ValidationRule(max_count="not a number")

# all_bundles is None (when needed)
validator.validate(rule, bundle, all_bundles=None)
```

**Tests needed:**
```python
def test_fails_when_missing_required_param()
def test_fails_when_invalid_param_type()
def test_handles_none_all_bundles()
```

#### Pattern 4: Circular Dependencies

**Special edge case for graph algorithms:**
```python
# Self-loop
skill_a depends on skill_a

# Two-node cycle
skill_a depends on skill_b
skill_b depends on skill_a

# Multi-node cycle
skill_a → skill_b → skill_c → skill_d → skill_a
```

**Tests needed:**
```python
def test_detects_self_loop()
def test_detects_two_node_cycle()
def test_detects_multi_node_cycle()
def test_passes_with_no_cycles()
```

---

## Edge Case Checklist

For any new code, verify you've tested:

### Input Validation
- [ ] Empty/null/None inputs
- [ ] Zero values
- [ ] Negative values
- [ ] Boundary values (min, max)
- [ ] Just above/below boundaries
- [ ] Invalid types
- [ ] Missing required parameters

### Collections
- [ ] Empty collections ([], {}, "")
- [ ] Single-element collections
- [ ] Duplicate elements
- [ ] None values in collections
- [ ] Missing dictionary keys

### File Operations
- [ ] File doesn't exist
- [ ] File is empty
- [ ] File is unreadable (permissions)
- [ ] File has invalid content
- [ ] Very large files

### String Operations
- [ ] Empty string
- [ ] Whitespace-only string
- [ ] Special characters
- [ ] Unicode characters
- [ ] Very long strings

### Error Handling
- [ ] Missing optional dependencies
- [ ] API/network errors
- [ ] Parsing errors
- [ ] Type errors
- [ ] Permission errors

### Drift-Specific
- [ ] Empty bundle.files
- [ ] Missing frontmatter
- [ ] Invalid YAML
- [ ] Circular dependencies
- [ ] all_bundles is None

---

## Common Edge Case Smells

**Warning signs you've missed edge cases:**

1. **No tests for empty inputs**
   - Missing tests for [], {}, "", None

2. **No tests for None values**
   - Parameters, return values, collection elements

3. **No tests for file errors**
   - Missing file, permission denied, malformed

4. **No tests for import errors**
   - Missing optional dependencies

5. **Only happy path tested**
   - No failure scenarios, no error cases

6. **No boundary tests**
   - Missing min-1, min, min+1, max-1, max, max+1

7. **No tests for special values**
   - Zero, negative, empty string, etc.

**If you see these smells, add edge case tests!**
