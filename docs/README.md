# Drift Documentation

This directory contains the Sphinx documentation for Drift.

## Building Documentation

### Prerequisites

Install documentation dependencies:

```bash
uv pip install -e ".[docs]"
```

### Build Locally

```bash
# Using the build script
./scripts/build-docs.sh

# Or manually
cd docs
sphinx-build -M html . _build
```

Output will be in `docs/_build/html/index.html`.

### View Locally

```bash
open docs/_build/html/index.html
```

## Documentation Structure

- `conf.py` - Sphinx configuration
- `index.rst` - Main documentation index
- `installation.rst` - Installation guide
- `quickstart.rst` - Quick start guide
- `configuration.rst` - Configuration reference
- `cli.rst` - CLI reference
- `validation-rules.rst` - Validation rules documentation
- `architecture.rst` - Architecture overview
- `contributing.rst` - Development guide
- `changelog.rst` - Changelog
- `api/` - API reference (auto-generated)
- `_static/` - Static assets
- `_build/` - Build output (git-ignored)

## Deployment

Documentation is automatically deployed to https://docs.driftai.dev on releases.

Manual deployment:

```bash
# Deploy to production
source infrastructure/config.sh
./scripts/deploy-docs.sh
```

## Writing Documentation

### reStructuredText

Documentation uses reStructuredText (`.rst`) format. See [Sphinx documentation](https://www.sphinx-doc.org/en/master/usage/restructuredtext/basics.html) for syntax.

### Code Examples

Use code blocks with language specification:

```rst
.. code-block:: python

   from drift.core.analyzer import Analyzer

   analyzer = Analyzer()
   result = analyzer.analyze()
```

### API Documentation

API documentation is auto-generated from docstrings using Sphinx autodoc.

Ensure all public APIs have:
- Type hints
- PEP 257 compliant docstrings
- Parameter descriptions
- Return value descriptions
- Exception descriptions

### Validation

Run documentation audit before releases:

```bash
# Using Claude Code
/audit-docs
```

This checks for:
- Code example accuracy
- Correct import paths
- Objective language (no subjective adjectives)
- Complete examples
