import re

# Read the actual file content
with open('.claude/skills/doc-audit/SKILL.md', 'r') as f:
    content = f.read()

# Find all code block markers
pattern = r"^```"
matches = list(re.finditer(pattern, content, flags=re.MULTILINE))
print(f"Found {len(matches)} code block markers (opening or closing)")
print()

# Show each marker with context
for i, match in enumerate(matches, 1):
    start = match.start()
    # Get line number
    line_num = content[:start].count('\n') + 1
    # Get the line content
    line_start = content.rfind('\n', 0, start) + 1
    line_end = content.find('\n', start)
    if line_end == -1:
        line_end = len(content)
    line_content = content[line_start:line_end]
    print(f"Marker {i} at line {line_num}: {repr(line_content)}")

print()
print("If markers come in pairs, they should alternate opening/closing.")
print("Opening markers have language spec (```python, ```markdown)")
print("Closing markers are just ```")
