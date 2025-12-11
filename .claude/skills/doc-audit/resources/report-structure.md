# Documentation Audit Report Structure

Template and guidelines for creating documentation audit reports.

## Report Template

```markdown
# Documentation Audit Report
Date: YYYY-MM-DD
Auditor: [Name]

## Executive Summary
- Files audited: X
- Code examples validated: Y
- Issues found: Z
- Critical issues: N

## Code Example Issues

### File: docs/quickstart.rst

#### Issue 1: Incorrect Import Path (Line 26)
**Severity**: Critical
**Current**:
```python
from drift.core.analyzer import Analyzer
```
**Issue**: Module not found at this path
**Verification**: Used serena find_symbol, module is actually at drift.analyzer
**Suggested Fix**:
```python
from drift.analyzer import Analyzer
```

#### Issue 2: Missing Parameter (Line 84)
**Severity**: High
**Current**:
```python
analyzer.analyze()
```
**Issue**: Method requires config_path parameter
**Verification**: Checked Analyzer class with serena, analyze() needs config_path
**Suggested Fix**:
```python
analyzer.analyze(config_path=".drift.yaml")
```

## Subjective Language Issues

### File: docs/overview.rst

#### Issue 1: Subjective Adverb (Line 45)
**Severity**: Medium
**Current**: "You can easily analyze AI conversations..."
**Suggested**: "You can analyze AI conversations..."
**Reason**: "Easily" is subjective and adds no technical value

#### Issue 2: Marketing Language (Line 102)
**Severity**: Medium
**Current**: "Drift provides a powerful validation system..."
**Suggested**: "Drift provides a validation system with X features..."
**Reason**: "Powerful" is subjective; state specific capabilities

#### Issue 3: False User Claim (Line 145)
**Severity**: Critical
**Current**: "Most users run drift --no-llm in CI/CD"
**Suggested**: "drift --no-llm runs without API calls, suitable for CI/CD"
**Reason**: No data to support "most users" claim

## Recommendations

1. Update all import examples to match actual package structure
2. Remove subjective language (easily, simply, powerful)
3. Add missing parameters to method examples
4. Verify CLI examples against current version
5. Replace user behavior claims with factual statements
```

## Issue Severity Guidelines

**Critical:**
- Incorrect code that won't work
- False API documentation
- Security issues in examples

**High:**
- Missing required parameters
- Deprecated API usage
- Incomplete examples that mislead

**Medium:**
- Subjective language
- Marketing claims
- Minor inconsistencies

**Low:**
- Stylistic improvements
- Optional enhancements
