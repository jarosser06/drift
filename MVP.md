# Drift MVP

## What It Is

A tool that analyzes AI agent conversation logs to identify gaps between what AI agents did and what users actually wanted. It outputs actionable punch lists for improving project documentation, workflow definitions, and context.

## How It Works

1. **Load conversations** from configured agent tools (initially Claude Code)
2. **Multi-pass analysis** - one conversation at a time, one drift learning type per pass
3. **Store intermediate results** in temp directory (auto-cleaned)
4. **Generate output** as markdown or JSON to stdout

## Analysis Flow

For each conversation file:
- Pass 1: Analyze for `incomplete_work` drift
- Pass 2: Analyze for `documentation_gap` drift
- Pass 3: Analyze for `wrong_assumption` drift
- Pass 4: Analyze for `workflow_issue` drift
- Pass 5: Analyze for `implicit_expectation` drift

Each pass receives:
- Single conversation content
- Single drift learning type definition
- Focused detection prompt for that type only

## Key Features

### Configuration
- **Global config** (`config.yaml`): Used when no project config exists
- **Project config** (`.drift.yaml`): Same exact schema as global, overrides global when present
- Both configs support all the same settings
- Global is only used when project config doesn't specify a setting

### Multi-Pass Analysis
Each conversation analyzed multiple times, one pass per drift learning type:
- One conversation + one drift learning type per LLM call
- Each pass uses focused prompt for specific learning type
- More accurate detection than single-pass all-type approach
- Intermediate results stored in temp directory

### Linter-Style Operation
Works like a linter:
- Run analysis command
- Prints results to stdout
- Supports multiple output formats (markdown, json)
- Temp files auto-cleaned after completion
- Exit codes indicate findings

### Configurable Drift Learning Types
Define each learning type with:
- **Name** - identifier (e.g., `incomplete_work`)
- **Description** - what this learning type means
- **Detection prompt** - explicit instructions for finding this pattern
- **Explicit signals** - phrases indicating this drift
- **Implicit signals** - behavioral patterns indicating this drift
- **Examples** - sample conversations showing this pattern
- **Model override** - optional model to use for this specific learning type

### Multi-Provider Support
- Modular provider architecture (currently AWS Bedrock)
- Model definitions include provider and all required parameters
- Per-learning-type model overrides
- Falls back to default model

### Multi-Agent Tool Support
Initially supports Claude Code, designed for extensibility:
- Modular conversation loaders per agent tool
- Agent tool-specific conversation file locations
- Unified conversation format for analysis
- Future: Cursor, Aider, Windsurf, etc.

### Learning Tracking
Captures per drift:
- Agent tool and conversation file where drift was detected
- What AI did vs what user wanted
- Learning type and frequency
- Turns involved and resolution status
- Whether user manually fixed it
- If still needs action going forward

## Drift Learning Types

Each learning type configured with full definition:

### incomplete_work
```yaml
incomplete_work:
  description: "AI stopped before completing the full scope of work"
  model: haiku  # Optional: override default model for this learning type
  detection_prompt: |
    Look for instances where the AI claimed to be done but the user
    had to ask for completion, finishing touches, or missing parts.
  explicit_signals:
    - "Finish"
    - "Complete"
    - "You didn't finish"
    - "What about"
  implicit_signals:
    - User lists missing items after AI says done
    - User asks for specific parts AI didn't do
  examples:
    - "User: implement auth | AI: [adds login only] | User: what about logout and session handling?"
```

### documentation_gap
```yaml
documentation_gap:
  description: "Missing or unclear documentation/guidance in project context"
  detection_prompt: |
    Identify when AI misunderstood requirements because documentation,
    skills, commands, or context files didn't explain something clearly.
  explicit_signals:
    - "The docs should have mentioned"
    - "This should be in the skill definition"
  implicit_signals:
    - User corrects same misunderstanding across multiple conversations
    - User manually updates docs/skills after correction
    - AI asks questions that docs should answer
  examples:
    - "AI uses wrong test framework | User: we use pytest, it's in the docs | Gap: docs didn't emphasize this clearly"
```

### wrong_assumption
```yaml
wrong_assumption:
  description: "AI made incorrect assumptions not stated by user"
  detection_prompt: |
    Find cases where AI assumed something (architecture, approach,
    requirements) that the user never stated or implied.
    These reveal what needs to be documented or configured.
  explicit_signals:
    - "I never said"
    - "Don't assume"
    - "Why did you think"
    - "Where did you get that idea"
  implicit_signals:
    - User corrects fundamental approach AI took
    - AI adds features/complexity user didn't want
    - AI uses pattern/library not mentioned
  examples:
    - "User: add error handling | AI: [implements retry logic with exponential backoff] | User: just log it, no retries"
    - "User: refactor this function | AI: [splits into 5 helper functions] | User: no, just extract the validation part"
```

### workflow_issue
```yaml
workflow_issue:
  description: "Problem with the process or approach AI took"
  detection_prompt: |
    Detect when AI followed wrong workflow, used wrong tools,
    or took inefficient approach to solve the task.
  explicit_signals:
    - "Why didn't you use"
    - "You should have"
    - "Wrong approach"
  implicit_signals:
    - User redirects to different tool/method
    - User asks why AI chose specific approach
  examples:
    - "User: debug the test failure | AI: [reads entire codebase] | User: just run the test and read the error"
```

### implicit_expectation
```yaml
implicit_expectation:
  description: "User expected behavior without explicitly stating it"
  detection_prompt: |
    Find expectations users had that they thought were obvious
    but weren't stated explicitly in their request.
  explicit_signals:
    - "Obviously"
    - "Of course"
    - "That should be clear"
  implicit_signals:
    - User surprised AI didn't do something
    - User states "this goes without saying"
  examples:
    - "User: update the API | AI: [changes function signature] | User: obviously maintain backwards compatibility"
```

## Output Formats

### Markdown (default)
```markdown
# Drift Analysis Results

## Summary
- Total conversations: 5
- Total learnings: 12
- By type: incomplete_work (3), documentation_gap (5), wrong_assumption (4)
- By agent tool: claude-code (12)

## Learnings

### Session: abc123 (drift project)
**Agent Tool:** claude-code
**File:** agent-f7091296.jsonl

#### [Turn 5] wrong_assumption
**What AI did:** Implemented retry logic with exponential backoff
**What user wanted:** Just log the error, no retries
**Frequency:** one-time
**Resolved:** No - still needs documentation about error handling preferences

#### [Turn 8] incomplete_work
**What AI did:** Created configuration structure but didn't implement multi-pass
**What user wanted:** Full multi-pass implementation
**Frequency:** one-time
**Resolved:** No - still needs implementation
```

### JSON (--format json)
```json
{
  "metadata": {
    "generated_at": "timestamp",
    "total_conversations": 5,
    "total_learnings": 12
  },
  "results": [{
    "session_id": "abc123",
    "agent_tool": "claude-code",
    "conversation_file": "agent-f7091296.jsonl",
    "project_path": "/Users/jim/Projects/drift",
    "learnings": [{
      "turn_number": 5,
      "turn_uuid": "xyz789",
      "agent_tool": "claude-code",
      "conversation_file": "agent-f7091296.jsonl",
      "ai_action": "what AI did",
      "user_intent": "what user wanted",
      "learning_type": "wrong_assumption",
      "frequency": "repeated",
      "workflow_element": "skill",
      "turns_to_resolve": 3,
      "turns_involved": [5, 6, 7],
      "resolved_in_conversation": false,
      "still_needs_action": true
    }]
  }]
}
```

## Benefits

### For Tool Developers
- Identify documentation gaps users encounter in practice
- See which workflow elements cause confusion
- Track which issues get resolved vs remain unaddressed
- Prioritize improvements based on frequency and impact

### For Power Users
- Understand friction points in their AI workflows
- Identify missing context that causes repeated corrections
- Track what manual fixes they're making
- Generate actionable documentation improvement lists

### For AI Tools
- Detect when agents make wrong assumptions (reveals what to document/configure)
- Learn from user corrections to improve agent behavior
- Identify workflow patterns that fail
- Measure improvement over time

## Configuration Schema

**Both `config.yaml` (global) and `.drift.yaml` (project) use this exact same schema.**

Project config overrides global config. Global config is only used when project config is not present or doesn't specify a setting.

```yaml
# Model definitions (provider + all required parameters)
models:
  haiku:
    provider: bedrock
    model_id: us.anthropic.claude-3-haiku-20240307-v1:0
    region: us-east-1

  sonnet:
    provider: bedrock
    model_id: us.anthropic.claude-3-5-sonnet-20241022-v2:0
    region: us-east-1

  gpt4:
    provider: openai
    model_id: gpt-4-turbo-preview
    api_key_env: OPENAI_API_KEY

# Default model for all learning types
default_model: haiku

# Drift learning type definitions
# If defined in project config, completely replaces global definitions
drift_learning_types:
  incomplete_work:
    model: haiku  # Optional: override default_model
    description: "AI stopped before completing full scope"
    detection_prompt: |
      Look for instances where AI claimed done but user
      had to ask for completion or missing parts.
    explicit_signals:
      - "Finish"
      - "Complete"
      - "You didn't finish"
    implicit_signals:
      - User lists missing items after AI says done
      - User asks for specific parts AI didn't do

  documentation_gap:
    model: sonnet  # Optional: override default_model
    description: "Missing/unclear documentation in project context"
    detection_prompt: |
      Identify when AI misunderstood because docs, skills,
      commands didn't explain something clearly.
    explicit_signals:
      - "The docs should mention"
      - "This should be in the skill"
    implicit_signals:
      - User corrects same thing across conversations
      - User manually updates docs after correction

  wrong_assumption:
    description: "AI made incorrect assumptions not stated by user"
    detection_prompt: |
      Find cases where AI assumed something not stated by user.
      These reveal what needs documentation or configuration.
    explicit_signals:
      - "I never said"
      - "Don't assume"
      - "Why did you think"
    implicit_signals:
      - User corrects fundamental approach AI took
      - AI adds complexity user didn't want

  workflow_issue:
    description: "Problem with the process or approach AI took"
    detection_prompt: |
      Detect when AI followed wrong workflow, used wrong tools,
      or took inefficient approach to solve the task.
    explicit_signals:
      - "Why didn't you use"
      - "You should have"
    implicit_signals:
      - User redirects to different tool/method

  implicit_expectation:
    description: "User expected behavior without explicitly stating it"
    detection_prompt: |
      Find expectations users had that they thought were obvious
      but weren't stated explicitly in their request.
    explicit_signals:
      - "Obviously"
      - "Of course"
    implicit_signals:
      - User surprised AI didn't do something

# Agent tool configuration
agent_tools:
  claude-code:
    conversation_path: ~/.claude/projects/

  # Future support
  # cursor:
  #   conversation_path: ~/.cursor/conversations/

# Conversation selection
conversations:
  mode: latest  # Options: latest, last_n_days, all
  days: 7  # Used when mode is last_n_days

# Temp directory for analysis in progress
temp_dir: /tmp/drift
```

## Example Configs

### Global Config (config.yaml)
```yaml
models:
  haiku:
    provider: bedrock
    model_id: us.anthropic.claude-3-haiku-20240307-v1:0
    region: us-east-1
  sonnet:
    provider: bedrock
    model_id: us.anthropic.claude-3-5-sonnet-20241022-v2:0
    region: us-east-1

default_model: haiku

drift_learning_types:
  incomplete_work:
    description: "AI stopped before completing full scope"
    detection_prompt: |
      Look for instances where AI claimed done but user
      had to ask for completion or missing parts.
    explicit_signals:
      - "Finish"
      - "Complete"
    implicit_signals:
      - User lists missing items after AI says done

  documentation_gap:
    model: sonnet
    description: "Missing/unclear documentation in project context"
    detection_prompt: |
      Identify when AI misunderstood because docs didn't explain clearly.
    explicit_signals:
      - "The docs should mention"
    implicit_signals:
      - User manually updates docs after correction

  wrong_assumption:
    description: "AI made incorrect assumptions not stated by user"
    detection_prompt: |
      Find cases where AI assumed something not stated.
    explicit_signals:
      - "I never said"
    implicit_signals:
      - AI adds complexity user didn't want

agent_tools:
  claude-code:
    conversation_path: ~/.claude/projects/

conversations:
  mode: last_n_days
  days: 7

temp_dir: /tmp/drift
```

### Project Config (.drift.yaml)
Same schema, overrides global:

```yaml
# Only check last 3 days for this project
conversations:
  mode: last_n_days
  days: 3

# Only check these two learning types for this project
drift_learning_types:
  incomplete_work:
    model: sonnet
    description: "AI stopped before completing full scope"
    detection_prompt: |
      Look for instances where AI claimed done but user
      had to ask for completion or missing parts.
    explicit_signals:
      - "Finish"
    implicit_signals:
      - User lists missing items

  documentation_gap:
    description: "Missing/unclear documentation in project context"
    detection_prompt: |
      Identify when AI misunderstood because docs didn't explain clearly.
    explicit_signals:
      - "The docs should mention"
    implicit_signals:
      - User corrects same thing across conversations

# Use same models from global
# (models and default_model inherited from global if not specified)
```

## CLI Usage

```bash
# Run analysis from project root (uses .drift.yaml, falls back to config.yaml)
drift analyze

# Output as JSON
drift analyze --format json

# Only analyze specific agent tool
drift analyze --agent-tool claude-code

# Only run specific learning types
drift analyze --types incomplete_work,documentation_gap

# Override conversation selection
drift analyze --latest  # Just latest conversation
drift analyze --days 3  # Last 3 days
drift analyze --all     # All conversations

# Use different model (overrides all model settings)
drift analyze --model sonnet

# Save output to file
drift analyze --format json > results.json
drift analyze --format markdown > report.md

# Analyze specific project (not in project root)
drift analyze --project /path/to/project
```

## Example Output

```bash
$ drift analyze --latest

# Drift Analysis Results

## Summary
- Conversations analyzed: 1 (latest across all enabled agent tools)
- Agent tools: claude-code
- Total learnings found: 2
- By type:
  - wrong_assumption: 1
  - incomplete_work: 1

## Learnings

### Session: f7091296 (drift project, 15 turns)
**Agent Tool:** claude-code
**File:** agent-f7091296.jsonl
**Timestamp:** 2025-11-22 14:30:00

#### [Turn 8] wrong_assumption
**What AI did:** Created comprehensive 500-line documentation
**What user wanted:** Concise MVP.md focused on core functionality
**Frequency:** one-time
**Resolved:** Yes (user corrected immediately)

#### [Turn 12] incomplete_work
**What AI did:** Analyzed conversations but didn't implement multi-pass
**What user wanted:** Full multi-pass implementation
**Frequency:** one-time
**Resolved:** No - still needs implementation
```
