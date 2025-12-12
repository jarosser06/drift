---
name: python-docstrings
description: Docstring format and content requirements using Google-style with custom parameter separator
path: "**/*.py"
---

# Python Docstring Standards

## Docstring Format

**MUST**: Use Google-style docstrings.

**MUST**: Use custom parameter separator: `-- param1: Description`

**MUST**: Document all public modules, classes, and functions.

## Docstring Content Requirements

**MUST**: Be concise and factual.

**MUST**: Use present tense.

**MUST**: Document parameters and return values.

## Prohibited Docstring Content

**MUST NOT**: Use subjective language such as:
- easily, simply, just
- obviously, clearly
- powerful, elegant, beautiful
- amazing, best, better, great, excellent
- effortlessly, seamlessly, straightforward

**MUST NOT**: Include TODOs in docstrings.

**MUST NOT**: Include implementation details (focus on WHAT, not HOW).

**MUST NOT**: Use future tense.
