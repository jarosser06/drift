---
description: Pre-commit code review workflow for staged git changes, analyzing logic bugs, security vulnerabilities, and style issues with categorized severity feedback
---

1. If arguments provided, review specific files/diffs:
   ```bash
   # Reviewing specific items passed as arguments
   echo "Reviewing: $ARGUMENTS"
   ```

2. Otherwise, review current git changes:
   ```bash
   git diff --name-only
   git diff
   ```

3. Analyze the code quality, looking for:
   - Logic bugs and edge cases
   - Performance issues
   - Security vulnerabilities
   - Code style consistency (naming, patterns)
   - Typos and documentation gaps

4. Provide constructive feedback categorized by severity (Critical, Major, Minor).
