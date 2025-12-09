---
description: Comprehensive code review
argument-hint: "[files...]"
skills:
  - python-basics
  - code-review
  - test-strategy
---

Perform a thorough code review of current changes or specified files.

**Review Areas:**

1. **Code Quality**
   - Clean, readable code
   - Proper naming conventions
   - No code duplication
   - Appropriate error handling

2. **Architecture**
   - Proper separation of concerns
   - Good abstraction levels
   - Follows project patterns
   - Scalable design

3. **Testing**
   - Comprehensive test coverage (90%+)
   - Edge cases covered
   - Tests are clear and maintainable
   - Proper mocking where needed

4. **Documentation**
   - Clear docstrings (PEP 257)
   - Inline comments where needed
   - README updates if applicable
   - API documentation complete

5. **Security**
   - No credentials in code
   - Proper input validation
   - Safe API usage
   - No injection vulnerabilities

6. **Performance**
   - Efficient algorithms
   - No obvious bottlenecks
   - Proper resource management

**Execution Steps:**

1. **Activate the code-review skill** - Essential for conducting thorough reviews
2. **Determine scope**:
   - For recent changes: Use `git diff main...HEAD` to see changed files
   - For specific files: Review files specified by the user
   - If no scope given: Ask user which files/areas to review
3. **Analyze files systematically**:
   - Read each file using the Read tool
   - Apply review criteria from the 6 areas above
   - Look for patterns across files
   - Note both issues and positive aspects
4. **Present findings** in structured format:
   - Group by category (Code Quality, Architecture, Testing, etc.)
   - List specific issues with file paths and line numbers
   - Provide actionable recommendations
   - Highlight critical vs. minor issues
5. **Summarize**:
   - Overall assessment
   - Priority fixes
   - Optional improvements

**Usage:**
```
/code-review
```

Provides detailed feedback on code quality and suggests improvements.
