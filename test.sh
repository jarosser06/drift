#!/bin/bash
# Testing script for Drift
# Usage: ./test.sh [--coverage] [--embedded]

set -e

COVERAGE=false
EMBEDDED=false
EXIT_CODE=0

# Parse arguments
for arg in "$@"; do
    case $arg in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --embedded)
            EMBEDDED=true
            shift
            ;;
        *)
            echo "Unknown argument: $arg"
            echo "Usage: ./test.sh [--coverage] [--embedded]"
            exit 1
            ;;
    esac
done

echo "=================================="
echo "Running tests for Drift"
echo "=================================="

# Run pytest with uv
echo ""
if [ "$COVERAGE" = true ]; then
    echo "Running pytest with coverage..."
    if uv run pytest tests/ -v --cov=src/drift --cov-report=html --cov-report=term --cov-fail-under=90; then
        echo ""
        echo "✓ Tests passed with 90%+ coverage!"
        echo "Coverage report generated in htmlcov/index.html"
    else
        echo ""
        echo "✗ Tests failed or coverage below 90%"
        EXIT_CODE=1
    fi
else
    echo "Running pytest..."
    if uv run pytest tests/ -v; then
        echo ""
        echo "✓ Tests passed!"
    else
        echo ""
        echo "✗ Tests failed"
        EXIT_CODE=1
    fi
fi

echo "=================================="

# In embedded mode, always exit 0 (for CI/hooks)
if [ "$EMBEDDED" = true ]; then
    exit 0
fi

exit $EXIT_CODE
