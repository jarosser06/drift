# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Conversation analysis rules (LLM-based)
- Project validation rules (programmatic)
- Multi-provider support (Anthropic API, AWS Bedrock)
- Response caching with SHA-256 based invalidation
- Parallel execution support with asyncio
- File format validators (JSON Schema, YAML Schema, YAML frontmatter)

### Changed
- N/A

### Deprecated
- N/A

### Removed
- N/A

### Fixed
- N/A

### Security
- N/A

## [0.1.0] - 2024-01-XX

### Added
- Initial release
- CLI tool for analyzing AI agent conversations
- Support for Claude Code agent tool
- Validation rules for commands, skills, and agents
- Markdown and JSON output formats
- Configuration via .drift.yaml
- Test suite with 90%+ coverage requirement
- Linting setup (black, flake8, isort, mypy)
