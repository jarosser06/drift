# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.2] - 2025-12-06

- Fix: populate execution_details for LLM-based validations

## [0.4.1] - 2025-12-06

- Fix FileExistsValidator glob pattern handling and cache .gitignore creation

## [0.4.0] - 2025-12-06

- Add support for custom validator plugins
- Add support for rule groups to organize validation rules
- Add detailed failure information to validators
- Add dependency graph validation framework with Claude Code validators

## [0.3.0] - 2025-12-04

- Add support for separate rules file with `--rules-file` option (local and remote file support)

## [0.2.0] - 2025-12-04

- Add Claude Code provider support - use existing Claude Code CLI without API keys
- Add comprehensive documentation infrastructure and validation rules
- Add automated release workflow with GitHub Actions for CI/CD
- Add release workflow scripts and automation tools
- Fix token counting replaced with line count for better performance
- Fix Claude Code MCP configuration
- Remove uv.lock from version control (library project best practice)

## [0.1.1] - 2025-12-03

- Add PyPI badges to README (version badge and Python 3.10+ compatibility)
- Add direct link to PyPI package page in installation section
- Add distro.sh script for building and publishing distributions with `build` and `push` commands
- Switch build backend from Hatchling to setuptools for better PyPI name/import name handling
- Add build tools to dev dependencies (build, twine, pkginfo>=1.12.0)

## [0.1.0] - 2025-12-03

- Initial release of ai-drift (published to PyPI)
- AI agent conversation analyzer for identifying drift between intent and execution
- Support for Anthropic API and AWS Bedrock providers with Claude models (Sonnet, Haiku)
- 24 validation rules: conversation quality (incomplete_work, delegation_missed, command_not_used, skill_not_used, guideline_violation, documentation_gap, codebase_gap), project structure (claude_md_exists, command/skill/agent broken links, duplicate dependencies, markdown formatting, inconsistency checks), and file validation (JSON Schema, YAML Schema, YAML frontmatter)
- CLI with multiple output formats (markdown with color, JSON)
- Configurable rules via .drift.yaml with flexible rule definitions
- LLM response caching with smart content-based invalidation (SHA-256 hashing)
- Parallel execution support for validation rules (asyncio-based, disable with --no-parallel)
- Support for Claude Code agent tool with conversation log parsing
- Rich terminal output with colors and formatting
- Comprehensive test suite with 90%+ coverage requirement
- Full linting configuration (black, flake8, isort, mypy)
- Project-aware analysis: automatically discovers commands, skills, agents, and MCP servers
- Fast `--no-llm` mode for programmatic-only validation
