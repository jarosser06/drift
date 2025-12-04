#!/bin/bash
# Build Sphinx documentation
# This script builds the documentation HTML files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCS_DIR="$PROJECT_ROOT/docs"

echo "Installing documentation dependencies..."
cd "$PROJECT_ROOT"
uv pip install -e ".[docs]"

echo "Building documentation..."
cd "$DOCS_DIR"

# Clean previous build
rm -rf _build/html

# Build HTML documentation
uv run sphinx-build -M html . _build

echo ""
echo "Documentation built successfully!"
echo "Output: $DOCS_DIR/_build/html/index.html"
echo ""
echo "To view locally: open $DOCS_DIR/_build/html/index.html"
