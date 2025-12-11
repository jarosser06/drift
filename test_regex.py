import re

# Read the actual file content
with open('.claude/skills/doc-audit/SKILL.md', 'r') as f:
    content = f.read()

# Apply the same regex that _remove_code_blocks uses
original_length = len(content)
pattern = r"^```.*?^```\s*$"
cleaned = re.sub(pattern, "", content, flags=re.MULTILINE | re.DOTALL)
cleaned_length = len(cleaned)

print(f"Original length: {original_length}")
print(f"Cleaned length: {cleaned_length}")
print(f"Removed {original_length - cleaned_length} characters")
print()

# Check if the problematic reference is still there
if 'docs/overview.rst' in cleaned:
    print("ERROR: 'docs/overview.rst' is still in the cleaned content!")
    # Find where it is
    lines = cleaned.split('\n')
    for i, line in enumerate(lines, 1):
        if 'docs/overview.rst' in line:
            print(f"Found on line {i}: {line}")
else:
    print("SUCCESS: 'docs/overview.rst' was removed from the content")
