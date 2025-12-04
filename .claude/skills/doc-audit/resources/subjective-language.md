# Subjective Language Detection Guide

Documentation should be objective, factual, and demonstrative - not marketing material.

## Subjective Adverbs to Flag

### Common Offenders

**Ease/Simplicity Claims:**
- easily
- simply
- just
- quickly
- effortlessly
- seamlessly
- straightforward
- trivially

**Obviousness Claims:**
- obviously
- clearly
- of course
- naturally
- evidently

**Speed/Efficiency Claims:**
- rapidly
- instantly
- immediately
- fast

### Examples

❌ **Bad**: "You can easily configure Drift using the .drift.yaml file"
✅ **Good**: "Configure Drift using the .drift.yaml file"

❌ **Bad**: "Simply run `drift` to analyze conversations"
✅ **Good**: "Run `drift` to analyze conversations"

❌ **Bad**: "Drift quickly identifies validation issues"
✅ **Good**: "Drift identifies validation issues"

## Subjective Adjectives to Flag

### Quality Claims

**Strength/Power:**
- powerful
- robust
- strong
- advanced

**Beauty/Elegance:**
- elegant
- beautiful
- clean
- polished

**Value Judgments:**
- great
- excellent
- amazing
- fantastic
- wonderful
- awesome

**Comprehensiveness:**
- comprehensive
- complete
- full-featured
- rich

### Examples

❌ **Bad**: "Drift provides a powerful validation engine"
✅ **Good**: "Drift provides a validation engine"

❌ **Bad**: "The elegant API makes analysis straightforward"
✅ **Good**: "The API enables conversation analysis"

❌ **Bad**: "Drift offers comprehensive validation rules"
✅ **Good**: "Drift offers validation rules for conversation analysis and project structure"

## Marketing Language Patterns

### Superlatives Without Data

❌ **Bad**: "Drift is the best tool for AI conversation analysis"
✅ **Good**: "Drift analyzes AI conversations for quality issues"

❌ **Bad**: "The most advanced validation system"
✅ **Good**: "Validates conversations using LLM analysis and programmatic checks"

### Emotional Appeals

❌ **Bad**: "You'll love how Drift improves your workflow"
✅ **Good**: "Drift identifies gaps between AI agent actions and user intentions"

❌ **Bad**: "Experience the power of automated quality assurance"
✅ **Good**: "Automate quality assurance for AI-augmented codebases"

### Vague Benefit Claims

❌ **Bad**: "Drift makes your AI projects better"
✅ **Good**: "Drift validates AI agent behavior against best practices"

❌ **Bad**: "Improve code quality with minimal effort"
✅ **Good**: "Validate code quality with programmatic and LLM-based rules"

## Objective Alternatives

### Replace Subjective with Specific

| Subjective | Objective Alternative |
|------------|----------------------|
| "easily configure" | "configure" |
| "powerful features" | "features include:" + list |
| "comprehensive analysis" | "analyzes X, Y, and Z" |
| "quickly identifies" | "identifies" |
| "elegant solution" | "solution using X pattern" |
| "robust validation" | "validation with N rules" |
| "advanced capabilities" | "capabilities include:" + list |

### Show, Don't Tell

❌ **Bad**: "Drift's powerful validation engine catches errors easily"
✅ **Good**: "Drift validates conversations using 15+ rules including task completion, error handling, and code quality"

❌ **Bad**: "The comprehensive CLI provides everything you need"
✅ **Good**: "The CLI supports multiple output formats, time-based filtering, and programmatic validation"

## Factual Language Guidelines

### Use Concrete Descriptions

✅ **Good patterns:**
- "Drift validates conversations using LLM analysis"
- "Supports Anthropic API and AWS Bedrock"
- "Includes 15 conversation analysis rules"
- "Outputs results in Markdown or JSON format"
- "Analyzes conversations from the last N days"

### Demonstrate Capabilities

Instead of praising features, show what they do:

❌ **Bad**: "Drift's amazing rule system is highly configurable"
✅ **Good**: "Configure rules in .drift.yaml with custom parameters and thresholds"

❌ **Bad**: "The powerful provider abstraction supports multiple LLMs"
✅ **Good**: "Provider interface supports Anthropic API and AWS Bedrock"

### Quantify When Possible

✅ **Examples:**
- "15 conversation analysis rules"
- "90%+ test coverage requirement"
- "Supports Python 3.10+"
- "Caches LLM responses for 24 hours"

## Context-Appropriate Language

### When Technical Terms Are Okay

Some words that might seem subjective are acceptable in technical contexts:

✅ **Acceptable:**
- "comprehensive test suite" (if you list what's tested)
- "robust error handling" (if you describe what errors are caught)
- "efficient caching" (if you specify cache duration/mechanism)

But only if immediately followed by specifics.

### When Comparisons Are Okay

Comparisons are acceptable when:
- Backed by data/metrics
- Comparing to specific alternatives
- Stating objective differences

✅ **Good**: "Drift analyzes conversations without requiring manual code review"
✅ **Good**: "Unlike manual validation, Drift checks all N rules consistently"

❌ **Bad**: "Drift is better than other tools"
❌ **Bad**: "More powerful than traditional linters"

## Audit Process

1. **Search for flagged words**: Use regex to find all subjective terms
2. **Evaluate context**: Some uses may be factual (e.g., "Python is a powerful language" in comparison context)
3. **Suggest replacements**: Provide specific, objective alternatives
4. **Verify claims**: Ensure replacement text is factually accurate

## Severity Levels

**Critical**: Marketing claims without factual basis
- "Best tool for..."
- "Revolutionary approach..."

**High**: Subjective quality judgments
- "powerful", "elegant", "amazing"

**Medium**: Ease/simplicity claims
- "easily", "simply", "just"

**Low**: Minor subjective modifiers
- "nice", "good", "great" (when not used as superlatives)

## Examples from Drift Context

### Configuration Documentation

❌ **Bad**: "Drift's elegant YAML configuration makes setup a breeze"
✅ **Good**: "Configure Drift using .drift.yaml with provider settings and validation rules"

### CLI Documentation

❌ **Bad**: "The powerful CLI easily handles complex analysis tasks"
✅ **Good**: "The CLI analyzes conversations with options for time range, output format, and validation mode"

### Validation Rules

❌ **Bad**: "Drift's comprehensive validation engine catches all quality issues"
✅ **Good**: "Drift validates conversations using conversation analysis rules (task completion, error handling) and project validation rules (documentation, dependencies)"

### Provider Documentation

❌ **Bad**: "Seamlessly switch between Anthropic and Bedrock providers"
✅ **Good**: "Switch between Anthropic API and AWS Bedrock by updating provider configuration in .drift.yaml"
